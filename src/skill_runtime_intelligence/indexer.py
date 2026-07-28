"""Index orchestration for local and observability adapters."""

import hashlib
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .adapters import CodexAdapter, ObservabilityAdapter
from .discovery import SkillDefinition, discover_skills
from .storage import Storage


def index_local(
    database: Path,
    codex_sessions: Path,
    skill_roots: Iterable[Path],
) -> Dict[str, int]:
    skills: List[SkillDefinition] = discover_skills(skill_roots)
    storage = Storage(database)
    try:
        storage.replace_skills(skill.to_dict() for skill in skills)
        adapter = CodexAdapter(codex_sessions)
        imported = 0
        failed = 0
        for source_path in adapter.session_files():
            try:
                session, raw, events, skill_runs = adapter.parse(source_path, skills)
                storage.replace_session(session, raw, events, skill_runs)
                imported += 1
            except (OSError, UnicodeError, ValueError):
                failed += 1
        counts = storage.counts()
        counts.update({"imported": imported, "failed": failed})
        return counts
    finally:
        storage.close()


def import_observability(
    database: Path,
    source_path: Path,
    profile: str = "auto",
) -> Dict[str, object]:
    """Import a vendor export through the canonical span adapter."""
    adapter = ObservabilityAdapter(source_path, profile)
    external_skills, bundles, detected_profile = adapter.parse()
    storage = Storage(database)
    try:
        storage.replace_skills(skill.to_dict() for skill in external_skills)
        imported = 0
        event_count = 0
        for session, raw, events, skill_runs in bundles:
            storage.replace_session(session, raw, events, skill_runs)
            imported += 1
            event_count += len(events)
        source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        storage.record_import(
            detected_profile,
            adapter.version,
            source_path,
            source_digest,
            imported,
            event_count,
        )
        result: Dict[str, object] = storage.counts()
        result.update(
            {
                "profile": detected_profile,
                "imported": imported,
                "imported_events": event_count,
                "external_skills": len(external_skills),
            }
        )
        return result
    finally:
        storage.close()


def watch_local(
    database: Path,
    codex_sessions: Path,
    skill_roots: Iterable[Path],
    interval_seconds: float = 2.0,
) -> None:
    """Continuously re-index only changed Codex session files.

    The source transcript remains authoritative. A changed session is parsed
    into a complete replacement transaction, so partial appends never leave a
    half-updated normalized graph.
    """
    roots = list(skill_roots)
    adapter = CodexAdapter(codex_sessions)
    known_mtimes: Dict[Path, int] = {}
    for path in adapter.session_files():
        try:
            known_mtimes[path] = path.stat().st_mtime_ns
        except OSError:
            continue
    skill_signature: Optional[str] = None
    skills: List[SkillDefinition] = []
    last_skill_scan = 0.0

    while True:
        now = time.monotonic()
        if not skills or now - last_skill_scan >= 30:
            discovered = discover_skills(roots)
            last_skill_scan = now
            next_signature = hashlib.sha256(
                "\0".join(
                    f"{skill.source_path}:{skill.digest}" for skill in discovered
                ).encode("utf-8")
            ).hexdigest()
            if next_signature != skill_signature:
                skills = discovered
                skill_signature = next_signature
                storage = Storage(database)
                try:
                    storage.replace_skills(skill.to_dict() for skill in skills)
                finally:
                    storage.close()

        changed = []
        current_paths = set(adapter.session_files())
        for path in current_paths:
            try:
                mtime = path.stat().st_mtime_ns
            except OSError:
                continue
            if known_mtimes.get(path) != mtime:
                known_mtimes[path] = mtime
                changed.append(path)
        for removed in set(known_mtimes) - current_paths:
            known_mtimes.pop(removed, None)

        if changed:
            storage = Storage(database)
            try:
                for source_path in changed:
                    try:
                        session, raw, events, skill_runs = adapter.parse(
                            source_path, skills
                        )
                        storage.replace_session(session, raw, events, skill_runs)
                    except (OSError, UnicodeError, ValueError):
                        continue
            finally:
                storage.close()
        time.sleep(max(0.5, interval_seconds))
