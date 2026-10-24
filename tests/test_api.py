import json

import pytest
from fastapi.testclient import TestClient

from apps.api.adapters import FixtureServiceAdapter
from apps.api.main import ApiSettings, create_app


@pytest.fixture
def settings(tmp_path):
    return ApiSettings(database_path=str(tmp_path / "api.sqlite3"))


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def build_graph(client):
    response = client.post("/api/twin", json={"persona_id": "pat-example-01"})
    assert response.status_code == 200
    return response.json()


def parse_sse(response):
    blocks = [block for block in response.text.split("\n\n") if block]
    parsed = []
    for block in blocks:
        lines = block.splitlines()
        parsed.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return parsed


def test_happy_paths(client):
    assert client.get("/api/health").json() == {"ok": True, "demo_mode": True}
    assert client.get("/api/personas").json() == [{"id": "pat-example-01", "name": "Pat Example"}]
    graph = build_graph(client)

    attack = client.post("/api/attack", json={"graph_id": graph["id"]})
    assert attack.status_code == 200
    assert len(attack.json()["paths"]) == len(attack.json()["findings"]) == 3

    remediation = client.post("/api/remediate", json={"graph_id": graph["id"]})
    assert remediation.status_code == 200
    assert remediation.json()["paths_before"] == 3
    assert remediation.json()["paths_after"] == 0

    league = client.post("/api/league/run", json={"graph_id": graph["id"], "rounds": 2})
    assert league.status_code == 200
    assert league.json()["run_id"].startswith("league-")

    ledger = client.get("/api/ledger")
    assert ledger.json() == {
        "entries": [],
        "verified": True,
        "summary": {"entries": 0, "bytes": 0, "by_service": {}},
    }
    assert client.post("/api/watch/run").json()["run_id"].startswith("watch-")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"persona_id": "pat-example-01", "seeds": {"name": "Pat Example"}, "attest": True},
        {"persona_id": "pat-example-01", "password": "not-allowed"},
        {"seeds": {"name": "Pat Example"}},
    ],
)
def test_twin_validation_errors_are_strings(client, payload):
    response = client.post("/api/twin", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_league_validation(client):
    graph = build_graph(client)
    response = client.post("/api/league/run", json={"graph_id": graph["id"], "rounds": 0})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_demo_mode_rejects_attested_live_seeds(client):
    response = client.post(
        "/api/twin",
        json={"seeds": {"name": "Pat Example", "emails": ["pat@example.com"]}, "attest": True},
    )
    assert response.status_code == 403
    assert "demo mode" in response.json()["detail"]


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/api/twin", {"persona_id": "unknown"}),
        ("post", "/api/attack", {"graph_id": "unknown"}),
        ("post", "/api/remediate", {"graph_id": "unknown"}),
        ("post", "/api/league/run", {"graph_id": "unknown", "rounds": 1}),
        ("get", "/api/events?run_id=unknown", None),
    ],
)
def test_unknown_ids_are_404(client, method, path, body):
    response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_sse_framing_isolation_completion_and_cleanup(client):
    graph = build_graph(client)
    first = client.post("/api/league/run", json={"graph_id": graph["id"], "rounds": 1}).json()["run_id"]
    second = client.post("/api/league/run", json={"graph_id": graph["id"], "rounds": 3}).json()["run_id"]

    response = client.get(f"/api/events?run_id={first}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.endswith("\n\n")
    events = parse_sse(response)
    assert [name for name, _ in events] == ["progress", "round", "done"]
    assert {event["run_id"] for _, event in events} == {first}
    assert second not in response.text
    assert client.app.state.streams.active_count == 0


def test_run_failure_is_an_sse_error(settings):
    class BrokenLeagueAdapter(FixtureServiceAdapter):
        def league_rounds(self, graph, rounds):
            raise RuntimeError("fixture league failed")

    service = BrokenLeagueAdapter(settings.fixture_dir)
    with TestClient(create_app(settings, service=service)) as client:
        graph = build_graph(client)
        run_id = client.post("/api/league/run", json={"graph_id": graph["id"], "rounds": 1}).json()["run_id"]
        events = parse_sse(client.get(f"/api/events?run_id={run_id}"))
        assert events[-1][0] == "error"
        assert events[-1][1]["data"]["detail"] == "fixture league failed"


def test_non_demo_fixture_adapter_does_not_fake_live_scan(tmp_path):
    settings = ApiSettings(demo_mode=False, database_path=str(tmp_path / "api.sqlite3"))
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/twin", json={"seeds": {"name": "Self Example"}, "attest": True})
    assert response.status_code == 501
    assert "fixture data was not substituted" in response.json()["detail"]


def test_cors_is_restrictive_by_default_and_configurable(tmp_path):
    default = ApiSettings(database_path=str(tmp_path / "default.sqlite3"))
    with TestClient(create_app(default)) as client:
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" not in response.headers

    configured = ApiSettings(
        database_path=str(tmp_path / "configured.sqlite3"), cors_origins=("http://localhost:5173",)
    )
    with TestClient(create_app(configured)) as client:
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
