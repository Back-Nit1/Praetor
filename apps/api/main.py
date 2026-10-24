"""Nemesis HTTP API."""

from __future__ import annotations

import asyncio
import os
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from apps.api.adapters import CoreServiceAdapter, FixtureServiceAdapter, NemesisServiceAdapter, UnknownPersonaError
from apps.api.repository import SqliteApiRepository
from core.schemas import Event, GraphRef, LeagueRunRequest, RunRef, TwinRequest

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ApiSettings:
    demo_mode: bool = True
    database_path: str = str(ROOT / "data" / "nemesis-api.sqlite3")
    fixture_dir: str = str(ROOT / "data" / "fixtures")
    adapter: str = "fixture"
    cors_origins: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> ApiSettings:
        origins = tuple(origin.strip() for origin in os.getenv("NEMESIS_CORS_ORIGINS", "").split(",") if origin.strip())
        return cls(
            demo_mode=os.getenv("NEMESIS_DEMO_MODE", "1").lower() in {"1", "true", "yes", "on"},
            database_path=os.getenv("NEMESIS_API_DB_PATH", cls.database_path),
            fixture_dir=os.getenv("NEMESIS_FIXTURE_DIR", cls.fixture_dir),
            adapter=os.getenv("NEMESIS_API_ADAPTER", "fixture").lower(),
            cors_origins=origins,
        )


class StreamRegistry:
    """Tracks live SSE subscriptions and always removes them on close/cancel."""

    def __init__(self) -> None:
        self._active: Counter[str] = Counter()

    def open(self, run_id: str) -> None:
        self._active[run_id] += 1

    def close(self, run_id: str) -> None:
        self._active[run_id] -= 1
        if self._active[run_id] <= 0:
            del self._active[run_id]

    @property
    def active_count(self) -> int:
        return sum(self._active.values())


def _build_adapter(settings: ApiSettings) -> NemesisServiceAdapter:
    if settings.adapter == "fixture":
        return FixtureServiceAdapter(settings.fixture_dir)
    if settings.adapter == "core":
        return CoreServiceAdapter()
    raise RuntimeError(f"unknown API adapter: {settings.adapter}")


def _validation_detail(exc: RequestValidationError) -> str:
    messages = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        prefix = f"{location}: " if location else ""
        messages.append(f"{prefix}{error['msg']}")
    return "; ".join(messages)


def _sse(event: Event) -> str:
    return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"


def create_app(
    settings: ApiSettings | None = None,
    service: NemesisServiceAdapter | None = None,
    repository: SqliteApiRepository | None = None,
) -> FastAPI:
    settings = settings or ApiSettings.from_env()
    service = service or _build_adapter(settings)
    repository = repository or SqliteApiRepository(settings.database_path)
    streams = StreamRegistry()
    app = FastAPI(title="Nemesis API")
    app.state.settings = settings
    app.state.service = service
    app.state.repository = repository
    app.state.streams = streams

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": _validation_detail(exc)})

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True, "demo_mode": settings.demo_mode}

    @app.get("/api/personas")
    def personas() -> list[dict[str, str]]:
        return service.personas()

    @app.post("/api/twin")
    def twin(body: TwinRequest):
        if body.seeds is not None and settings.demo_mode:
            raise HTTPException(status_code=403, detail="live seeds are disabled in demo mode; choose a synthetic persona")
        try:
            graph = service.build_twin(body.persona_id, body.seeds, body.attest)
        except UnknownPersonaError as exc:
            raise HTTPException(status_code=404, detail=f"unknown synthetic persona: {exc}") from exc
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        repository.put_graph(graph)
        return graph

    def require_graph(graph_id: str):
        graph = repository.get_graph(graph_id)
        if graph is None:
            raise HTTPException(status_code=404, detail=f"unknown graph_id: {graph_id}")
        return graph

    @app.post("/api/attack")
    def attack(body: GraphRef):
        return service.attack(require_graph(body.graph_id))

    @app.post("/api/remediate")
    def remediate(body: GraphRef):
        return service.remediate(require_graph(body.graph_id))

    def save_run(kind: str, graph_id: str | None, build_data) -> RunRef:
        run_id = f"{kind}-{uuid4().hex}"
        events = [Event(type="progress", run_id=run_id, data={"stage": "started", "kind": kind})]
        status = "done"
        try:
            for event_type, data in build_data():
                events.append(Event(type=event_type, run_id=run_id, data=data))
            events.append(Event(type="done", run_id=run_id, data={"kind": kind}))
        except Exception as exc:  # noqa: BLE001 - failures must become observable run events
            status = "error"
            events.append(Event(type="error", run_id=run_id, data={"detail": str(exc)}))
        repository.put_run(run_id, kind, graph_id, status, events)
        return RunRef(run_id=run_id)

    @app.post("/api/league/run")
    def league_run(body: LeagueRunRequest) -> RunRef:
        graph = require_graph(body.graph_id)

        def data():
            for result in service.league_rounds(graph, body.rounds):
                yield "round", result.model_dump(mode="json")

        return save_run("league", graph.id, data)

    @app.get("/api/events")
    def events(request: Request, run_id: str):
        if not repository.has_run(run_id):
            raise HTTPException(status_code=404, detail=f"unknown run_id: {run_id}")

        async def generate() -> AsyncIterator[str]:
            streams.open(run_id)
            try:
                for event in repository.get_events(run_id):
                    if await request.is_disconnected():
                        return
                    yield _sse(event)
                    await asyncio.sleep(0)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - response headers have already been sent
                yield _sse(Event(type="error", run_id=run_id, data={"detail": str(exc)}))
            finally:
                streams.close(run_id)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/ledger")
    def ledger():
        return service.ledger()

    @app.post("/api/watch/run")
    def watch_run() -> RunRef:
        return save_run("watch", None, lambda: iter((("progress", service.watch_result()),)))

    return app


app = create_app()
