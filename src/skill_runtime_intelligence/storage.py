"""SQLite storage for Skill Runtime Intelligence.

The database deliberately keeps source records, normalized events, deterministic
relationships, and inferences in separate layers. SkillRun is the primary query
entity; an agent session is only its runtime context.
"""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


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
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self._migrate_legacy_schema()

    def _migrate_legacy_schema(self) -> None:
        """Apply additive migrations and remove the old one-run-per-skill limit."""
        event_columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(normalized_events)")
        }
        if "skill_run_id" not in event_columns:
            self.connection.execute(
                "ALTER TABLE normalized_events ADD COLUMN skill_run_id TEXT"
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

    def replace_session(
        self,
        session: Dict[str, Any],
        raw: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        skill_runs: List[Dict[str, Any]],
    ) -> None:
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
                        parent_event_id, occurred_at, event_type, stage, status,
                        evidence_grade, confidence, basis, summary, source_locator,
                        payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        event["session_id"],
                        event.get("turn_id"),
                        event.get("skill_id"),
                        event.get("skill_run_id"),
                        event.get("parent_event_id"),
                        event.get("occurred_at"),
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
                    "observed" if direct_skill_evidence else "derived",
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

    def get_skill_run(self, skill_run_id: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            """
            SELECT sr.*, sk.name, sk.description, sk.source_path, sk.digest,
                   sk.source_kind, s.title AS session_title, s.cwd, s.model,
                   s.agent_version, s.adapter, s.adapter_version, s.source_path
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
            SELECT adapter, adapter_version, COUNT(*) AS session_count,
                   SUM(event_count) AS event_count,
                   MAX(indexed_at) AS last_indexed_at
            FROM sessions
            GROUP BY adapter, adapter_version
            ORDER BY session_count DESC, adapter
            """
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["capabilities"] = self.capabilities_for(item["adapter"])
            result.append(item)
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
            for table in (
                "sessions",
                "skills",
                "normalized_events",
                "skill_runs",
                "derived_relationships",
                "inferences",
            )
        }
