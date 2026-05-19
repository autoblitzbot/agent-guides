#!/usr/bin/env python3
"""Post a public kind-1 text note to Nostr using nak."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
]


def load_config() -> dict:
    config_path = Path.home() / ".nostr" / "config.json"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {config_path}: {exc}", file=sys.stderr)
        sys.exit(1)


def get_nsec(config: dict) -> str | None:
    return os.environ.get("NOSTR_NSEC") or config.get("nsec")


def get_relays(config: dict, cli_relays: list[str] | None = None) -> list[str]:
    if cli_relays:
        return cli_relays

    relays_env = os.environ.get("NOSTR_RELAYS")
    if relays_env:
        relays = [relay.strip() for relay in relays_env.split(",") if relay.strip()]
        if relays:
            return relays

    relays_cfg = config.get("relays")
    if isinstance(relays_cfg, list) and relays_cfg:
        return [str(relay) for relay in relays_cfg if str(relay).strip()]

    return DEFAULT_RELAYS


def read_content(args: argparse.Namespace) -> str:
    if args.content:
        return " ".join(args.content).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def parse_event(stdout: str) -> dict:
    text = stdout.strip()
    if not text:
        return {}

    # nak normally prints one JSON event. Be tolerant of extra lines.
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            continue
    return {}


def post(content: str, nsec: str, relays: list[str], timeout: int) -> dict:
    if shutil.which("nak") is None:
        print("ERROR: nak CLI not found on PATH", file=sys.stderr)
        sys.exit(1)

    cmd = ["nak", "event", "--sec", nsec, "--content", content, *relays]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        print("ERROR: nak timed out", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown nak error"
        print(f"ERROR: {stderr}", file=sys.stderr)
        sys.exit(result.returncode)

    stdout = result.stdout.strip()
    if stdout:
        print(stdout)
    return parse_event(stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Post a public kind-1 Nostr note using nak.")
    parser.add_argument("content", nargs="*", help="note content; stdin is used when omitted")
    parser.add_argument("--relay", action="append", dest="relays", help="relay URL; repeat for multiple relays")
    parser.add_argument("--dry-run", action="store_true", help="print content and relays without posting")
    parser.add_argument("--timeout", type=int, default=30, help="nak timeout in seconds")
    args = parser.parse_args()

    content = read_content(args)
    if not content:
        print("ERROR: empty content", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    relays = get_relays(config, args.relays)

    if args.dry_run:
        print(json.dumps({"content": content, "relays": relays, "dry_run": True}, ensure_ascii=False, indent=2))
        return

    nsec = get_nsec(config)
    if not nsec:
        print("ERROR: no NSEC found. Set NOSTR_NSEC or ~/.nostr/config.json", file=sys.stderr)
        sys.exit(1)

    event = post(content, nsec, relays, args.timeout)
    note_id = event.get("id", "unknown")
    print(f"\n✓ Posted. note ID: {note_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
