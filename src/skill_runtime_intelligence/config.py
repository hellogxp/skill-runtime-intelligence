"""Local product configuration with conservative privacy defaults."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .event_queue import default_state_root


CONFIG_VERSION = "skill-runtime-config-v1"


def default_config_path(state_root: Optional[Path] = None) -> Path:
    return (state_root or default_state_root()) / "config.json"


def default_database_path(state_root: Optional[Path] = None) -> Path:
    return (state_root or default_state_root()) / "data" / "panorama.db"


def default_config(state_root: Optional[Path] = None) -> Dict[str, Any]:
    return {
        "version": CONFIG_VERSION,
        "database": str(default_database_path(state_root)),
        "projects": [],
        "exclude_paths": [],
        "retention_days": None,
        "network_export": {"enabled": False, "endpoint": ""},
        "hooks": {
            "codex": {"consent": "not_requested"},
            "claude-code": {"consent": "not_requested"},
            "qoder": {"consent": "not_requested"},
            "opencode": {"consent": "not_requested"},
        },
    }


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    config_path = (path or default_config_path()).expanduser()
    value = default_config(config_path.parent)
    if not config_path.exists():
        return value
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Skill Runtime config must be a JSON object")
    default_hooks = dict(value["hooks"])
    value.update(loaded)
    loaded_hooks = loaded.get("hooks", {})
    if not isinstance(loaded_hooks, dict):
        raise ValueError("config.hooks must be an object")
    default_hooks.update(loaded_hooks)
    value["hooks"] = default_hooks
    if not isinstance(value.get("projects"), list):
        raise ValueError("config.projects must be a list")
    if not isinstance(value.get("exclude_paths"), list):
        raise ValueError("config.exclude_paths must be a list")
    return value


def save_config(value: Dict[str, Any], path: Optional[Path] = None) -> Path:
    config_path = (path or default_config_path()).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        config_path.parent.chmod(0o700)
    except OSError:
        pass
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{config_path.name}.",
        suffix=".tmp",
        dir=str(config_path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(str(temporary), str(config_path))
    finally:
        if temporary.exists():
            temporary.unlink()
    return config_path


def normalized_paths(values: Iterable[Path]) -> list:
    result = []
    seen = set()
    for value in values:
        path = str(value.expanduser().resolve())
        if path not in seen:
            result.append(path)
            seen.add(path)
    return result


def path_is_excluded(path: Path, exclusions: Iterable[Path]) -> bool:
    try:
        candidate = path.expanduser().resolve()
    except OSError:
        candidate = path.expanduser().absolute()
    for exclusion in exclusions:
        try:
            candidate.relative_to(exclusion.expanduser().resolve())
            return True
        except (OSError, ValueError):
            continue
    return False
