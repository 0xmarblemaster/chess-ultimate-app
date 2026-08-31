"""Coach diagnostics logger.

A structured, best-effort failure log so operators can always answer the
question "what went wrong?" without grepping raw tracebacks out of
``errors.log`` (which is noisy with expected 404s etc.).

Events are written as newline-delimited JSON to
``$HERMES_HOME/logs/diagnostics.jsonl``. Read them back with
``scripts/coach_logs.py`` (or ``hermes-coach-logs``).

Design rules:
  * Diagnostics must NEVER break a coach request. Every public function
    swallows its own exceptions.
  * Additive only. This module observes; it does not change coach behaviour.
  * JSON-safe: non-serialisable fields are coerced to ``repr()``.
"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Optional

# Rotate the active file once it crosses this size; keep one .1 backup.
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_LOCK = threading.Lock()


def _logs_dir() -> Path:
    """Resolve the logs directory the same way the server does.

    Uses ``HERMES_HOME`` when set (prod: profiles/chess-coach), otherwise
    falls back to ``<repo>/logs`` next to this file.
    """
    home = os.environ.get("HERMES_HOME")
    base = Path(home) if home else Path(__file__).resolve().parent.parent
    d = base / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path() -> Path:
    return _logs_dir() / "diagnostics.jsonl"


def _rotate(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size > _MAX_BYTES:
            path.replace(path.with_name(path.name + ".1"))
    except Exception:
        pass


def record(
    kind: str,
    *,
    request_id: Optional[str] = None,
    level: str = "error",
    message: str = "",
    exc: Optional[BaseException] = None,
    **fields: Any,
) -> None:
    """Append one structured diagnostic event. Never raises.

    Args:
        kind: short machine slug, e.g. ``empty_response``, ``agent_error``,
            ``tool_error``, ``mcp_discovery_failed``, ``http_error``.
        request_id: correlates to the ``X-Request-Id`` header / access log.
        level: ``error`` | ``warning`` | ``info``.
        message: human-readable one-liner.
        exc: optional exception; its type, str, and (trimmed) traceback are
            captured.
        **fields: any extra JSON-safe context (path, status, model, tool, ...).
    """
    try:
        event: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "epoch": round(time.time(), 3),
            "kind": kind,
            "level": level,
            "request_id": request_id,
            "message": message,
        }
        if exc is not None:
            event["error"] = f"{type(exc).__name__}: {exc}"
            tb = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            event["traceback"] = tb[-4000:]
        for k, v in fields.items():
            try:
                json.dumps(v)
                event[k] = v
            except Exception:
                event[k] = repr(v)

        line = json.dumps(event, ensure_ascii=False)
        path = log_path()
        with _LOCK:
            _rotate(path)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        # Diagnostics must never break the request path.
        pass


def read_events(
    limit: Optional[int] = None,
    kind: Optional[str] = None,
    since_epoch: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Read diagnostic events back (newest last). Never raises.

    Malformed lines are skipped. Applies optional ``kind`` / ``since_epoch``
    filters, then returns the last ``limit`` matching events.
    """
    events: list[dict[str, Any]] = []
    try:
        path = log_path()
        if not path.exists():
            return events
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                except Exception:
                    continue
                if kind and ev.get("kind") != kind:
                    continue
                if since_epoch is not None and ev.get("epoch", 0) < since_epoch:
                    continue
                events.append(ev)
    except Exception:
        return events
    if limit is not None and limit >= 0:
        return events[-limit:]
    return events
