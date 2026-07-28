"""Index orchestration for local adapters."""

from pathlib import Path
from typing import Dict, Iterable, List

from .adapters import CodexAdapter
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
