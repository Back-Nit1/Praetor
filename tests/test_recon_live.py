"""Live recon with fakes only: no network, no keys."""
import json
from types import SimpleNamespace as NS

import httpx
import openai
import pytest
from tavily.errors import TimeoutError as TavilyTimeout
from tavily.errors import UsageLimitExceededError

from core import ledger, llm
from core.recon.extract import extract
from core.recon.live import live_facts
from core.recon.search import QueryBudgetExceeded, Searcher, queries_for
from core.schemas import Seeds

EMAIL, PHONE, ADDR = "pat.example@example.com", "(555) 555-0142", "100 Example Street"
URL = "https://peoplesearch.example.com/pat"
SNIP = {"title": "Pat Example", "url": URL,
        "content": f"Pat Example, {ADDR}. Phone {PHONE}. Email {EMAIL}. Relatives: Sam Sample, Alex Sample."}
SEEDS = Seeds(name="Pat Example", city="Exampleton", emails=[EMAIL], handles=["pat_ex"])


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("NEMESIS_LEDGER_DB", str(tmp_path / "ledger.sqlite"))
    monkeypatch.setenv("NEMESIS_CACHE", "0")
    for k in ("NEMESIS_DEMO_MODE", "PRAETOR_DEMO_MODE"):
        monkeypatch.delenv(k, raising=False)


class FakeTavily:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def search(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0) if self.replies else {"results": [SNIP]}
        if isinstance(r, Exception):
            raise r
        return r


def searcher(*replies, **kw):
    return Searcher(True, client=FakeTavily(*replies), sleep=lambda s: None, **kw)


class FakeSDK:
    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        return NS(choices=[NS(message=NS(content=self.replies.pop(0)))], usage=NS(prompt_tokens=10, completion_tokens=5))


def use_model(monkeypatch, *replies):
    sdk = FakeSDK(*(r if isinstance(r, str) else json.dumps(r) for r in replies))
    monkeypatch.setattr(llm, "chat", llm.Client(sdk, {"NANO": "m-nano"}, cache_dir=None, sleep=lambda s: None).chat)
    return sdk


def fact(snippet=0, kind="email", value="<EMAIL_1>", source_kind="broker", confidence=0.9):
    return {"snippet": snippet, "kind": kind, "value": value, "source_kind": source_kind, "confidence": confidence}


# ---------- search guards ----------
@pytest.mark.parametrize("kw,exc", [({"attest": False}, ValueError), ({"persona_id": "pat-example-01"}, ValueError)])
def test_guard_blocks_before_any_request(kw, exc):
    s = Searcher(**{"attest": True, **kw}, client=FakeTavily())
    with pytest.raises(exc):
        s.search('"Pat Example"')
    assert not s._client.calls and not ledger.entries()


@pytest.mark.parametrize("var", ["NEMESIS_DEMO_MODE", "PRAETOR_DEMO_MODE"])
def test_demo_mode_blocks(monkeypatch, var):
    monkeypatch.setenv(var, "1")
    s = searcher()
    with pytest.raises(PermissionError, match="demo"):
        s.search("x")
    with pytest.raises(PermissionError):
        live_facts(SEEDS, True, searcher=s)
    assert not s._client.calls and not ledger.entries()


@pytest.mark.parametrize("q", ['"relative_1"', 'Pat Example relative_12 address'])
def test_relative_tokens_never_searched(q):
    s = searcher()
    with pytest.raises(ValueError, match="relative"):
        s.search(q)
    assert not s._client.calls and not ledger.entries()


def test_queries_only_from_user_seeds_and_refuse_tokens():
    qs = queries_for(SEEDS)
    assert qs and all(any(v in q for v in ("Pat Example", EMAIL, "pat_ex")) for q in qs)
    assert not any("Sam" in q or "relative" in q for q in qs)
    with pytest.raises(ValueError, match="relative"):
        queries_for(Seeds(name="relative_1"))
    with pytest.raises(ValueError, match="relative"):
        queries_for(Seeds(name="Pat Example", handles=["relative_2"]))


# ---------- search mechanics ----------
def test_one_ledger_entry_per_request_and_shape():
    s = searcher({"results": [SNIP, "junk", {"url": "u", "content": "c", "raw_content": "dropped"}]})
    out = s.search('"Pat Example"')
    assert out == [SNIP, {"url": "u", "content": "c"}]
    (e,) = ledger.entries()
    assert e.service == "tavily" and e.purpose == "recon-search" and ledger.verify_chain()


def test_retry_timeouts_each_attempt_logged():
    s = searcher(TavilyTimeout("slow"), TavilyTimeout("slow"), {"results": [SNIP]})
    assert s.search("q") == [SNIP]
    assert len(s._client.calls) == 3 and len(ledger.entries()) == 3
    assert s._client.calls[0]["timeout"] == s.timeout
    assert s.used == 1  # retries are not extra queries


def test_retry_exhausted_raises_and_fatal_errors_not_retried():
    s = searcher(*[TavilyTimeout("slow")] * 3)
    with pytest.raises(TavilyTimeout):
        s.search("q")
    assert len(ledger.entries()) == 3
    s2 = searcher(UsageLimitExceededError("quota"))
    with pytest.raises(UsageLimitExceededError):
        s2.search("q2")
    assert len(ledger.entries()) == 4


def test_query_budget():
    s = searcher(max_queries=2)
    s.search("a")
    s.search("b")
    with pytest.raises(QueryBudgetExceeded):
        s.search("c")
    assert len(s._client.calls) == 2 and len(ledger.entries()) == 2


def test_cache_hit_costs_nothing(tmp_path):
    s = searcher(cache_dir=tmp_path / "c", max_queries=1)
    first = s.search("q")
    assert s.search("q") == first  # budget is 1: would raise if the hit counted
    assert len(s._client.calls) == 1 and len(ledger.entries()) == 1
    (next((tmp_path / "c").iterdir())).write_text("{not json")  # corrupt entry -> treated as a miss
    assert searcher(cache_dir=tmp_path / "c").search("q") == first


# ---------- extraction ----------
def test_extract_redacts_outbound_and_rehydrates(monkeypatch):
    sdk = use_model(monkeypatch, {"facts": [
        fact(kind="email", value="<EMAIL_1>"), fact(kind="phone", value="<PHONE_1>"),
        fact(kind="address", value="<ADDRESS_1>"), fact(kind="name", value="Pat Example"),
        fact(kind="email", value="<EMAIL_1>", confidence=0.4),  # duplicate
        fact(kind="relative_token", value="relative_1"), fact(kind="relative_token", value="relative_2"),
    ]})
    facts = extract([SNIP])
    wire = json.dumps(sdk.requests)
    assert all(raw not in wire for raw in (EMAIL, "555-0142", ADDR))
    assert {f.kind for f in facts} == {"email", "phone", "address", "name", "relative_token"}
    assert {(f.kind, f.value) for f in facts} >= {("email", EMAIL), ("phone", "555-555-0142"), ("address", ADDR)}
    assert sorted(f.value for f in facts if f.kind == "relative_token") == ["relative_1", "relative_2"]
    assert all(f.source_url == URL for f in facts)
    assert sum(f.kind == "email" for f in facts) == 1
    assert "Sam" not in " ".join(f.value for f in facts) and "Alex" not in " ".join(f.value for f in facts)
    assert [e.service for e in ledger.entries()] == ["tokenfactory"] and ledger.entries()[0].redactions >= 3


def test_extract_rejects_bad_facts_keeps_good(monkeypatch):
    use_model(monkeypatch, {"facts": [
        fact(value="<EMAIL_1>"),                              # good
        fact(value="stranger@example.org"),                   # not in snippet (hallucinated)
        fact(value="<EMAIL_9>"),                              # unknown placeholder survives rehydration -> ungrounded
        fact(kind="relative_token", value="Sam Sample"),      # a name, not a token
        fact(kind="ssn", value="x"),                          # kind outside the schema
        fact(source_kind="darkweb"),                          # bad source_kind
        fact(confidence=7), fact(confidence="high"),          # out of range / not a number
        fact(snippet=3), fact(snippet=-1), fact(snippet=True),  # bad index
        {"kind": "email"}, "oops", None, fact(value=""),      # malformed items
    ]})
    out = extract([SNIP])
    assert [(f.kind, f.value) for f in out] == [("email", EMAIL)]


@pytest.mark.parametrize("reply", ["not json", "[]", '{"facts": "no"}', '{"other": 1}', "null"])
def test_extract_survives_malformed_output(monkeypatch, reply):
    use_model(monkeypatch, reply)
    assert extract([SNIP]) == []


def test_extract_chunks_and_global_relative_tokens(monkeypatch):
    snips = [{**SNIP, "url": f"https://b{i}.example.com/p"} for i in range(7)]
    rel = lambda i: fact(snippet=i, kind="relative_token", value="relative_1")
    sdk = use_model(monkeypatch, {"facts": [rel(0), rel(1)]}, {"facts": [rel(0)]})
    out = extract(snips)
    assert len(sdk.requests) == 2  # 5 + 2 snippets
    assert sorted(f.value for f in out) == ["relative_1", "relative_2", "relative_3"]  # same local label != same person


def test_extract_skips_non_http_and_empty():
    assert extract([]) == []
    assert extract([{"url": "javascript:alert(1)", "content": "x"}, {"content": "no url"}]) == []  # no model call


def test_extract_budget_error_propagates(monkeypatch):
    sdk = FakeSDK()
    monkeypatch.setattr(llm, "chat", llm.Client(sdk, {"NANO": "m"}, cache_dir=None, max_tokens_ceiling=10).chat)
    with pytest.raises(llm.BudgetExceeded):
        extract([SNIP])


def test_extract_api_error_propagates(monkeypatch):
    err = openai.APIConnectionError(request=httpx.Request("POST", "http://example.com"))

    class Boom(FakeSDK):
        def _create(self, **kw):
            raise err

    monkeypatch.setattr(llm, "chat", llm.Client(Boom(), {"NANO": "m"}, cache_dir=None, max_retries=0).chat)
    with pytest.raises(openai.APIConnectionError):
        extract([SNIP])


# ---------- end to end ----------
def test_live_facts_end_to_end(monkeypatch):
    use_model(monkeypatch, {"facts": [fact(value="<EMAIL_1>"), fact(kind="name", value="Pat Example")]})
    s = searcher(max_queries=5)  # same SNIP for every query -> deduped by URL
    facts = live_facts(SEEDS, True, searcher=s)
    assert {(f.kind, f.value) for f in facts} == {("email", EMAIL), ("name", "Pat Example")}
    assert len(s._client.calls) == len(queries_for(SEEDS))
    assert [e.service for e in ledger.entries()].count("tavily") == len(queries_for(SEEDS))
    assert [e.service for e in ledger.entries()].count("tokenfactory") == 1 and ledger.verify_chain()
    with pytest.raises(ValueError, match="attest"):
        live_facts(SEEDS, False, searcher=s)
