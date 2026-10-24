import json
import sqlite3
from types import SimpleNamespace as NS

import httpx
import openai
import pytest

from core import ledger
from core.llm import BudgetExceeded, Client, redact, rehydrate


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAETOR_LEDGER_DB", str(tmp_path / "sub" / "dir" / "ledger.sqlite"))  # parents auto-created
    monkeypatch.setenv("PRAETOR_CACHE", "0")


class FakeSDK:
    """Queue of replies or exceptions; records every request."""

    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        text, usage = r if isinstance(r, tuple) else (r, (10, 5))
        return NS(choices=[NS(message=NS(content=text))], usage=NS(prompt_tokens=usage[0], completion_tokens=usage[1]))


MODELS = {"ULTRA": "m-ultra", "SUPER": "m-super", "NANO": "m-nano"}
CONN_ERR = openai.APIConnectionError(request=httpx.Request("POST", "http://example.com"))


def client(*replies, **kw):
    return Client(FakeSDK(*replies), MODELS, sleep=lambda s: None, **kw)


# ---- ledger
def test_ledger_chain_and_summary():
    assert ledger.verify_chain() and ledger.entries() == []
    a = ledger.record("tokenfactory", "extract", b"hello", 2)
    b = ledger.record("tavily", "search", "world")
    assert (a.id, b.id, b.prev_hash, a.bytes, a.redactions) == (1, 2, a.hash, 5, 2)
    assert a.prev_hash == "0" * 64 and ledger.entries() == [a, b] and ledger.verify_chain()
    s = ledger.summary()
    assert (s["calls"], s["bytes"], s["redactions"]) == (2, 10, 2) and s["by_service"]["tavily"]["calls"] == 1


def test_ledger_stores_no_payload():
    ledger.record("tokenfactory", "extract", b"jane@example.com secret", 1)
    dump = "\n".join(sqlite3.connect(ledger.db_path()).iterdump())
    assert "jane@example.com" not in dump and "secret" not in dump


def test_ledger_append_only_and_tamper_detected():
    for i in range(3):
        ledger.record("tokenfactory", f"p{i}", b"x")
    con = sqlite3.connect(ledger.db_path())
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("UPDATE ledger SET bytes = 0 WHERE id = 2")

    def drop_guards():  # an attacker with file access can drop the triggers (they are recreated on the next connect)...
        for trig in ("ledger_no_update", "ledger_no_delete"):
            con.execute(f"DROP TRIGGER IF EXISTS {trig}")

    drop_guards()
    con.execute("UPDATE ledger SET bytes = 999 WHERE id = 2")
    con.commit()
    assert not ledger.verify_chain()  # ...but the chain still breaks
    drop_guards()
    con.execute("UPDATE ledger SET bytes = 1 WHERE id = 2")
    con.commit()
    assert ledger.verify_chain()
    drop_guards()
    con.execute("DELETE FROM ledger WHERE id = 2")
    con.commit()
    assert not ledger.verify_chain()


def test_ledger_rejects_bad_service():
    with pytest.raises(ValueError):
        ledger.record("nope", "x", b"")
    assert ledger.entries() == []


# ---- redaction
def test_redact_roundtrip_and_stability():
    text = ("Mail jane.doe@example.com or call (555) 555-0123, +1 555-555-0188. Lives at 100 Example Street, Apt 4. "
            "Again jane.doe@example.com. SSN 123-45-6789, key AB12CD34EF56.")
    out, m = redact(text)
    assert out.count("<EMAIL_1>") == 2 and "<PHONE_2>" in out and "<ADDRESS_1>" in out and "<ID_1>" in out
    assert not any(s in out for s in ("jane.doe", "555-0123", "Example Street", "123-45-6789", "AB12CD34EF56"))
    assert rehydrate(out, m) == text
    assert redact("x jane.doe@example.com", m)[0] == "x <EMAIL_1>" and len(m) == 6  # shared map keeps placeholders stable


def test_redact_leaves_prose_alone():
    prose = ("In 2024 I bought 3 Big apples, 12 items cost 100-2000 yen. See section 4.2 on the lane. "
             "Model nemotron-3-super-120b-a12b ran 5 times at version v1.2.3, order 42.")
    assert redact(prose) == (prose, {})


def test_rehydrate_ignores_unknown_placeholders():
    assert rehydrate("<EMAIL_9> <EMAIL_1>", {"<EMAIL_1>": "a@example.com"}) == "<EMAIL_9> a@example.com"


# ---- client
def test_tier_routing_and_redaction_and_ledger():
    c = client("ok for <EMAIL_1>", "b", "c")
    msgs = [{"role": "user", "content": "write to jane@example.com"}]
    assert c.chat("SUPER", msgs, "t1") == "ok for jane@example.com"
    c.chat("ULTRA", msgs, "t2")
    c.chat("NANO", msgs, "t3")
    assert [r["model"] for r in c.sdk.requests] == ["m-super", "m-ultra", "m-nano"]
    assert "jane@example.com" not in json.dumps(c.sdk.requests) and "<EMAIL_1>" in json.dumps(c.sdk.requests)
    es = ledger.entries()
    assert [e.purpose for e in es] == ["t1", "t2", "t3"] and all(e.redactions == 1 and e.service == "tokenfactory" for e in es)
    assert es[0].bytes == len(json.dumps(c.sdk.requests[0], sort_keys=True)) and ledger.verify_chain()
    assert c.usage["calls"] == 3 and c.usage["prompt_tokens"] == 30 and c.usage["usd"] == 0


def test_unknown_tier_and_missing_model():
    with pytest.raises(ValueError):
        client().chat("HUGE", [], "x")
    with pytest.raises(RuntimeError, match="MODEL_NANO"):
        Client(FakeSDK(), {"NANO": ""}).chat("NANO", [], "x")


def test_structured_output_rehydrated():
    c = client('{"emails": ["<EMAIL_1>"], "n": 1}')
    out = c.chat("NANO", [{"role": "user", "content": "a@example.com"}], "x", json_schema={"type": "object"})
    assert out == {"emails": ["a@example.com"], "n": 1}
    assert c.sdk.requests[0]["response_format"]["json_schema"]["schema"] == {"type": "object"}
    with pytest.raises(ValueError):  # not JSON -> error, not cached
        client("nope").chat("NANO", [{"role": "user", "content": "q"}], "x", json_schema={"type": "object"})


def test_retry_backoff_then_success():
    sleeps = []
    c = Client(FakeSDK(CONN_ERR, CONN_ERR, "fine"), MODELS, sleep=sleeps.append)
    assert c.chat("NANO", [{"role": "user", "content": "hi"}], "x") == "fine"
    assert sleeps == [0.5, 1.0] and len(ledger.entries()) == 3  # each attempt is itemised


def test_retry_gives_up():
    c = client(*[CONN_ERR] * 4, max_retries=3)
    with pytest.raises(openai.APIConnectionError):
        c.chat("NANO", [{"role": "user", "content": "hi"}], "x")
    assert len(c.sdk.requests) == 4
    c2 = client(ValueError("boom"))  # non-retryable errors surface immediately
    with pytest.raises(ValueError):
        c2.chat("NANO", [{"role": "user", "content": "hi"}], "x")
    assert len(c2.sdk.requests) == 1


def test_cache_hit_skips_call_and_ledger(tmp_path):
    c = client("hello <EMAIL_1>", cache_dir=tmp_path / "cache")
    msgs = [{"role": "user", "content": "to a@example.com"}]
    assert c.chat("SUPER", msgs, "x") == c.chat("SUPER", msgs, "x") == "hello a@example.com"
    assert len(c.sdk.requests) == 1 and len(ledger.entries()) == 1 and c.usage["calls"] == 1
    assert "a@example.com" not in "".join(p.read_text() for p in (tmp_path / "cache").iterdir())


def test_token_ceiling_rejects_before_call():
    c = client("a", max_tokens_ceiling=3000, max_output_tokens=2048)
    c.chat("NANO", [{"role": "user", "content": "hi"}], "x")  # used 15, projected well under 3000
    with pytest.raises(BudgetExceeded):
        c.chat("NANO", [{"role": "user", "content": "z" * 4000}], "x")
    assert len(c.sdk.requests) == 1 and len(ledger.entries()) == 1  # rejected call never left the machine


def test_usd_cap_only_when_price_configured():
    c = client("a", "b", max_usd=0.01, prices={"SUPER": (1000.0, 1000.0)})  # SUPER priced; NANO unpriced
    with pytest.raises(BudgetExceeded, match="USD"):
        c.chat("SUPER", [{"role": "user", "content": "hi"}], "x")
    assert c.chat("NANO", [{"role": "user", "content": "hi"}], "x") == "a" and c.usage["usd"] == 0
