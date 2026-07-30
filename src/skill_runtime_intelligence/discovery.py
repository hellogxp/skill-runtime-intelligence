"""Agent Skill filesystem discovery."""

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import path_is_excluded


FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    source_kind: str
    source_path: str
    digest: str
    valid: bool
    validation_message: str
    version: str = ""
    compatibility: str = ""
    resources: Tuple[Dict[str, Any], ...] = ()

    def to_dict(self):
        return asdict(self)


def _frontmatter_value(body: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}\s*:\s*(.+?)\s*$", body)
    if not match:
        return ""
    return match.group(1).strip().strip("'\"")


def _source_kind(path: Path) -> str:
    parts = set(path.parts)
    if "plugins" in parts or "cache" in parts:
        return "plugin"
    try:
        resolved = path.resolve()
        home = Path.home().resolve()
        user_roots = (
            home / ".codex" / "skills",
            home / ".claude" / "skills",
            home / ".qoder" / "skills",
            home / ".config" / "opencode" / "skills",
            home / ".agents" / "skills",
        )
        if any(resolved.is_relative_to(root) for root in user_roots):
            return "user"
    except OSError:
        pass
    return "project"


def _resources(skill_file: Path) -> Tuple[Dict[str, Any], ...]:
    result = []
    skill_dir = skill_file.parent
    for directory, kind in (
        ("scripts", "script"),
        ("references", "reference"),
        ("assets", "asset"),
    ):
        resource_root = skill_dir / directory
        if not resource_root.is_dir() or resource_root.is_symlink():
            continue
        for path in sorted(resource_root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                size = path.stat().st_size
                relative = str(path.relative_to(skill_dir))
            except OSError:
                continue
            result.append({"path": relative, "kind": kind, "bytes": size})
    return tuple(result)


def parse_skill(skill_file: Path) -> SkillDefinition:
    try:
        stable_path = str(skill_file.resolve())
    except OSError:
        stable_path = str(skill_file)
    stable_id = f"skill_{hashlib.sha256(stable_path.encode('utf-8')).hexdigest()[:20]}"
    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        digest = hashlib.sha256(str(skill_file).encode("utf-8")).hexdigest()
        return SkillDefinition(
            stable_id,
            skill_file.parent.name,
            "",
            _source_kind(skill_file),
            str(skill_file.resolve()),
            digest,
            False,
            f"Unable to read SKILL.md: {exc.__class__.__name__}",
        )

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    match = FRONTMATTER.search(content)
    metadata = match.group(1) if match else ""
    name = _frontmatter_value(metadata, "name") or skill_file.parent.name
    description = _frontmatter_value(metadata, "description")
    version = _frontmatter_value(metadata, "version")
    compatibility = _frontmatter_value(metadata, "compatibility")
    errors = []
    if not match:
        errors.append("Missing YAML frontmatter")
    if not description:
        errors.append("Missing description")
    return SkillDefinition(
        stable_id,
        name,
        description,
        _source_kind(skill_file),
        str(skill_file.resolve()),
        digest,
        not errors,
        "; ".join(errors),
        version,
        compatibility,
        _resources(skill_file),
    )


def discover_skills(
    roots: Iterable[Path], exclusions: Iterable[Path] = ()
) -> List[SkillDefinition]:
    seen = set()
    skills = []
    for root in roots:
        root = root.expanduser()
        if not root.is_dir():
            continue
        for skill_file in root.rglob("SKILL.md"):
            if path_is_excluded(skill_file, exclusions):
                continue
            try:
                resolved = str(skill_file.resolve())
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            skills.append(parse_skill(skill_file))
    return sorted(skills, key=lambda item: (item.name.lower(), item.source_path))


def default_skill_roots(project: Optional[Path] = None) -> List[Path]:
    home = Path.home()
    roots = [
        home / ".codex" / "skills",
        home / ".codex" / "plugins" / "cache",
        home / ".claude" / "skills",
        home / ".qoder" / "skills",
        home / ".config" / "opencode" / "skills",
        home / ".agents" / "skills",
    ]
    if project:
        roots.extend(
            [
                project / ".codex" / "skills",
                project / ".claude" / "skills",
                project / ".qoder" / "skills",
                project / ".opencode" / "skills",
                project / ".agents" / "skills",
            ]
        )
    return roots
