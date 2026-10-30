"""Index orchestration for local and observability adapters."""

import hashlib
import os
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from .adapters import CodexAdapter, ObservabilityAdapter
from .config import path_is_excluded
from .discovery import SkillDefinition, discover_skills
from .storage import Storage

_LARGE_ACTIVE_SOURCE_BYTES = 8 * 1024 * 1024
_LARGE_SOURCE_SETTLE_SECONDS = 30.0
_LARGE_SOURCE_MAX_PENDING_SECONDS = 300.0


def _source_watermark(source_mtimes: Dict[Path, int]) -> str:
    payload = "\0".join(
        f"{path}:{source_mtimes[path]}"
        for path in sorted(source_mtimes, key=str)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _eligible_source_mtimes(
    adapter: CodexAdapter,
    exclusions: Iterable[Path],
) -> Dict[Path, int]:
    excluded = list(exclusions)
    result = {}
    for path in adapter.session_files():
        cwd = adapter.peek_cwd(path)
        if cwd and path_is_excluded(Path(cwd), excluded):
            continue
        try:
            result[path] = path.stat().st_mtime_ns
        except OSError:
            continue
    return result


def index_local(
    database: Path,
    codex_sessions: Path,
    skill_roots: Iterable[Path],
    exclusions: Iterable[Path] = (),
    *,
    rebuild: bool = False,
    history_days: Optional[int] = None,
) -> Dict[str, int]:
    excluded = list(exclusions)
    skills: List[SkillDefinition] = discover_skills(skill_roots, excluded)
    storage = Storage(database)
    try:
        storage.replace_skills(skill.to_dict() for skill in skills)
        adapter = CodexAdapter(codex_sessions)
        checkpoints = storage.source_checkpoints("codex")
        existing_sources = storage.session_source_versions("codex")
        cutoff_ns = None
        if history_days is not None and history_days > 0:
            cutoff_ns = time.time_ns() - history_days * 86_400 * 1_000_000_000
        imported = 0
        failed = 0
        skipped_unchanged = 0
        skipped_history = 0
        skipped_active = 0
        checkpointed_existing = 0
        for source_path in adapter.session_files():
            try:
                resolved = str(source_path.resolve())
                before = source_path.stat()
                checkpoint = checkpoints.get(resolved)
                signature = (
                    int(before.st_dev),
                    int(before.st_ino),
                    int(before.st_size),
                    int(before.st_mtime_ns),
                )
                if not rebuild and checkpoint:
                    saved = (
                        int(checkpoint["device"]),
                        int(checkpoint["inode"]),
                        int(checkpoint["size"]),
                        int(checkpoint["mtime_ns"]),
                    )
                    if (
                        checkpoint["adapter_version"] == adapter.version
                        and saved == signature
                    ):
                        skipped_unchanged += 1
                        continue
                    if (
                        before.st_size >= _LARGE_ACTIVE_SOURCE_BYTES
                        and time.time_ns() - before.st_mtime_ns
                        < int(_LARGE_SOURCE_SETTLE_SECONDS * 1_000_000_000)
                    ):
                        skipped_active += 1
                        continue
                existing = existing_sources.get(resolved)
                if (
                    not rebuild
                    and checkpoint is None
                    and existing
                    and existing["adapter_version"] == adapter.version
                    and int(before.st_mtime_ns)
                    <= int(existing["indexed_at_ns"] or 0) + 1_000_000_000
                ):
                    storage.set_source_checkpoint(
                        source_path, "codex", adapter.version, before
                    )
                    checkpointed_existing += 1
                    continue
                if (
                    not rebuild
                    and checkpoint is None
                    and existing is None
                    and cutoff_ns is not None
                    and before.st_mtime_ns < cutoff_ns
                ):
                    skipped_history += 1
                    continue
                cwd = adapter.peek_cwd(source_path)
                if cwd and path_is_excluded(Path(cwd), excluded):
                    continue
                session, raw, events, skill_runs = adapter.parse(source_path, skills)
                storage.replace_session(session, raw, events, skill_runs)
                after = source_path.stat()
                if (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                ) == (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    storage.set_source_checkpoint(
                        source_path, "codex", adapter.version, after
                    )
                imported += 1
            except (OSError, UnicodeError, ValueError):
                failed += 1
        counts = storage.counts()
        counts.update(
            {
                "imported": imported,
                "failed": failed,
                "skipped_unchanged": skipped_unchanged,
                "skipped_history": skipped_history,
                "skipped_active": skipped_active,
                "checkpointed_existing": checkpointed_existing,
            }
        )
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


def _index_changed_batch(
    database: Path,
    adapter: CodexAdapter,
    skills: List[SkillDefinition],
    changed: List[Path],
    eligible_mtimes: Dict[Path, int],
    removed_source_count: int = 0,
    source_boundary_probe: Optional[
        Callable[[], Dict[Path, int]]
    ] = None,
) -> Dict[str, object]:
    storage = Storage(database)
    epoch_state = storage.begin_collection_epoch(
        "codex",
        source_count=len(eligible_mtimes),
        changed_source_count=len(changed) + max(0, removed_source_count),
        removed_source_count=removed_source_count,
        source_watermark_sha256=_source_watermark(eligible_mtimes),
    )
    processed = 0
    failed = 0
    late_arrivals = 0
    try:
        try:
            for source_path in changed:
                try:
                    session, raw, events, skill_runs = adapter.parse(
                        source_path, skills
                    )
                    storage.replace_session(session, raw, events, skill_runs)
                    try:
                        storage.set_source_checkpoint(
                            source_path,
                            "codex",
                            str(session.get("adapter_version") or "unknown"),
                            source_path.stat(),
                        )
                    except OSError:
                        pass
                    processed += 1
                except (OSError, UnicodeError, ValueError):
                    failed += 1
                    continue
            if source_boundary_probe is None:
                current_mtimes = {}
                for source_path in eligible_mtimes:
                    try:
                        current_mtimes[source_path] = (
                            source_path.stat().st_mtime_ns
                        )
                    except OSError:
                        continue
            else:
                current_mtimes = source_boundary_probe()
            late_arrivals = sum(
                eligible_mtimes.get(source_path)
                != current_mtimes.get(source_path)
                for source_path in set(eligible_mtimes) | set(current_mtimes)
            )
        except Exception:
            storage.complete_collection_epoch(
                "codex",
                epoch_state["epoch"],
                processed_source_count=processed,
                failed_source_count=failed + 1,
                late_arrival_count=late_arrivals,
                status="failed",
            )
            raise
        return storage.complete_collection_epoch(
            "codex",
            epoch_state["epoch"],
            processed_source_count=processed,
            failed_source_count=failed,
            late_arrival_count=late_arrivals,
        )
    finally:
        storage.close()


def watch_local(
    database: Path,
    codex_sessions: Path,
    skill_roots: Iterable[Path],
    interval_seconds: float = 2.0,
    exclusions: Iterable[Path] = (),
    parent_pid: Optional[int] = None,
) -> None:
    """Continuously re-index only changed Codex session files.

    The source transcript remains authoritative. A changed session is parsed
    into a complete replacement transaction, so partial appends never leave a
    half-updated normalized graph.
    """
    roots = list(skill_roots)
    excluded = list(exclusions)
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
    pending_changes: Dict[Path, tuple[float, float]] = {}
    settle_seconds = max(1.0, min(5.0, interval_seconds * 2))
    max_pending_seconds = max(10.0, interval_seconds * 10)

    while True:
        if parent_pid and os.getppid() != parent_pid:
            return
        now = time.monotonic()
        if not skills or now - last_skill_scan >= 30:
            discovered = discover_skills(roots, excluded)
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

        current_paths = set(adapter.session_files())
        removed_paths = set(known_mtimes) - current_paths
        eligible_mtimes = _eligible_source_mtimes(adapter, excluded)
        for path in current_paths:
            if path not in eligible_mtimes:
                known_mtimes.pop(path, None)
                pending_changes.pop(path, None)
                continue
            mtime = eligible_mtimes[path]
            if known_mtimes.get(path) != mtime:
                known_mtimes[path] = mtime
                first_seen, _ = pending_changes.get(path, (now, now))
                pending_changes[path] = (first_seen, now)
        for removed in removed_paths:
            known_mtimes.pop(removed, None)
            pending_changes.pop(removed, None)

        changed = []
        for path, (first_seen, last_seen) in pending_changes.items():
            try:
                is_large = path.stat().st_size >= _LARGE_ACTIVE_SOURCE_BYTES
            except OSError:
                is_large = False
            path_settle = (
                _LARGE_SOURCE_SETTLE_SECONDS if is_large else settle_seconds
            )
            path_max_pending = (
                _LARGE_SOURCE_MAX_PENDING_SECONDS
                if is_large
                else max_pending_seconds
            )
            if (
                now - last_seen >= path_settle
                or now - first_seen >= path_max_pending
            ):
                changed.append(path)
        for path in changed:
            pending_changes.pop(path, None)

        if changed or removed_paths:
            _index_changed_batch(
                database,
                adapter,
                skills,
                changed,
                eligible_mtimes,
                removed_source_count=len(removed_paths),
                source_boundary_probe=lambda: _eligible_source_mtimes(
                    adapter,
                    excluded,
                ),
            )
        time.sleep(max(0.5, interval_seconds))
