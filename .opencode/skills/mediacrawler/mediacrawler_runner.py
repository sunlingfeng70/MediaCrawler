#!/usr/bin/env python3
"""Small, local-only command wrapper for the MediaCrawler CLI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


PLATFORMS = ("xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu")
LOGIN_TYPES = ("qrcode", "phone", "cookie")
SAVE_OPTIONS = ("csv", "db", "json", "jsonl", "sqlite", "excel", "mongodb", "postgres")
PROXY_PROVIDERS = ("kuaidaili", "wandouhttp", "static")


def discover_project_root(start: Path) -> Path:
    """Find a MediaCrawler checkout without consulting the network."""

    for candidate in (start, *start.parents):
        if (
            (candidate / "main.py").is_file()
            and (candidate / "pyproject.toml").is_file()
            and (candidate / "config").is_dir()
        ):
            return candidate
    raise FileNotFoundError(
        "MediaCrawler root not found; pass --project-root PATH"
    )


def read_cookies(cookie_file: Path | None) -> str | None:
    """Read cookies from a file or environment without logging the value."""

    if cookie_file is not None:
        value = cookie_file.read_text(encoding="utf-8").strip()
        if not value:
            raise ValueError(f"Cookie file is empty: {cookie_file}")
        return value

    value = os.environ.get("MEDIACRAWLER_COOKIES", "").strip()
    return value or None


def add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--platform", choices=PLATFORMS, default="xhs")
    parser.add_argument("--login-type", choices=LOGIN_TYPES, default="qrcode")
    parser.add_argument("--keywords", default="")
    parser.add_argument("--specified-id", default="")
    parser.add_argument("--creator-id", default="")
    parser.add_argument("--cookies-file", type=Path)
    parser.add_argument("--get-comment", choices=("yes", "no"), default="no")
    parser.add_argument("--get-sub-comment", choices=("yes", "no"), default="no")
    parser.add_argument("--headless", choices=("yes", "no"), default="no")
    parser.add_argument("--save-data-option", choices=SAVE_OPTIONS, default="jsonl")
    parser.add_argument("--save-data-path", default="")
    parser.add_argument("--max-notes", type=int, default=15)
    parser.add_argument("--max-comments", type=int, default=10)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--enable-ip-proxy", choices=("yes", "no"), default="no")
    parser.add_argument("--ip-proxy-provider", choices=PROXY_PROVIDERS, default="kuaidaili")
    parser.add_argument("--ip-proxy-pool-count", type=int, default=2)
    parser.add_argument("--static-proxy-url", default="")


def build_crawl_command(operation: str, args: argparse.Namespace) -> list[str]:
    if args.max_notes < 1:
        raise ValueError("--max-notes must be at least 1")
    if args.max_comments < 0:
        raise ValueError("--max-comments cannot be negative")
    if args.max_concurrency < 1:
        raise ValueError("--max-concurrency must be at least 1")
    if args.start_page < 1:
        raise ValueError("--start-page must be at least 1")

    if operation == "search" and not args.keywords.strip():
        raise ValueError("search requires --keywords")
    if operation == "detail" and not args.specified_id.strip():
        raise ValueError("detail requires --specified-id")
    if operation == "creator" and not args.creator_id.strip():
        raise ValueError("creator requires --creator-id")

    cookies = read_cookies(args.cookies_file)
    if args.login_type == "cookie" and not cookies:
        raise ValueError(
            "cookie login requires --cookies-file or MEDIACRAWLER_COOKIES"
        )

    command = [
        "uv",
        "run",
        "main.py",
        "--platform",
        args.platform,
        "--lt",
        args.login_type,
        "--type",
        operation,
        "--start",
        str(args.start_page),
        "--get_comment",
        args.get_comment,
        "--get_sub_comment",
        args.get_sub_comment,
        "--headless",
        args.headless,
        "--save_data_option",
        args.save_data_option,
        "--crawler_max_notes_count",
        str(args.max_notes),
        "--max_comments_count_singlenotes",
        str(args.max_comments),
        "--max_concurrency_num",
        str(args.max_concurrency),
        "--enable_ip_proxy",
        args.enable_ip_proxy,
        "--ip_proxy_pool_count",
        str(args.ip_proxy_pool_count),
        "--ip_proxy_provider_name",
        args.ip_proxy_provider,
    ]

    if args.keywords:
        command.extend(("--keywords", args.keywords))
    if args.specified_id:
        command.extend(("--specified_id", args.specified_id))
    if args.creator_id:
        command.extend(("--creator_id", args.creator_id))
    if args.save_data_path:
        command.extend(("--save_data_path", args.save_data_path))
    if args.static_proxy_url:
        command.extend(("--static_proxy_url", args.static_proxy_url))
    if cookies:
        command.extend(("--cookies", cookies))

    return command


def redact_command(command: Sequence[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for token in command:
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
        else:
            redacted.append(token)
            redact_next = token == "--cookies"
    return redacted


def check_environment(root: Path) -> int:
    checks = {
        "project_root": str(root),
        "main_py": (root / "main.py").is_file(),
        "pyproject_toml": (root / "pyproject.toml").is_file(),
        "config_dir": (root / "config").is_dir(),
        "uv_available": shutil.which("uv") is not None,
    }
    checks["status"] = "ok" if all(
        value is True for key, value in checks.items() if key != "project_root"
    ) else "needs-attention"
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if checks["status"] == "ok" else 1


REPORT_KINDS = ("detail_contents", "detail_comments", "search", "creator")
REPORT_BUCKETS = {"detail_contents": "contents", "detail_comments": "comments"}


def summarize_record(kind: str, record: dict) -> dict:
    """Extract agent-friendly fields from a single jsonl record."""

    if kind == "detail_contents":
        return {
            "id": record.get("aweme_id") or record.get("note_id"),
            "title": (record.get("title") or "")[:60],
            "author": record.get("nickname"),
            "comment_count": record.get("comment_count"),
            "url": record.get("aweme_url"),
        }
    if kind == "detail_comments":
        return {
            "comment_id": record.get("comment_id"),
            "content": (record.get("content") or "")[:60],
            "user": record.get("nickname"),
            "homepage_url": record.get("homepage_url") or "",
        }
    if kind == "search":
        return {
            "id": record.get("aweme_id") or record.get("note_id"),
            "title": (record.get("title") or "")[:60],
            "author": record.get("nickname"),
        }
    if kind == "creator":
        return {
            "id": record.get("aweme_id") or record.get("note_id"),
            "title": (record.get("title") or "")[:60],
        }
    return record


def build_report(root: Path, platform: str, save_data_path: str, limit: int) -> dict:
    """Summarize the newest jsonl crawl outputs under the data directory."""

    base = Path(save_data_path) if save_data_path else root / "data"
    if not base.is_dir():
        raise ValueError(f"Data path not found: {base}")

    files = sorted(base.rglob("*.jsonl"))
    if platform:
        files = [path for path in files if platform in str(path)]
    if not files:
        raise ValueError(f"No jsonl files under {base}" + (f" for platform {platform}" if platform else ""))

    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    files = files[:20]

    summary: dict = {
        "platform": platform or "all",
        "base": str(base),
        "files": [],
        "totals": {"contents": 0, "comments": 0, "search": 0, "creator": 0, "records": 0},
    }
    for path in files:
        kind = next((k for k in REPORT_KINDS if k in path.name), "other")
        count = 0
        samples: list[dict] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line in ("[", "]"):
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                count += 1
                if len(samples) < limit:
                    samples.append(summarize_record(kind, record))
        bucket = REPORT_BUCKETS.get(kind, kind if kind in summary["totals"] else "records")
        summary["totals"][bucket] += count
        summary["totals"]["records"] += count
        summary["files"].append({"path": str(path), "kind": kind, "records": count, "samples": samples})
    return summary


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MediaCrawler locally")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="check local prerequisites")
    check_parser.set_defaults(operation=None)

    for operation in ("search", "detail", "creator"):
        operation_parser = subparsers.add_parser(operation)
        add_runtime_options(operation_parser)
        operation_parser.set_defaults(operation=operation)

    init_parser = subparsers.add_parser("init-db", help="initialize a database")
    init_parser.add_argument("--database", choices=("sqlite", "mysql", "postgres"), required=True)
    init_parser.set_defaults(operation="init-db")

    report_parser = subparsers.add_parser("report", help="summarize crawl output files")
    report_parser.add_argument("--platform", default="", help="filter by platform (xhs, dy, ...); empty = all")
    report_parser.add_argument("--save-data-path", default="", help="path to crawl output; default <root>/data")
    report_parser.add_argument("--limit", type=int, default=5, help="sample records per file")
    report_parser.set_defaults(operation="report")

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root = discover_project_root(args.project_root or Path.cwd())
        if args.command == "check":
            return check_environment(root)

        if args.command == "init-db":
            command = ["uv", "run", "main.py", "--init_db", args.database]
        elif args.command == "report":
            summary = build_report(root, args.platform, args.save_data_path, args.limit)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        else:
            command = build_crawl_command(args.operation, args)

        if args.dry_run:
            print(" ".join(redact_command(command)))
            return 0

        completed = subprocess.run(command, cwd=root, check=False)
        return completed.returncode
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"MediaCrawler runner error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
