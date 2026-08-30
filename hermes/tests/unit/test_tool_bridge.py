"""Unit tests for the voice tool bridge (src/tool_bridge.py).

Covers schema conversion to Gemini format and the single-tool dispatch endpoint:
success, unknown-tool 404, tool-error -> 200, X-User-Id identity override, and
session board_state sync.
"""

import json
import threading
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src import tool_bridge
from src.server import app
from src.sessions import session_store
from src.tool_bridge import (
    _UNSUPPORTED_SCHEMA_KEYS,
    build_tool_declarations,
    clean_gemini_schema,
)

USER_HEADERS = {"X-User-Id": "test-user-123"}


@pytest.fixture(autouse=True)
def _clear_sessions():
    session_store._sessions.clear()
    yield
    session_store._sessions.clear()


def _walk_keys(node):
    """Yield every dict key present anywhere in a nested schema."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


@pytest.mark.unit
class TestSchemaConversion:
    def test_clean_strips_unsupported_keys_recursively(self):
        dirty = {
            "type": "object",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "additionalProperties": False,
            "properties": {
                "arrows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "brush": {"type": "string", "default": "green"},
                        },
                    },
                },
            },
        }
        cleaned = clean_gemini_schema(dirty)
        keys = set(_walk_keys(cleaned))
        assert keys.isdisjoint(_UNSUPPORTED_SCHEMA_KEYS)
        # Non-offending structure survives.
        assert cleaned["type"] == "object"
        assert "brush" in cleaned["properties"]["arrows"]["items"]["properties"]

    def test_build_tool_declarations_shape(self):
        decls = build_tool_declarations()
        assert len(decls) >= 15
        names = {d["name"] for d in decls}
        assert "board_control" in names
        for decl in decls:
            assert isinstance(decl["name"], str) and decl["name"]
            assert "description" in decl
            assert "parameters" in decl
            # No Gemini-rejected keys anywhere in the parameter tree.
            assert set(_walk_keys(decl["parameters"])).isdisjoint(
                _UNSUPPORTED_SCHEMA_KEYS
            )


@pytest.mark.unit
class TestToolsEndpoint:
    def setup_method(self):
        self.client = TestClient(app)

    def test_get_tools_returns_declarations(self):
        resp = self.client.get("/api/coach/tools")
        assert resp.status_code == 200
        tools = resp.json()["tools"]
        assert any(t["name"] == "board_control" for t in tools)


@pytest.mark.unit
class TestToolDispatch:
    def setup_method(self):
        self.client = TestClient(app)

    def test_requires_user_id(self):
        resp = self.client.post("/api/coach/tool/board_control", json={"args": {}})
        assert resp.status_code == 401

    def test_unknown_tool_404(self):
        resp = self.client.post(
            "/api/coach/tool/does_not_exist",
            headers=USER_HEADERS,
            json={"args": {}},
        )
        assert resp.status_code == 404

    def test_dispatch_success_with_board_actions(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        resp = self.client.post(
            "/api/coach/tool/board_control",
            headers=USER_HEADERS,
            json={"args": {"action_type": "set_fen", "fen": fen}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "error" not in body
        assert body["board_actions"]
        assert body["board_actions"][0]["type"] == "set_fen"
        assert body["board_actions"][0]["fen"] == fen

    def test_tool_error_returns_200_with_error(self):
        # Unknown action_type makes board_control return an error dict, not raise.
        resp = self.client.post(
            "/api/coach/tool/board_control",
            headers=USER_HEADERS,
            json={"args": {"action_type": "bogus_action"}},
        )
        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_user_id_override(self):
        captured = {}

        def _fake_dispatch(name, args, **kwargs):
            captured["args"] = args
            return json.dumps({"ok": True})

        with patch.object(tool_bridge.registry, "dispatch", side_effect=_fake_dispatch):
            resp = self.client.post(
                "/api/coach/tool/get_user_progress",
                headers=USER_HEADERS,
                json={"args": {"user_id": "attacker-999"}},
            )
        assert resp.status_code == 200
        # The model-supplied user_id must be replaced with the header identity.
        assert captured["args"]["user_id"] == "test-user-123"

    def test_board_state_sync_on_set_fen(self):
        session = session_store.create(user_id="test-user-123", session_id="sess-1")
        fen = "8/8/8/8/8/8/8/K6k w - - 0 1"
        resp = self.client.post(
            "/api/coach/tool/board_control",
            headers=USER_HEADERS,
            json={
                "args": {"action_type": "set_fen", "fen": fen},
                "session_id": "sess-1",
            },
        )
        assert resp.status_code == 200
        assert session.board_state == fen

    def test_slow_dispatch_does_not_block_event_loop(self):
        # A slow synchronous tool must run off the event loop, so a concurrent
        # request (here /health) stays responsive while it's in flight.
        started = threading.Event()

        def _slow_dispatch(name, args, **kwargs):
            started.set()
            time.sleep(2.0)
            return json.dumps({"ok": True})

        health_ms = {}

        def _fire_slow():
            self.client.post(
                "/api/coach/tool/board_control",
                headers=USER_HEADERS,
                json={"args": {"action_type": "set_fen"}},
            )

        with patch.object(tool_bridge.registry, "dispatch", side_effect=_slow_dispatch):
            worker = threading.Thread(target=_fire_slow)
            worker.start()
            assert started.wait(timeout=2.0), "slow dispatch never started"
            t0 = time.perf_counter()
            resp = self.client.get("/health")
            health_ms["elapsed"] = (time.perf_counter() - t0) * 1000
            worker.join(timeout=5.0)

        assert resp.status_code == 200
        assert health_ms["elapsed"] < 500, (
            f"/health blocked for {health_ms['elapsed']:.0f}ms during slow dispatch"
        )

    def test_board_state_sync_scoped_to_user(self):
        # A session owned by another user must not be mutated.
        session = session_store.create(user_id="other-user", session_id="sess-2")
        original = session.board_state
        fen = "8/8/8/8/8/8/8/K6k w - - 0 1"
        resp = self.client.post(
            "/api/coach/tool/board_control",
            headers=USER_HEADERS,
            json={
                "args": {"action_type": "set_fen", "fen": fen},
                "session_id": "sess-2",
            },
        )
        assert resp.status_code == 200
        assert session.board_state == original
