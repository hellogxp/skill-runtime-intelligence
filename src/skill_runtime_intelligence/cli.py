"""Command-line entry point."""

import argparse
import json
import threading
from pathlib import Path
from typing import List

from .discovery import default_skill_roots
from .adapters import SUPPORTED_PROFILES
from .indexer import import_observability, index_local, watch_local
from .server import serve


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _index_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--database", type=_path, default=Path(".sri/panorama.db"),
        help="SQLite database path (default: .sri/panorama.db)",
    )
    parser.add_argument(
        "--codex-sessions", type=_path, default=Path("~/.codex/sessions").expanduser(),
        help="Codex JSONL session root",
    )
    parser.add_argument(
        "--skill-root", action="append", type=_path, default=[],
        help="Additional Skill root; repeat for multiple roots",
    )
    parser.add_argument(
        "--project", type=_path, default=Path.cwd(),
        help="Project whose local Skill roots should be scanned",
    )


def _roots(args) -> List[Path]:
    roots = default_skill_roots(args.project)
    roots.extend(args.skill_root)
    return roots


def _run_index(args) -> dict:
    result = index_local(args.database, args.codex_sessions, _roots(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-panorama",
        description="Local-first, evidence-graded Agent Skill runtime panorama",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index local Skills and Codex sessions")
    _index_args(index_parser)

    serve_parser = subparsers.add_parser("serve", help="Serve an existing local index")
    serve_parser.add_argument("--database", type=_path, default=Path(".sri/panorama.db"))
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=4317)

    dev_parser = subparsers.add_parser("dev", help="Index once, then open the local UI")
    _index_args(dev_parser)
    dev_parser.add_argument("--host", default="127.0.0.1")
    dev_parser.add_argument("--port", type=int, default=4317)
    dev_parser.add_argument(
        "--watch-interval",
        type=float,
        default=2.0,
        help="Seconds between incremental transcript checks (default: 2)",
    )

    import_parser = subparsers.add_parser(
        "import", help="Import Skill runtime evidence from an observability export"
    )
    import_parser.add_argument("source", type=_path, help="JSON export path")
    import_parser.add_argument(
        "--format",
        choices=("auto",) + SUPPORTED_PROFILES,
        default="auto",
        help="Source profile; auto detects common export shapes",
    )
    import_parser.add_argument(
        "--database", type=_path, default=Path(".sri/panorama.db")
    )
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "index":
        _run_index(args)
    elif args.command == "serve":
        serve(args.database, args.host, args.port)
    elif args.command == "dev":
        _run_index(args)
        watcher = threading.Thread(
            target=watch_local,
            args=(
                args.database,
                args.codex_sessions,
                _roots(args),
                args.watch_interval,
            ),
            daemon=True,
            name="skill-runtime-watch",
        )
        watcher.start()
        serve(args.database, args.host, args.port)
    elif args.command == "import":
        result = import_observability(args.database, args.source, args.format)
        print(json.dumps(result, ensure_ascii=False, indent=2))
