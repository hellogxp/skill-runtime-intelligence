"""SQLite storage with explicit raw, normalized, and derived layers."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    digest TEXT NOT NULL,
    valid INTEGER NOT NULL,
    validation_message TEXT NOT NULL,
    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    adapter TEXT NOT NULL,
    adapter_version TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    source_format_version TEXT NOT NULL,
    title TEXT NOT NULL,
    cwd TEXT NOT NULL,
    model TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    duration_ms INTEGER,
    status TEXT NOT NULL,
    completeness TEXT NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_source_records (
    raw_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    adapter TEXT NOT NULL,
    source_path TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    record_hash TEXT NOT NULL,
    occurred_at TEXT,
    record_type TEXT NOT NULL,
    redacted_envelope_json TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS normalized_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_id TEXT,
    skill_id TEXT,
    parent_event_id TEXT,
    occurred_at TEXT,
    event_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_grade TEXT NOT NULL,
    confidence REAL NOT NULL,
    basis TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS skill_runs (
    skill_run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    activation_mode TEXT NOT NULL,
    evidence_grade TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    basis TEXT NOT NULL,
    UNIQUE(session_id, skill_id),
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_session_time
    ON normalized_events(session_id, occurred_at, event_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON normalized_events(event_type);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
"""


class Storage:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def replace_skills(self, skills: Iterable[Dict[str, Any]]) -> None:
        with self.connection:
            for skill in skills:
                self.connection.execute(
                    """
                    INSERT INTO skills (
                        skill_id, name, description, source_kind, source_path,
                        digest, valid, validation_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_path) DO UPDATE SET
                        skill_id=excluded.skill_id,
                        name=excluded.name,
                        description=excluded.description,
                        source_kind=excluded.source_kind,
                        digest=excluded.digest,
                        valid=excluded.valid,
                        validation_message=excluded.validation_message,
                        indexed_at=CURRENT_TIMESTAMP
                    """,
                    (
                        skill["skill_id"],
                        skill["name"],
                        skill["description"],
                        skill["source_kind"],
                        skill["source_path"],
                        skill["digest"],
                        int(skill["valid"]),
                        skill["validation_message"],
                    ),
                )

    def replace_session(self, session: Dict[str, Any], raw: List[Dict[str, Any]],
                        events: List[Dict[str, Any]], skill_runs: List[Dict[str, Any]]) -> None:
        with self.connection:
            self.connection.execute(
                "DELETE FROM sessions WHERE session_id = ? OR source_path = ?",
                (session["session_id"], session["source_path"]),
            )
            columns = (
                "session_id", "adapter", "adapter_version", "source_path",
                "source_format_version", "title", "cwd", "model", "agent_version",
                "started_at", "ended_at", "duration_ms", "status", "completeness",
                "event_count",
            )
            self.connection.execute(
                f"INSERT INTO sessions ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                tuple(session.get(column) for column in columns),
            )
            for record in raw:
                self.connection.execute(
                    """
                    INSERT INTO raw_source_records (
                        raw_id, session_id, adapter, source_path, line_number,
                        record_hash, occurred_at, record_type, redacted_envelope_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["raw_id"], record["session_id"], record["adapter"],
                        record["source_path"], record["line_number"], record["record_hash"],
                        record.get("occurred_at"), record["record_type"],
                        record["redacted_envelope_json"],
                    ),
                )
            for event in events:
                self.connection.execute(
                    """
                    INSERT INTO normalized_events (
                        event_id, session_id, turn_id, skill_id, parent_event_id,
                        occurred_at, event_type, stage, status, evidence_grade,
                        confidence, basis, summary, source_locator, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"], event["session_id"], event.get("turn_id"),
                        event.get("skill_id"), event.get("parent_event_id"),
                        event.get("occurred_at"), event["event_type"], event["stage"],
                        event["status"], event["evidence_grade"], event["confidence"],
                        event["basis"], event["summary"], event["source_locator"],
                        json.dumps(event.get("payload", {}), ensure_ascii=False),
                    ),
                )
            for run in skill_runs:
                self.connection.execute(
                    """
                    INSERT INTO skill_runs (
                        skill_run_id, session_id, skill_id, activation_mode,
                        evidence_grade, status, started_at, ended_at, basis
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run["skill_run_id"], run["session_id"], run["skill_id"],
                        run["activation_mode"], run["evidence_grade"], run["status"],
                        run.get("started_at"), run.get("ended_at"), run["basis"],
                    ),
                )

    def list_runs(self, limit: int = 200) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT s.*,
                   GROUP_CONCAT(DISTINCT sk.name) AS skills,
                   COUNT(DISTINCT sr.skill_run_id) AS skill_count
            FROM sessions s
            LEFT JOIN skill_runs sr ON sr.session_id = s.session_id
            LEFT JOIN skills sk ON sk.skill_id = sr.skill_id
            GROUP BY s.session_id
            ORDER BY COALESCE(s.started_at, s.indexed_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, session_id: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        events = self.connection.execute(
            """
            SELECT e.*, sk.name AS skill_name
            FROM normalized_events e
            LEFT JOIN skills sk ON sk.skill_id = e.skill_id
            WHERE e.session_id = ?
            ORDER BY e.occurred_at, e.event_id
            """,
            (session_id,),
        ).fetchall()
        result["events"] = []
        for event in events:
            item = dict(event)
            item["payload"] = json.loads(item.pop("payload_json"))
            result["events"].append(item)
        result["skill_runs"] = [
            dict(item)
            for item in self.connection.execute(
                """
                SELECT sr.*, sk.name, sk.source_path
                FROM skill_runs sr
                JOIN skills sk ON sk.skill_id = sr.skill_id
                WHERE sr.session_id = ?
                ORDER BY sr.started_at, sk.name
                """,
                (session_id,),
            ).fetchall()
        ]
        return result

    def list_skills(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT sk.*, COUNT(sr.skill_run_id) AS observed_runs
            FROM skills sk
            LEFT JOIN skill_runs sr ON sr.skill_id = sk.skill_id
            GROUP BY sk.skill_id
            ORDER BY sk.name COLLATE NOCASE, sk.source_path
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def counts(self) -> Dict[str, int]:
        return {
            table: self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("sessions", "skills", "normalized_events", "skill_runs")
        }
