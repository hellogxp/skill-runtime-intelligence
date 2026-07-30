"""SQLite storage for Skill Runtime Intelligence.

The database deliberately keeps source records, normalized events, deterministic
relationships, and inferences in separate layers. SkillRun is the primary query
entity; an agent session is only its runtime context.
"""

import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .comparison import build_comparison
from .diagnostics import diagnose_skill_run


_STORAGE_INIT_LOCK = threading.Lock()


STAGES = (
    "request",
    "discovery",
    "activation",
    "instructions",
    "resources",
    "execution",
    "artifacts",
    "outcome",
)

ADAPTER_CAPABILITIES = {
    "codex": {
        "request": "observed",
        "discovery": "unsupported",
        "activation": "partial",
        "instructions": "observed",
        "resources": "observed",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "partial",
    },
    "claude-code": {
        "request": "observed",
        "discovery": "unsupported",
        "activation": "observed",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "observed",
    },
    "qoder": {
        "request": "observed",
        "discovery": "unsupported",
        "activation": "observed",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "partial",
    },
    "opencode": {
        "request": "observed",
        "discovery": "unsupported",
        "activation": "observed",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "partial",
    },
    "otel": {
        "request": "partial",
        "discovery": "unsupported",
        "activation": "partial",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "observed",
    },
    "langfuse": {
        "request": "partial",
        "discovery": "unsupported",
        "activation": "partial",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "observed",
    },
    "langsmith": {
        "request": "partial",
        "discovery": "unsupported",
        "activation": "partial",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "observed",
    },
    "phoenix": {
        "request": "partial",
        "discovery": "unsupported",
        "activation": "partial",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "observed",
    },
    "weave": {
        "request": "partial",
        "discovery": "unsupported",
        "activation": "partial",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "observed",
    },
    "datadog": {
        "request": "partial",
        "discovery": "unsupported",
        "activation": "partial",
        "instructions": "partial",
        "resources": "partial",
        "execution": "observed",
        "artifacts": "partial",
        "outcome": "observed",
    },
}


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
    version TEXT NOT NULL DEFAULT '',
    compatibility TEXT NOT NULL DEFAULT '',
    resources_json TEXT NOT NULL DEFAULT '[]',
    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    adapter TEXT NOT NULL,
    adapter_version TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    source_format_version TEXT NOT NULL,
    source_session_id TEXT NOT NULL DEFAULT '',
    correlation_key TEXT NOT NULL DEFAULT '',
    collection_mode TEXT NOT NULL DEFAULT 'unknown',
    transport TEXT NOT NULL DEFAULT 'unknown',
    source_health TEXT NOT NULL DEFAULT 'unknown',
    last_event_at TEXT,
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

CREATE TABLE IF NOT EXISTS skill_runs (
    skill_run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_id TEXT,
    skill_id TEXT NOT NULL,
    run_index INTEGER NOT NULL DEFAULT 1,
    activation_mode TEXT NOT NULL,
    evidence_grade TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    basis TEXT NOT NULL,
    source_adapter TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS normalized_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_id TEXT,
    skill_id TEXT,
    skill_run_id TEXT,
    parent_event_id TEXT,
    occurred_at TEXT,
    timestamp_origin TEXT NOT NULL DEFAULT 'unknown',
    ingested_at TEXT,
    clock_domain TEXT NOT NULL DEFAULT 'unknown',
    clock_uncertainty_ms REAL,
    timestamp_precision TEXT NOT NULL DEFAULT 'unknown',
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

CREATE TABLE IF NOT EXISTS derived_relationships (
    relationship_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    skill_run_id TEXT,
    source_event_id TEXT,
    target_event_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    evidence_grade TEXT NOT NULL,
    confidence REAL NOT NULL,
    basis TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inferences (
    inference_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    skill_run_id TEXT,
    inference_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    basis TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS imports (
    import_id TEXT PRIMARY KEY,
    adapter TEXT NOT NULL,
    adapter_version TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_digest TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_count INTEGER NOT NULL,
    event_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO runtime_state (key, value) VALUES ('revision', '0');

CREATE INDEX IF NOT EXISTS idx_events_session_time
    ON normalized_events(session_id, occurred_at, event_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON normalized_events(event_type);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_runs_started ON skill_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_relationships_run
    ON derived_relationships(skill_run_id, target_event_id);
"""


def _relationship_id(*parts: Any) -> str:
    value = "\0".join("" if part is None else str(part) for part in parts)
    return "rel_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


class Storage:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        try:
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA busy_timeout = 5000")
            # Runtime startup intentionally initializes the live index and Hook
            # bridge in parallel. SQLite's journal-mode transition can fail
            # immediately when two fresh connections race, even with a busy
            # timeout. Serialize only schema/journal initialization; normal
            # reads and writes remain concurrent under WAL.
            with _STORAGE_INIT_LOCK:
                self.connection.execute("PRAGMA journal_mode = WAL")
                self.connection.executescript(SCHEMA)
                self._migrate_legacy_schema()
        except Exception:
            self.connection.close()
            raise

    def _migrate_legacy_schema(self) -> None:
        """Apply additive migrations and remove the old one-run-per-skill limit."""
        skill_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(skills)")
        }
        skill_additions = {
            "version": "TEXT NOT NULL DEFAULT ''",
            "compatibility": "TEXT NOT NULL DEFAULT ''",
            "resources_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, declaration in skill_additions.items():
            if column not in skill_columns:
                self.connection.execute(
                    f"ALTER TABLE skills ADD COLUMN {column} {declaration}"
                )
        session_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(sessions)")
        }
        session_additions = {
            "source_session_id": "TEXT NOT NULL DEFAULT ''",
            "correlation_key": "TEXT NOT NULL DEFAULT ''",
            "collection_mode": "TEXT NOT NULL DEFAULT 'unknown'",
            "transport": "TEXT NOT NULL DEFAULT 'unknown'",
            "source_health": "TEXT NOT NULL DEFAULT 'unknown'",
            "last_event_at": "TEXT",
        }
        for column, declaration in session_additions.items():
            if column not in session_columns:
                self.connection.execute(
                    f"ALTER TABLE sessions ADD COLUMN {column} {declaration}"
                )
        self.connection.execute(
            """
            UPDATE sessions
            SET source_session_id = CASE
                    WHEN source_session_id = '' THEN session_id
                    ELSE source_session_id
                END,
                correlation_key = CASE
                    WHEN correlation_key = '' THEN adapter || ':' || session_id
                    ELSE correlation_key
                END,
                collection_mode = CASE
                    WHEN adapter = 'codex' THEN 'transcript_fallback'
                    ELSE 'observability_import'
                END,
                transport = CASE
                    WHEN adapter = 'codex' THEN 'filesystem_watch'
                    ELSE 'file_import'
                END,
                source_health = CASE
                    WHEN adapter = 'codex' THEN 'active'
                    ELSE 'imported'
                END,
                last_event_at = COALESCE(last_event_at, ended_at, started_at, indexed_at)
            WHERE collection_mode = 'unknown'
            """
        )
        event_columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(normalized_events)")
        }
        event_additions = {
            "skill_run_id": "TEXT",
            "timestamp_origin": "TEXT NOT NULL DEFAULT 'unknown'",
            "ingested_at": "TEXT",
            "clock_domain": "TEXT NOT NULL DEFAULT 'unknown'",
            "clock_uncertainty_ms": "REAL",
            "timestamp_precision": "TEXT NOT NULL DEFAULT 'unknown'",
        }
        for column, declaration in event_additions.items():
            if column not in event_columns:
                self.connection.execute(
                    f"ALTER TABLE normalized_events ADD COLUMN {column} {declaration}"
                )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_skill_run "
            "ON normalized_events(skill_run_id, occurred_at, event_id)"
        )

        run_sql_row = self.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='skill_runs'"
        ).fetchone()
        run_sql = (run_sql_row["sql"] if run_sql_row else "") or ""
        required = {"turn_id", "run_index", "confidence", "source_adapter"}
        run_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(skill_runs)")
        }
        if "UNIQUE(session_id, skill_id)" in run_sql or not required.issubset(run_columns):
            self.connection.execute("PRAGMA foreign_keys = OFF")
            with self.connection:
                self.connection.execute("ALTER TABLE skill_runs RENAME TO skill_runs_legacy")
                self.connection.execute(
                    """
                    CREATE TABLE skill_runs (
                        skill_run_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        turn_id TEXT,
                        skill_id TEXT NOT NULL,
                        run_index INTEGER NOT NULL DEFAULT 1,
                        activation_mode TEXT NOT NULL,
                        evidence_grade TEXT NOT NULL,
                        confidence REAL NOT NULL DEFAULT 1.0,
                        status TEXT NOT NULL,
                        started_at TEXT,
                        ended_at TEXT,
                        basis TEXT NOT NULL,
                        source_adapter TEXT NOT NULL DEFAULT '',
                        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                        FOREIGN KEY(skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
                    )
                    """
                )
                legacy_columns = {
                    row["name"]
                    for row in self.connection.execute("PRAGMA table_info(skill_runs_legacy)")
                }
                if {"skill_run_id", "session_id", "skill_id"}.issubset(legacy_columns):
                    self.connection.execute(
                        """
                        INSERT INTO skill_runs (
                            skill_run_id, session_id, skill_id, activation_mode,
                            evidence_grade, status, started_at, ended_at, basis
                        )
                        SELECT skill_run_id, session_id, skill_id, activation_mode,
                               evidence_grade, status, started_at, ended_at, basis
                        FROM skill_runs_legacy
                        """
                    )
                self.connection.execute("DROP TABLE skill_runs_legacy")
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_skill_runs_started "
                "ON skill_runs(started_at DESC)"
            )
        self.connection.commit()

    @staticmethod
    def _source_defaults(session: Dict[str, Any]) -> Dict[str, str]:
        adapter = str(session.get("adapter") or "unknown")
        if adapter == "codex":
            return {
                "collection_mode": "transcript_fallback",
                "transport": "filesystem_watch",
                "source_health": "active",
            }
        return {
            "collection_mode": "observability_import",
            "transport": "file_import",
            "source_health": "imported",
        }

    def _bump_revision(self) -> int:
        self.connection.execute(
            """
            UPDATE runtime_state
            SET value = CAST(value AS INTEGER) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE key = 'revision'
            """
        )
        return self.revision()

    def revision(self) -> int:
        row = self.connection.execute(
            "SELECT value FROM runtime_state WHERE key = 'revision'"
        ).fetchone()
        return int(row["value"] if row else 0)

    def runtime_state(self, key: str, default: str = "") -> str:
        row = self.connection.execute(
            "SELECT value FROM runtime_state WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"]) if row else default

    def set_runtime_state(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO runtime_state (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (key, value),
            )

    @staticmethod
    def _collection_epoch_key(adapter: str) -> str:
        normalized = adapter.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", normalized):
            raise ValueError("invalid collection adapter identifier")
        return f"collection.{normalized}.epoch"

    def collection_epoch(self, adapter: str) -> Dict[str, Any]:
        value = self.runtime_state(self._collection_epoch_key(adapter), "")
        if not value:
            return {}
        try:
            result = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return result if isinstance(result, dict) else {}

    def begin_collection_epoch(
        self,
        adapter: str,
        *,
        source_count: int,
        changed_source_count: int,
        removed_source_count: int = 0,
        source_watermark_sha256: str,
    ) -> Dict[str, Any]:
        key = self._collection_epoch_key(adapter)
        previous = self.collection_epoch(adapter)
        epoch = int(previous.get("epoch", 0) or 0) + 1
        state = {
            "schema_version": "collection-epoch-v1",
            "adapter": adapter,
            "epoch": epoch,
            "status": "running",
            "source_count": max(0, int(source_count)),
            "changed_source_count": max(0, int(changed_source_count)),
            "removed_source_count": max(0, int(removed_source_count)),
            "processed_source_count": 0,
            "failed_source_count": 0,
            "late_arrival_count": 0,
            "source_watermark_sha256": str(source_watermark_sha256),
            "start_revision": self.revision(),
            "end_revision": None,
        }
        self.set_runtime_state(
            key,
            json.dumps(state, separators=(",", ":"), sort_keys=True),
        )
        return state

    def complete_collection_epoch(
        self,
        adapter: str,
        epoch: int,
        *,
        processed_source_count: int,
        failed_source_count: int,
        late_arrival_count: int,
        status: str = "completed",
    ) -> Dict[str, Any]:
        if status not in {"completed", "failed"}:
            raise ValueError("collection epoch status must be completed or failed")
        key = self._collection_epoch_key(adapter)
        state = self.collection_epoch(adapter)
        if not state or int(state.get("epoch", 0) or 0) != int(epoch):
            raise RuntimeError("collection epoch does not match active state")
        if state.get("status") != "running":
            raise RuntimeError("collection epoch is not running")
        state.update(
            {
                "status": status,
                "processed_source_count": max(
                    0, int(processed_source_count)
                ),
                "failed_source_count": max(0, int(failed_source_count)),
                "late_arrival_count": max(0, int(late_arrival_count)),
                "end_revision": self.revision(),
            }
        )
        self.set_runtime_state(
            key,
            json.dumps(state, separators=(",", ":"), sort_keys=True),
        )
        return state

    def list_runtime_state(self, prefix: str) -> List[Dict[str, str]]:
        rows = self.connection.execute(
            """
            SELECT key, value, updated_at FROM runtime_state
            WHERE key LIKE ?
            ORDER BY key
            """,
            (f"{prefix}%",),
        ).fetchall()
        return [dict(row) for row in rows]

    def export_events_after(
        self, row_id: int = 0, limit: int = 200
    ) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT e.rowid AS export_row_id, e.*, s.adapter, s.adapter_version,
                   s.source_session_id, s.model, s.agent_version, s.cwd,
                   sk.name AS skill_name
            FROM normalized_events e
            JOIN sessions s ON s.session_id = e.session_id
            LEFT JOIN skills sk ON sk.skill_id = e.skill_id
            WHERE e.rowid > ?
            ORDER BY e.rowid
            LIMIT ?
            """,
            (max(0, int(row_id)), max(1, min(int(limit), 2000))),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def replace_skills(self, skills: Iterable[Dict[str, Any]]) -> None:
        with self.connection:
            for skill in skills:
                self.connection.execute(
                    """
                    INSERT INTO skills (
                        skill_id, name, description, source_kind, source_path,
                        digest, valid, validation_message, version, compatibility,
                        resources_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_path) DO UPDATE SET
                        skill_id=excluded.skill_id,
                        name=excluded.name,
                        description=excluded.description,
                        source_kind=excluded.source_kind,
                        digest=excluded.digest,
                        valid=excluded.valid,
                        validation_message=excluded.validation_message,
                        version=excluded.version,
                        compatibility=excluded.compatibility,
                        resources_json=excluded.resources_json,
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
                        skill.get("version", ""),
                        skill.get("compatibility", ""),
                        json.dumps(skill.get("resources", []), ensure_ascii=False),
                    ),
                )
            self._bump_revision()

    def replace_session(
        self,
        session: Dict[str, Any],
        raw: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        skill_runs: List[Dict[str, Any]],
    ) -> None:
        session = dict(session)
        source_defaults = self._source_defaults(session)
        for key, value in source_defaults.items():
            session.setdefault(key, value)
        session.setdefault("source_session_id", session["session_id"])
        session.setdefault(
            "correlation_key",
            f"{session['adapter']}:{session['source_session_id']}",
        )
        session.setdefault(
            "last_event_at", session.get("ended_at") or session.get("started_at")
        )
        with self.connection:
            self.connection.execute(
                "DELETE FROM sessions WHERE session_id = ? OR source_path = ?",
                (session["session_id"], session["source_path"]),
            )
            columns = (
                "session_id",
                "adapter",
                "adapter_version",
                "source_path",
                "source_format_version",
                "source_session_id",
                "correlation_key",
                "collection_mode",
                "transport",
                "source_health",
                "last_event_at",
                "title",
                "cwd",
                "model",
                "agent_version",
                "started_at",
                "ended_at",
                "duration_ms",
                "status",
                "completeness",
                "event_count",
            )
            self.connection.execute(
                f"INSERT INTO sessions ({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
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
                        record["raw_id"],
                        record["session_id"],
                        record["adapter"],
                        record["source_path"],
                        record["line_number"],
                        record["record_hash"],
                        record.get("occurred_at"),
                        record["record_type"],
                        record["redacted_envelope_json"],
                    ),
                )
            for run in skill_runs:
                self.connection.execute(
                    """
                    INSERT INTO skill_runs (
                        skill_run_id, session_id, turn_id, skill_id, run_index,
                        activation_mode, evidence_grade, confidence, status,
                        started_at, ended_at, basis, source_adapter
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run["skill_run_id"],
                        run["session_id"],
                        run.get("turn_id"),
                        run["skill_id"],
                        run.get("run_index", 1),
                        run["activation_mode"],
                        run["evidence_grade"],
                        run.get("confidence", 1.0),
                        run["status"],
                        run.get("started_at"),
                        run.get("ended_at"),
                        run["basis"],
                        run.get("source_adapter", session["adapter"]),
                    ),
                )
            for event in events:
                self.connection.execute(
                    """
                    INSERT INTO normalized_events (
                        event_id, session_id, turn_id, skill_id, skill_run_id,
                        parent_event_id, occurred_at, timestamp_origin, ingested_at,
                        clock_domain, clock_uncertainty_ms, timestamp_precision,
                        event_type, stage, status,
                        evidence_grade, confidence, basis, summary, source_locator,
                        payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        event["session_id"],
                        event.get("turn_id"),
                        event.get("skill_id"),
                        event.get("skill_run_id"),
                        event.get("parent_event_id"),
                        event.get("occurred_at"),
                        event.get("timestamp_origin", "unknown"),
                        event.get("ingested_at"),
                        event.get("clock_domain", "unknown"),
                        event.get("clock_uncertainty_ms"),
                        event.get("timestamp_precision", "unknown"),
                        event["event_type"],
                        event["stage"],
                        event["status"],
                        event["evidence_grade"],
                        event["confidence"],
                        event["basis"],
                        event["summary"],
                        event["source_locator"],
                        json.dumps(event.get("payload", {}), ensure_ascii=False),
                    ),
                )
            self._build_relationships(session["session_id"], events, skill_runs)
            self._bump_revision()

    def append_collector_events(
        self, bundles: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Append immutable live events from native telemetry, hooks, or an SDK.

        The caller provides validated, redacted bundles. Event IDs make the
        operation idempotent, and relationships are rebuilt from all evidence
        for each affected session after the append completes.
        """
        accepted = 0
        duplicates = 0
        affected_sessions = set()
        with self.connection:
            for bundle in bundles:
                session = bundle["session"]
                event = dict(bundle["event"])
                raw = bundle["raw"]
                skill = bundle.get("skill")
                run = bundle.get("skill_run")

                if skill:
                    self.connection.execute(
                        """
                        INSERT INTO skills (
                            skill_id, name, description, source_kind, source_path,
                            digest, valid, validation_message, version,
                            compatibility, resources_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(source_path) DO UPDATE SET
                            name=excluded.name,
                            description=CASE
                                WHEN excluded.description = '' THEN skills.description
                                ELSE excluded.description
                            END,
                            digest=excluded.digest,
                            version=CASE
                                WHEN excluded.version = '' THEN skills.version
                                ELSE excluded.version
                            END,
                            compatibility=CASE
                                WHEN excluded.compatibility = '' THEN skills.compatibility
                                ELSE excluded.compatibility
                            END,
                            resources_json=CASE
                                WHEN excluded.resources_json = '[]' THEN skills.resources_json
                                ELSE excluded.resources_json
                            END,
                            indexed_at=CURRENT_TIMESTAMP
                        """,
                        (
                            skill["skill_id"],
                            skill["name"],
                            skill.get("description", ""),
                            skill.get("source_kind", "runtime"),
                            skill["source_path"],
                            skill["digest"],
                            int(skill.get("valid", True)),
                            skill.get("validation_message", ""),
                            skill.get("version", ""),
                            skill.get("compatibility", ""),
                            json.dumps(skill.get("resources", []), ensure_ascii=False),
                        ),
                    )

                existing_session = self.connection.execute(
                    "SELECT session_id FROM sessions WHERE session_id = ?",
                    (session["session_id"],),
                ).fetchone()
                if existing_session:
                    self.connection.execute(
                        """
                        UPDATE sessions
                        SET adapter = ?, adapter_version = ?,
                            collection_mode = ?, transport = ?,
                            source_health = ?, last_event_at = ?,
                            status = CASE
                                WHEN ? IN ('completed', 'failed', 'interrupted')
                                    THEN ?
                                ELSE status
                            END,
                            completeness = CASE
                                WHEN ? = 'complete' THEN 'complete'
                                ELSE completeness
                            END,
                            ended_at = COALESCE(?, ended_at),
                            title = CASE WHEN title = '' THEN ? ELSE title END,
                            cwd = CASE WHEN cwd = '' THEN ? ELSE cwd END,
                            model = CASE WHEN model = '' THEN ? ELSE model END,
                            agent_version = CASE
                                WHEN agent_version = '' THEN ? ELSE agent_version
                            END
                        WHERE session_id = ?
                        """,
                        (
                            session["adapter"],
                            session["adapter_version"],
                            session["collection_mode"],
                            session["transport"],
                            session["source_health"],
                            event.get("occurred_at"),
                            session["status"],
                            session["status"],
                            session["completeness"],
                            session.get("ended_at"),
                            session["title"],
                            session["cwd"],
                            session["model"],
                            session["agent_version"],
                            session["session_id"],
                        ),
                    )
                else:
                    columns = (
                        "session_id",
                        "adapter",
                        "adapter_version",
                        "source_path",
                        "source_format_version",
                        "source_session_id",
                        "correlation_key",
                        "collection_mode",
                        "transport",
                        "source_health",
                        "last_event_at",
                        "title",
                        "cwd",
                        "model",
                        "agent_version",
                        "started_at",
                        "ended_at",
                        "duration_ms",
                        "status",
                        "completeness",
                        "event_count",
                    )
                    self.connection.execute(
                        f"INSERT INTO sessions ({','.join(columns)}) "
                        f"VALUES ({','.join('?' for _ in columns)})",
                        tuple(session.get(column) for column in columns),
                    )

                if run:
                    self.connection.execute(
                        """
                        INSERT INTO skill_runs (
                            skill_run_id, session_id, turn_id, skill_id, run_index,
                            activation_mode, evidence_grade, confidence, status,
                            started_at, ended_at, basis, source_adapter
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(skill_run_id) DO UPDATE SET
                            status = CASE
                                WHEN excluded.status IN ('failed', 'completed', 'interrupted')
                                    THEN excluded.status
                                ELSE skill_runs.status
                            END,
                            ended_at = COALESCE(excluded.ended_at, skill_runs.ended_at),
                            evidence_grade = CASE
                                WHEN skill_runs.evidence_grade = 'observed'
                                    THEN skill_runs.evidence_grade
                                ELSE excluded.evidence_grade
                            END,
                            confidence = MAX(skill_runs.confidence, excluded.confidence)
                        """,
                        (
                            run["skill_run_id"],
                            run["session_id"],
                            run.get("turn_id"),
                            run["skill_id"],
                            run.get("run_index", 1),
                            run["activation_mode"],
                            run["evidence_grade"],
                            run.get("confidence", 1.0),
                            run["status"],
                            run.get("started_at"),
                            run.get("ended_at"),
                            run["basis"],
                            run.get("source_adapter", session["adapter"]),
                        ),
                    )
                elif event.get("skill_run_id") and not event.get("skill_id"):
                    run_row = self.connection.execute(
                        "SELECT skill_id FROM skill_runs WHERE skill_run_id = ?",
                        (event["skill_run_id"],),
                    ).fetchone()
                    if run_row:
                        event["skill_id"] = run_row["skill_id"]

                raw_result = self.connection.execute(
                    """
                    INSERT OR IGNORE INTO raw_source_records (
                        raw_id, session_id, adapter, source_path, line_number,
                        record_hash, occurred_at, record_type, redacted_envelope_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        raw["raw_id"],
                        raw["session_id"],
                        raw["adapter"],
                        raw["source_path"],
                        raw["line_number"],
                        raw["record_hash"],
                        raw.get("occurred_at"),
                        raw["record_type"],
                        raw["redacted_envelope_json"],
                    ),
                )
                event_result = self.connection.execute(
                    """
                    INSERT OR IGNORE INTO normalized_events (
                        event_id, session_id, turn_id, skill_id, skill_run_id,
                        parent_event_id, occurred_at, timestamp_origin, ingested_at,
                        clock_domain, clock_uncertainty_ms, timestamp_precision,
                        event_type, stage, status,
                        evidence_grade, confidence, basis, summary, source_locator,
                        payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        event["session_id"],
                        event.get("turn_id"),
                        event.get("skill_id"),
                        event.get("skill_run_id"),
                        event.get("parent_event_id"),
                        event.get("occurred_at"),
                        event.get("timestamp_origin", "unknown"),
                        event.get("ingested_at"),
                        event.get("clock_domain", "unknown"),
                        event.get("clock_uncertainty_ms"),
                        event.get("timestamp_precision", "unknown"),
                        event["event_type"],
                        event["stage"],
                        event["status"],
                        event["evidence_grade"],
                        event["confidence"],
                        event["basis"],
                        event["summary"],
                        event["source_locator"],
                        json.dumps(event.get("payload", {}), ensure_ascii=False),
                    ),
                )
                if event_result.rowcount:
                    accepted += 1
                else:
                    duplicates += 1
                if not raw_result.rowcount and event_result.rowcount:
                    raise RuntimeError("collector raw/event idempotency diverged")
                affected_sessions.add(session["session_id"])

            for session_id in affected_sessions:
                self.connection.execute(
                    """
                    UPDATE sessions
                    SET event_count = (
                            SELECT COUNT(*) FROM normalized_events
                            WHERE session_id = ?
                        ),
                        started_at = COALESCE(
                            started_at,
                            (SELECT MIN(occurred_at) FROM normalized_events
                             WHERE session_id = ?)
                        )
                    WHERE session_id = ?
                    """,
                    (session_id, session_id, session_id),
                )
                self._rebuild_session_relationships(session_id)
            if accepted:
                self._bump_revision()
        return {"accepted": accepted, "duplicates": duplicates}

    def _rebuild_session_relationships(self, session_id: str) -> None:
        events = []
        for row in self.connection.execute(
            "SELECT * FROM normalized_events WHERE session_id = ?",
            (session_id,),
        ).fetchall():
            event = dict(row)
            event["payload"] = json.loads(event.pop("payload_json"))
            events.append(event)
        runs = [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM skill_runs WHERE session_id = ?", (session_id,)
            ).fetchall()
        ]
        self._build_relationships(session_id, events, runs)

    def _build_relationships(
        self,
        session_id: str,
        events: List[Dict[str, Any]],
        skill_runs: List[Dict[str, Any]],
    ) -> None:
        self.connection.execute(
            "DELETE FROM derived_relationships WHERE session_id = ?", (session_id,)
        )
        for event in events:
            skill_run_id = event.get("skill_run_id")
            parent_event_id = event.get("parent_event_id")
            if parent_event_id:
                self._insert_relationship(
                    session_id,
                    skill_run_id,
                    parent_event_id,
                    event["event_id"],
                    "source_parent",
                    "derived",
                    1.0,
                    "Deterministic source parent/call identifier match",
                )
            if skill_run_id:
                direct_skill_evidence = event["event_type"].startswith(
                    ("skill.", "instruction.", "resource.")
                )
                self._insert_relationship(
                    session_id,
                    skill_run_id,
                    None,
                    event["event_id"],
                    "skill_scope",
                    (
                        event.get("evidence_grade", "derived")
                        if direct_skill_evidence
                        else "derived"
                    ),
                    1.0,
                    (
                        "Event directly names or accesses the Skill"
                        if direct_skill_evidence
                        else "Event occurred inside the active Skill scope"
                    ),
                )
        for run in skill_runs:
            for event in events:
                if event["stage"] not in {"request", "outcome"}:
                    continue
                same_turn = (
                    run.get("turn_id")
                    and event.get("turn_id") == run.get("turn_id")
                )
                session_level = not run.get("turn_id") and not event.get("turn_id")
                if not (same_turn or session_level):
                    continue
                self._insert_relationship(
                    session_id,
                    run["skill_run_id"],
                    None,
                    event["event_id"],
                    "runtime_context",
                    "derived",
                    1.0,
                    "Request/outcome event shares the SkillRun turn boundary",
                )

    def _insert_relationship(
        self,
        session_id: str,
        skill_run_id: Optional[str],
        source_event_id: Optional[str],
        target_event_id: str,
        relationship_type: str,
        evidence_grade: str,
        confidence: float,
        basis: str,
    ) -> None:
        relationship_id = _relationship_id(
            session_id,
            skill_run_id,
            source_event_id,
            target_event_id,
            relationship_type,
        )
        self.connection.execute(
            """
            INSERT OR REPLACE INTO derived_relationships (
                relationship_id, session_id, skill_run_id, source_event_id,
                target_event_id, relationship_type, evidence_grade, confidence, basis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relationship_id,
                session_id,
                skill_run_id,
                source_event_id,
                target_event_id,
                relationship_type,
                evidence_grade,
                confidence,
                basis,
            ),
        )

    def record_import(
        self,
        adapter: str,
        adapter_version: str,
        source_path: Path,
        source_digest: str,
        session_count: int,
        event_count: int,
    ) -> None:
        import_id = _relationship_id(adapter, source_path.resolve(), source_digest)
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO imports (
                    import_id, adapter, adapter_version, source_path, source_digest,
                    session_count, event_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_id,
                    adapter,
                    adapter_version,
                    str(source_path.resolve()),
                    source_digest,
                    session_count,
                    event_count,
                ),
            )
            self._bump_revision()

    def list_runs(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Compatibility session list. The main UI uses list_skill_runs."""
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

    def list_skill_runs(self, limit: int = 300) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT sr.*, sk.name, sk.description, sk.source_path, sk.digest,
                   s.title AS session_title, s.cwd, s.model, s.agent_version,
                   s.adapter, s.duration_ms AS session_duration_ms,
                   COUNT(DISTINCT e.event_id) AS event_count,
                   COUNT(DISTINCT CASE WHEN e.stage = 'execution' THEN e.event_id END)
                       AS execution_count,
                   COUNT(DISTINCT CASE WHEN e.stage = 'artifacts' THEN e.event_id END)
                       AS artifact_count,
                   COUNT(DISTINCT CASE WHEN e.status = 'failed' THEN e.event_id END)
                       AS error_count
            FROM skill_runs sr
            JOIN skills sk ON sk.skill_id = sr.skill_id
            JOIN sessions s ON s.session_id = sr.session_id
            LEFT JOIN normalized_events e ON e.skill_run_id = sr.skill_run_id
            GROUP BY sr.skill_run_id
            ORDER BY COALESCE(sr.started_at, s.started_at, s.indexed_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            stage_summary = self._stage_summary(
                item["skill_run_id"], item["adapter"]
            )
            item["stage_summary"] = stage_summary
            item["evidence_completeness"] = self._evidence_completeness(stage_summary)
            item["first_gap"] = self._first_gap(stage_summary)
            result.append(item)
        return result

    def compare_skill_runs(
        self,
        left_skill_run_id: str,
        right_skill_run_id: str,
        *,
        axis: str = "same_skill",
        task_aligned: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        left = self.get_skill_run(left_skill_run_id)
        right = self.get_skill_run(right_skill_run_id)
        if left is None or right is None:
            return None

        comparison = build_comparison(
            left,
            right,
            axis=axis,
            task_aligned=task_aligned,
        )
        stages = comparison["stages"]

        def event_type_counts(run: Dict[str, Any]) -> Dict[str, int]:
            result: Dict[str, int] = {}
            for event in run["events"]:
                event_type = event["event_type"]
                result[event_type] = result.get(event_type, 0) + 1
            return result

        left_counts = event_type_counts(left)
        right_counts = event_type_counts(right)
        event_types = []
        for event_type in sorted(set(left_counts) | set(right_counts)):
            left_count = left_counts.get(event_type, 0)
            right_count = right_counts.get(event_type, 0)
            event_types.append(
                {
                    "event_type": event_type,
                    "left_count": left_count,
                    "right_count": right_count,
                    "delta": right_count - left_count,
                }
            )

        def summary(run: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "skill_run_id": run["skill_run_id"],
                "skill": run["name"],
                "skill_digest": run["digest"],
                "agent": run["adapter"],
                "agent_version": run["agent_version"],
                "model": run["model"],
                "status": run["status"],
                "activation_mode": run["activation_mode"],
                "evidence_grade": run["evidence_grade"],
                "evidence_completeness": run["evidence_completeness"],
                "first_gap": run["first_gap"],
                "started_at": run["started_at"],
                "duration_ms": run["session_duration_ms"],
            }

        comparable = [stage for stage in stages if stage["comparability"] == "comparable"]
        changed = [stage for stage in comparable if stage["changed"]]
        limited = [stage for stage in stages if stage["comparability"] != "comparable"]
        comparison.update({
            "left": summary(left),
            "right": summary(right),
            "comparable_stage_count": len(comparable),
            "changed_stage_count": len(changed),
            "limited_stage_count": len(limited),
            "first_changed_stage": changed[0]["stage"] if changed else None,
            "stages": stages,
            "event_types": event_types,
            "discipline": (
                "Only stages with equivalent adapter capability are classified "
                "as behavioral differences. Masked dimensions remain available "
                "for side-by-side evidence inspection only."
            ),
        })
        return comparison

    def get_skill_run(self, skill_run_id: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            """
            SELECT sr.*, sk.name, sk.description, sk.source_path, sk.digest,
                   sk.source_kind, sk.version AS skill_version,
                   s.title AS session_title, s.cwd, s.model,
                   s.agent_version, s.adapter, s.adapter_version,
                   s.source_session_id, s.correlation_key, s.source_path
                       AS session_source_path,
                   s.duration_ms AS session_duration_ms, s.completeness
                       AS session_completeness
            FROM skill_runs sr
            JOIN skills sk ON sk.skill_id = sr.skill_id
            JOIN sessions s ON s.session_id = sr.session_id
            WHERE sr.skill_run_id = ?
            """,
            (skill_run_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        events = self.connection.execute(
            """
            SELECT e.*, sk.name AS skill_name,
                   CASE WHEN e.skill_run_id = ? THEN 0 ELSE 1 END AS context_only
            FROM normalized_events e
            LEFT JOIN skills sk ON sk.skill_id = e.skill_id
            WHERE EXISTS (
                SELECT 1 FROM derived_relationships r
                WHERE r.skill_run_id = ? AND r.target_event_id = e.event_id
            )
            ORDER BY e.occurred_at, e.event_id
            """,
            (
                skill_run_id,
                skill_run_id,
            ),
        ).fetchall()
        result["events"] = []
        for event in events:
            item = dict(event)
            item["payload"] = json.loads(item.pop("payload_json"))
            result["events"].append(item)
        result["relationships"] = [
            dict(item)
            for item in self.connection.execute(
                """
                SELECT * FROM derived_relationships
                WHERE skill_run_id = ?
                ORDER BY relationship_type, target_event_id
                """,
                (skill_run_id,),
            ).fetchall()
        ]
        result["inferences"] = [
            {
                **dict(item),
                "payload": json.loads(item["payload_json"]),
            }
            for item in self.connection.execute(
                "SELECT * FROM inferences WHERE skill_run_id = ?",
                (skill_run_id,),
            ).fetchall()
        ]
        result["stage_summary"] = self._stage_summary(
            skill_run_id, result["adapter"]
        )
        result["evidence_completeness"] = self._evidence_completeness(
            result["stage_summary"]
        )
        result["first_gap"] = self._first_gap(result["stage_summary"])
        result["narrative"] = self._narrative(result)
        result["adapter_capabilities"] = self.capabilities_for(result["adapter"])
        result["findings"] = diagnose_skill_run(result)
        return result

    def get_run(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Compatibility session detail endpoint."""
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

    def _stage_summary(self, skill_run_id: str, adapter: str) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT stage, COUNT(*) AS event_count,
                   SUM(CASE WHEN evidence_grade = 'observed' THEN 1 ELSE 0 END)
                       AS observed_count,
                   SUM(CASE WHEN evidence_grade = 'derived' THEN 1 ELSE 0 END)
                       AS derived_count,
                   SUM(CASE WHEN evidence_grade = 'inferred' THEN 1 ELSE 0 END)
                       AS inferred_count,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
                       AS failed_count
            FROM normalized_events e
            WHERE EXISTS (
                SELECT 1 FROM derived_relationships r
                WHERE r.skill_run_id = ? AND r.target_event_id = e.event_id
            )
            GROUP BY stage
            """,
            (skill_run_id,),
        ).fetchall()
        by_stage = {row["stage"]: dict(row) for row in rows}
        capabilities = self.capabilities_for(adapter)
        result = []
        for stage in STAGES:
            values = by_stage.get(stage, {})
            count = int(values.get("event_count") or 0)
            capability = capabilities.get(stage, "unsupported")
            if count:
                status = "failed" if values.get("failed_count") else "observed"
                grades = [
                    grade
                    for grade in ("observed", "derived", "inferred")
                    if values.get(f"{grade}_count")
                ]
                grade = grades[0] if grades else "observed"
            elif capability == "unsupported":
                status = "unsupported"
                grade = None
            else:
                status = "not_observed"
                grade = None
            result.append(
                {
                    "stage": stage,
                    "status": status,
                    "capability": capability,
                    "event_count": count,
                    "evidence_grade": grade,
                }
            )
        return result

    @staticmethod
    def _evidence_completeness(stage_summary: List[Dict[str, Any]]) -> int:
        observable = [
            stage for stage in stage_summary if stage["capability"] != "unsupported"
        ]
        if not observable:
            return 0
        observed = sum(stage["event_count"] > 0 for stage in observable)
        return round(observed * 100 / len(observable))

    @staticmethod
    def _first_gap(stage_summary: List[Dict[str, Any]]) -> Optional[str]:
        for stage in stage_summary:
            if stage["status"] == "not_observed":
                return stage["stage"]
        return None

    @staticmethod
    def _narrative(run: Dict[str, Any]) -> str:
        counts = {item["stage"]: item["event_count"] for item in run["stage_summary"]}
        fragments = [f"Skill `{run['name']}` has runtime evidence in this run."]
        if counts["activation"]:
            fragments.append(f"Activation evidence: {counts['activation']}.")
        elif run["activation_mode"] == "unknown":
            fragments.append("Activation mode was not exposed by the source.")
        if counts["instructions"]:
            fragments.append("Its primary instructions were loaded.")
        if counts["resources"]:
            fragments.append(f"{counts['resources']} resource access event(s) were observed.")
        if counts["execution"]:
            fragments.append(f"{counts['execution']} execution event(s) were attributed.")
        if counts["artifacts"]:
            fragments.append(f"{counts['artifacts']} file or artifact event(s) were connected.")
        if run.get("first_gap"):
            fragments.append(
                f"The first observable lifecycle gap is `{run['first_gap']}`; "
                "this is missing evidence, not proof of failure."
            )
        return " ".join(fragments)

    @staticmethod
    def capabilities_for(adapter: str) -> Dict[str, str]:
        return dict(ADAPTER_CAPABILITIES.get(adapter, ADAPTER_CAPABILITIES["otel"]))

    def list_sources(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT adapter, adapter_version, collection_mode, transport,
                   source_health, COUNT(*) AS session_count,
                   SUM(event_count) AS event_count,
                   MAX(indexed_at) AS last_indexed_at,
                   MAX(last_event_at) AS last_event_at
            FROM sessions
            GROUP BY adapter, adapter_version, collection_mode, transport,
                     source_health
            ORDER BY session_count DESC, adapter
            """
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["capabilities"] = self.capabilities_for(item["adapter"])
            item["live"] = item["collection_mode"] in {
                "native_telemetry",
                "official_hook",
                "lightweight_hook",
                "sdk",
                "transcript_fallback",
            }
            item["role"] = (
                "fallback"
                if item["collection_mode"] == "transcript_fallback"
                else (
                    "import"
                    if item["collection_mode"] == "observability_import"
                    else "primary"
                )
            )
            result.append(item)
        return result

    def list_skills(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT sk.*, COUNT(sr.skill_run_id) AS observed_runs,
                   COUNT(DISTINCT s.adapter) AS observed_agent_count,
                   GROUP_CONCAT(DISTINCT s.adapter) AS observed_agents,
                   MAX(sr.started_at) AS last_observed_at,
                   SUM(CASE WHEN sr.status = 'failed' THEN 1 ELSE 0 END)
                       AS failed_runs
            FROM skills sk
            LEFT JOIN skill_runs sr ON sr.skill_id = sk.skill_id
            LEFT JOIN sessions s ON s.session_id = sr.session_id
            GROUP BY sk.skill_id
            ORDER BY sk.name COLLATE NOCASE, sk.source_path
            """
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["resources"] = json.loads(item.pop("resources_json"))
            except (TypeError, json.JSONDecodeError):
                item["resources"] = []
            item["observed_agents"] = [
                value for value in str(item["observed_agents"] or "").split(",")
                if value
            ]
            item["resource_counts"] = {
                kind: sum(
                    resource.get("kind") == kind
                    for resource in item["resources"]
                    if isinstance(resource, dict)
                )
                for kind in ("script", "reference", "asset")
            }
            item["activation_observation"] = (
                "observed" if item["observed_runs"] else "not_observed"
            )
            result.append(item)
        return result

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        skill = next(
            (item for item in self.list_skills() if item["skill_id"] == skill_id),
            None,
        )
        if skill is None:
            return None
        skill["recent_runs"] = [
            dict(row)
            for row in self.connection.execute(
                """
                SELECT sr.skill_run_id, sr.status, sr.activation_mode,
                       sr.started_at, sr.evidence_grade, s.adapter, s.model,
                       s.cwd, s.title AS session_title
                FROM skill_runs sr
                JOIN sessions s ON s.session_id = sr.session_id
                WHERE sr.skill_id = ?
                ORDER BY COALESCE(sr.started_at, s.started_at) DESC
                LIMIT 30
                """,
                (skill_id,),
            ).fetchall()
        ]
        return skill

    def compare_skill_definitions(
        self, left_skill_id: str, right_skill_id: str
    ) -> Optional[Dict[str, Any]]:
        """Compare two installed definitions without implying runtime causality."""
        left = next(
            (
                item
                for item in self.list_skills()
                if item["skill_id"] == left_skill_id
            ),
            None,
        )
        right = next(
            (
                item
                for item in self.list_skills()
                if item["skill_id"] == right_skill_id
            ),
            None,
        )
        if left is None or right is None:
            return None

        def resource_identity(resource: Dict[str, Any]) -> tuple:
            return (
                str(resource.get("kind") or ""),
                str(resource.get("path") or ""),
                int(resource.get("bytes") or 0),
            )

        left_resources = {
            resource_identity(resource)
            for resource in left.get("resources", [])
            if isinstance(resource, dict)
        }
        right_resources = {
            resource_identity(resource)
            for resource in right.get("resources", [])
            if isinstance(resource, dict)
        }

        def resource_dict(identity: tuple) -> Dict[str, Any]:
            kind, path, size = identity
            return {"kind": kind, "path": path, "bytes": size}

        fields = {}
        for field in (
            "name",
            "description",
            "version",
            "compatibility",
            "digest",
            "source_kind",
            "source_path",
            "valid",
        ):
            fields[field] = {
                "left": left.get(field),
                "right": right.get(field),
                "changed": left.get(field) != right.get(field),
            }
        changed_fields = [
            field for field, values in fields.items() if values["changed"]
        ]
        resources_added = [
            resource_dict(item) for item in sorted(right_resources - left_resources)
        ]
        resources_removed = [
            resource_dict(item) for item in sorted(left_resources - right_resources)
        ]
        return {
            "left": {
                "skill_id": left_skill_id,
                "name": left["name"],
                "version": left["version"],
                "digest": left["digest"],
            },
            "right": {
                "skill_id": right_skill_id,
                "name": right["name"],
                "version": right["version"],
                "digest": right["digest"],
            },
            "same_name": left["name"].casefold() == right["name"].casefold(),
            "same_digest": left["digest"] == right["digest"],
            "changed_fields": changed_fields,
            "fields": fields,
            "resources_added": resources_added,
            "resources_removed": resources_removed,
            "evidence_grade": "observed",
            "basis": (
                "Direct comparison of indexed Skill definition metadata and "
                "resource identities; resource contents are not stored."
            ),
        }

    def skill_conflicts(self, minimum_overlap: float = 0.25) -> List[Dict[str, Any]]:
        """Return description-overlap candidates as explicitly inferred evidence."""
        stopwords = {
            "the", "and", "for", "with", "from", "this", "that", "when",
            "use", "using", "skill", "agent", "user", "to", "of", "a", "an",
            "or", "in", "on", "is", "are",
        }
        skills = self.list_skills()
        tokens = {}
        for skill in skills:
            values = {
                token.casefold()
                for token in re.findall(r"[\w-]{3,}", skill["description"])
                if token.casefold() not in stopwords
            }
            tokens[skill["skill_id"]] = values
        result = []
        for left_index, left in enumerate(skills):
            for right in skills[left_index + 1:]:
                if left["name"].casefold() == right["name"].casefold():
                    continue
                union = tokens[left["skill_id"]] | tokens[right["skill_id"]]
                overlap = tokens[left["skill_id"]] & tokens[right["skill_id"]]
                score = len(overlap) / len(union) if union else 0.0
                if score < minimum_overlap:
                    continue
                result.append(
                    {
                        "left": {
                            "skill_id": left["skill_id"],
                            "name": left["name"],
                        },
                        "right": {
                            "skill_id": right["skill_id"],
                            "name": right["name"],
                        },
                        "overlap": round(score, 3),
                        "shared_terms": sorted(overlap)[:12],
                        "evidence_grade": "inferred",
                        "confidence": round(min(0.85, 0.45 + score / 2), 3),
                        "basis": (
                            "Installed Skill descriptions share trigger-like terms; "
                            "candidate matching is not exposed by the Agent."
                        ),
                    }
                )
        return sorted(result, key=lambda item: item["overlap"], reverse=True)

    def delete_skill_run(self, skill_run_id: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            "SELECT session_id FROM skill_runs WHERE skill_run_id = ?",
            (skill_run_id,),
        ).fetchone()
        if row is None:
            return None
        session_id = row["session_id"]
        with self.connection:
            self.connection.execute(
                "DELETE FROM inferences WHERE skill_run_id = ?", (skill_run_id,)
            )
            self.connection.execute(
                "DELETE FROM derived_relationships WHERE skill_run_id = ?",
                (skill_run_id,),
            )
            self.connection.execute(
                "DELETE FROM normalized_events WHERE skill_run_id = ?",
                (skill_run_id,),
            )
            self.connection.execute(
                "DELETE FROM skill_runs WHERE skill_run_id = ?", (skill_run_id,)
            )
            remaining = self.connection.execute(
                "SELECT COUNT(*) FROM skill_runs WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
            session_deleted = remaining == 0
            if session_deleted:
                self.connection.execute(
                    "DELETE FROM sessions WHERE session_id = ?", (session_id,)
                )
            self._bump_revision()
        return {
            "skill_run_id": skill_run_id,
            "session_id": session_id,
            "session_deleted": session_deleted,
            "source_transcript_deleted": False,
        }

    def purge_expired(
        self,
        retention_days: int,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Apply the local retention policy to indexed records only."""
        days = int(retention_days)
        if days < 1:
            raise ValueError("retention_days must be at least 1")
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        cutoff = (reference.astimezone(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self.connection.execute(
            """
            SELECT session_id
            FROM sessions
            WHERE julianday(
                COALESCE(ended_at, last_event_at, started_at, indexed_at)
            ) < julianday(?)
            """,
            (cutoff,),
        ).fetchall()
        session_ids = [row["session_id"] for row in rows]
        if session_ids:
            with self.connection:
                self.connection.executemany(
                    "DELETE FROM sessions WHERE session_id = ?",
                    [(session_id,) for session_id in session_ids],
                )
                self._bump_revision()
        return {
            "retention_days": days,
            "cutoff": cutoff,
            "sessions_deleted": len(session_ids),
            "source_transcripts_deleted": False,
        }

    def counts(self) -> Dict[str, int]:
        return {
            table: self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "sessions",
                "skills",
                "normalized_events",
                "skill_runs",
                "derived_relationships",
                "inferences",
            )
        }
