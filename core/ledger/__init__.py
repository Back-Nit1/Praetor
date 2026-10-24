"""Append-only, hash-chained log of every outbound call.

Stores metadata only: byte count, payload SHA-256, purpose, service, redaction count.
Never payload contents, identifiers, keys or redaction maps.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from core.schemas import LedgerEntry, now

GENESIS = "0" * 64
_HASHED = ("id", "ts", "service", "purpose", "bytes", "payload_sha256", "redactions", "prev_hash")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, service TEXT NOT NULL, purpose TEXT NOT NULL,
  bytes INTEGER NOT NULL, payload_sha256 TEXT NOT NULL, redactions INTEGER NOT NULL,
  prev_hash TEXT NOT NULL, hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger
  BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger
  BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
"""


def db_path() -> Path:
    """Read on every call so tests can point NEMESIS_LEDGER_DB at a tmp dir."""
    return Path(os.environ.get("NEMESIS_LEDGER_DB", "data/private/ledger.sqlite"))


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30, isolation_level=None)  # autocommit; we BEGIN explicitly
    con.row_factory = sqlite3.Row
    con.executescript(_SCHEMA)
    return con


def _hash(row) -> str:
    canonical = json.dumps({k: row[k] for k in _HASHED}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def record(service: str, purpose: str, payload_bytes: bytes | str, redactions: int = 0) -> LedgerEntry:
    data = payload_bytes.encode() if isinstance(payload_bytes, str) else payload_bytes
    with closing(_connect()) as con:
        con.execute("BEGIN IMMEDIATE")  # serialises writers across threads and processes
        try:
            last = con.execute("SELECT id, hash FROM ledger ORDER BY id DESC LIMIT 1").fetchone()
            row = {
                "id": (last["id"] if last else 0) + 1,
                "ts": now().isoformat(),
                "service": service,
                "purpose": purpose,
                "bytes": len(data),
                "payload_sha256": hashlib.sha256(data).hexdigest(),
                "redactions": redactions,
                "prev_hash": last["hash"] if last else GENESIS,
            }
            row["hash"] = _hash(row)
            entry = LedgerEntry(**row)  # validates service / non-negative counts before anything is written
            con.execute(
                "INSERT INTO ledger (id, ts, service, purpose, bytes, payload_sha256, redactions, prev_hash, hash)"
                " VALUES (:id, :ts, :service, :purpose, :bytes, :payload_sha256, :redactions, :prev_hash, :hash)",
                row,
            )
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    return entry


def entries() -> list[LedgerEntry]:
    with closing(_connect()) as con:
        return [LedgerEntry(**dict(r)) for r in con.execute("SELECT * FROM ledger ORDER BY id")]


def verify_chain() -> bool:
    """Recompute every hash and link. Catches edits and mid-chain deletes; a truncated tail needs an external anchor."""
    prev = GENESIS
    with closing(_connect()) as con:
        for r in con.execute("SELECT * FROM ledger ORDER BY id"):
            if r["prev_hash"] != prev or r["hash"] != _hash(r):
                return False
            prev = r["hash"]
    return True


def summary() -> dict:
    with closing(_connect()) as con:
        by_service = {
            r["service"]: {"calls": r["calls"], "bytes": r["bytes"], "redactions": r["redactions"]}
            for r in con.execute(
                "SELECT service, COUNT(*) calls, SUM(bytes) bytes, SUM(redactions) redactions FROM ledger GROUP BY service"
            )
        }
    return {
        "calls": sum(s["calls"] for s in by_service.values()),
        "bytes": sum(s["bytes"] for s in by_service.values()),
        "redactions": sum(s["redactions"] for s in by_service.values()),
        "by_service": by_service,
    }
