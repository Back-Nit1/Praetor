"""SQLite persistence for API-owned graphs, runs, and event streams."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.schemas import Event, ExposureGraph


class SqliteApiRepository:
    """Small persistence boundary so storage can evolve independently of routes."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None
        if self.path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = self._memory_connection or sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _close(self, connection: sqlite3.Connection) -> None:
        if connection is not self._memory_connection:
            connection.close()

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS graphs (
                    id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    graph_id TEXT,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY (run_id, sequence),
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );
                """
            )
            connection.commit()
        finally:
            self._close(connection)

    def put_graph(self, graph: ExposureGraph) -> None:
        connection = self._connect()
        try:
            connection.execute(
                "INSERT OR REPLACE INTO graphs(id, document) VALUES (?, ?)",
                (graph.id, graph.model_dump_json()),
            )
            connection.commit()
        finally:
            self._close(connection)

    def get_graph(self, graph_id: str) -> ExposureGraph | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT document FROM graphs WHERE id = ?", (graph_id,)).fetchone()
            return ExposureGraph.model_validate_json(row["document"]) if row else None
        finally:
            self._close(connection)

    def put_run(
        self,
        run_id: str,
        kind: str,
        graph_id: str | None,
        status: str,
        events: list[Event],
    ) -> None:
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO runs(id, kind, graph_id, status) VALUES (?, ?, ?, ?)",
                    (run_id, kind, graph_id, status),
                )
                connection.executemany(
                    "INSERT INTO events(run_id, sequence, document) VALUES (?, ?, ?)",
                    [(run_id, index, event.model_dump_json()) for index, event in enumerate(events)],
                )
        finally:
            self._close(connection)

    def has_run(self, run_id: str) -> bool:
        connection = self._connect()
        try:
            return connection.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone() is not None
        finally:
            self._close(connection)

    def get_events(self, run_id: str) -> list[Event]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT document FROM events WHERE run_id = ? ORDER BY sequence", (run_id,)
            ).fetchall()
            return [Event.model_validate(json.loads(row["document"])) for row in rows]
        finally:
            self._close(connection)
