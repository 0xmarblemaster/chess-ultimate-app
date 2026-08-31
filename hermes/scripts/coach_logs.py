#!/usr/bin/env python3
"""coach_logs — read back the coach diagnostics log ("what went wrong").

Reads the structured events written by ``src/coach_diagnostics.py`` to
``$HERMES_HOME/logs/diagnostics.jsonl`` and prints them for a human.

Examples:
    # last 20 events (default)
    python scripts/coach_logs.py

    # counts by kind over the last 24h
    python scripts/coach_logs.py --summary --since 24h

    # only empty-response fallbacks, last 50, full detail
    python scripts/coach_logs.py --kind empty_response --tail 50 --verbose

    # follow live (like tail -f)
    python scripts/coach_logs.py --follow

Exit code is 0 normally, or 2 with ``--fail-on-errors`` when any
error-level event is present in the window (handy for cron/healthchecks).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Make ``src`` importable whether run from the repo root or elsewhere.
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

try:
    from src import coach_diagnostics as diag
except Exception:  # pragma: no cover - fallback if src layout differs
    diag = None


def _resolve_path() -> Path:
    if diag is not None:
        return diag.log_path()
    home = os.environ.get("HERMES_HOME")
    base = Path(home) if home else _REPO
    return base / "logs" / "diagnostics.jsonl"


def _parse_since(s: str | None) -> float | None:
    """Parse '90s' / '15m' / '24h' / '7d' into an absolute epoch cutoff."""
    if not s:
        return None
    s = s.strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        if s[-1] in units:
            return time.time() - float(s[:-1]) * units[s[-1]]
        return time.time() - float(s)  # bare number = seconds
    except Exception:
        return None


def _iter_events(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except Exception:
                continue


_COLORS = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}
_RESET = "\033[0m"


def _fmt(ev: dict, verbose: bool, color: bool) -> str:
    level = ev.get("level", "info")
    head = (
        f"{ev.get('ts','?')}  {level.upper():7} {ev.get('kind','?'):22} "
        f"req={ev.get('request_id') or '-'}  {ev.get('message','')}"
    )
    if color and level in _COLORS:
        head = f"{_COLORS[level]}{head}{_RESET}"
    extras = {
        k: v
        for k, v in ev.items()
        if k not in {"ts", "epoch", "kind", "level", "request_id", "message", "traceback"}
    }
    lines = [head]
    if extras:
        lines.append("    " + json.dumps(extras, ensure_ascii=False))
    if verbose and ev.get("traceback"):
        lines.append("    " + ev["traceback"].replace("\n", "\n    ").rstrip())
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read the coach diagnostics log.")
    ap.add_argument("--tail", type=int, default=20, help="show last N events (default 20)")
    ap.add_argument("--kind", help="filter by event kind (e.g. empty_response)")
    ap.add_argument("--since", help="window: 90s | 15m | 24h | 7d")
    ap.add_argument("--summary", action="store_true", help="counts by kind instead of a list")
    ap.add_argument("--verbose", action="store_true", help="include tracebacks + all fields")
    ap.add_argument("--follow", action="store_true", help="stream new events (tail -f)")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    ap.add_argument("--fail-on-errors", action="store_true", help="exit 2 if any error-level event in window")
    args = ap.parse_args()

    path = _resolve_path()
    color = not args.no_color and sys.stdout.isatty()
    since = _parse_since(args.since)

    def _match(ev: dict) -> bool:
        if args.kind and ev.get("kind") != args.kind:
            return False
        if since is not None and ev.get("epoch", 0) < since:
            return False
        return True

    if args.follow:
        print(f"# following {path} (Ctrl-C to stop)")
        seen = 0
        try:
            while True:
                events = [e for e in _iter_events(path) if _match(e)]
                for ev in events[seen:]:
                    print(_fmt(ev, args.verbose, color))
                seen = len(events)
                time.sleep(1.0)
        except KeyboardInterrupt:
            return 0

    events = [e for e in _iter_events(path) if _match(e)]

    if args.summary:
        by_kind: dict[str, int] = {}
        by_level: dict[str, int] = {}
        for ev in events:
            by_kind[ev.get("kind", "?")] = by_kind.get(ev.get("kind", "?"), 0) + 1
            by_level[ev.get("level", "?")] = by_level.get(ev.get("level", "?"), 0) + 1
        win = args.since or "all time"
        print(f"# {len(events)} events ({win})  file={path}")
        if not events:
            print("  (none)")
        for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1]):
            print(f"  {n:6}  {k}")
        if by_level:
            print("  ---")
            for lv, n in sorted(by_level.items(), key=lambda kv: -kv[1]):
                print(f"  {n:6}  level={lv}")
    else:
        shown = events[-args.tail:] if args.tail and args.tail > 0 else events
        if not shown:
            print(f"# no events (file={path})")
        for ev in shown:
            print(_fmt(ev, args.verbose, color))

    if args.fail_on_errors and any(e.get("level") == "error" for e in events):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
