"""Unit tests for the coach diagnostics logger (src/coach_diagnostics.py).

All tests point HERMES_HOME at a tmp dir so they never touch the real
diagnostics log and stay fully isolated.
"""
import importlib
import json

import pytest


@pytest.fixture()
def diag(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    mod = importlib.import_module("src.coach_diagnostics")
    importlib.reload(mod)  # re-resolve _logs_dir under the patched env
    return mod


def _lines(diag):
    p = diag.log_path()
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def test_record_writes_jsonl(diag, tmp_path):
    diag.record("empty_response", request_id="abc123", message="hi", model="gemini")
    events = _lines(diag)
    assert len(events) == 1
    ev = events[0]
    assert ev["kind"] == "empty_response"
    assert ev["request_id"] == "abc123"
    assert ev["level"] == "error"  # default
    assert ev["model"] == "gemini"
    assert "ts" in ev and "epoch" in ev
    # written under the patched HERMES_HOME
    assert str(tmp_path) in str(diag.log_path())


def test_record_captures_exception(diag):
    try:
        raise ValueError("boom")
    except ValueError as exc:
        diag.record("agent_error", exc=exc)
    ev = _lines(diag)[0]
    assert ev["error"].startswith("ValueError: boom")
    assert "Traceback" in ev["traceback"]


def test_record_never_raises_on_unserializable(diag):
    class Weird:
        def __repr__(self):
            return "<weird>"

    # Must not raise even with a non-JSON-serialisable field.
    diag.record("http_error", obj=Weird())
    ev = _lines(diag)[0]
    assert ev["obj"] == "<weird>"


def test_record_swallows_all_errors(diag, monkeypatch):
    # Even if writing blows up, record() must not propagate.
    monkeypatch.setattr(diag, "log_path", lambda: (_ for _ in ()).throw(OSError("nope")))
    diag.record("boom")  # should silently no-op


def test_read_events_filter_and_limit(diag):
    for i in range(5):
        diag.record("empty_response", i=i)
    diag.record("agent_error", i=99)
    only_empty = diag.read_events(kind="empty_response")
    assert len(only_empty) == 5
    assert diag.read_events(limit=2)[-1]["kind"] == "agent_error"
    assert len(diag.read_events(limit=3)) == 3


def test_read_events_skips_malformed(diag):
    diag.record("http_error", status=500)
    with diag.log_path().open("a") as f:
        f.write("this is not json\n")
    diag.record("http_error", status=502)
    events = diag.read_events()
    assert len(events) == 2  # malformed line skipped, not fatal
    assert [e["status"] for e in events] == [500, 502]


def test_read_events_missing_file_is_empty(diag):
    assert diag.read_events() == []


def test_rotation(diag, monkeypatch):
    monkeypatch.setattr(diag, "_MAX_BYTES", 200)
    for i in range(50):
        diag.record("http_error", padding="x" * 50, i=i)
    backup = diag.log_path().with_name(diag.log_path().name + ".1")
    assert backup.exists()  # rotated at least once
