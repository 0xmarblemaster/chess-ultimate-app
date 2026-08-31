"""Unit tests for the flag-gated MCP startup discovery hook (Phase 2).

Covers ``src.config.COACH_MCP_ENABLED`` and ``src.server._maybe_discover_mcp_tools``:
with the flag off nothing is discovered and the framework's discover function is
never called; with it on, discovered tool names are returned; and a discovery
failure is swallowed so Hermes startup can never crash.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src import config
from src import server


@pytest.mark.unit
class TestCoachMcpFlag:
    def test_defaults_off(self):
        # Default must be False so behavior is byte-identical without the flag.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COACH_MCP_ENABLED", None)
            assert config._env_flag("COACH_MCP_ENABLED", False) is False

    def test_enabled_by_env(self):
        with patch.dict(os.environ, {"COACH_MCP_ENABLED": "true"}):
            assert config._env_flag("COACH_MCP_ENABLED", False) is True


@pytest.mark.unit
class TestMaybeDiscoverMcpTools:
    def test_flag_off_never_calls_discover(self):
        fake = MagicMock(return_value=["mcp-engine.chessdb_eval"])
        with patch.object(config, "COACH_MCP_ENABLED", False), patch(
            "tools.mcp_tool.discover_mcp_tools", fake
        ):
            result = server._maybe_discover_mcp_tools()
        assert result == []
        fake.assert_not_called()

    def test_flag_on_returns_discovered_tools(self):
        fake = MagicMock(
            return_value=["mcp-engine.chessdb_eval", "mcp-engine.stockfish_multipv"]
        )
        with patch.object(config, "COACH_MCP_ENABLED", True), patch(
            "tools.mcp_tool.discover_mcp_tools", fake
        ):
            result = server._maybe_discover_mcp_tools()
        assert result == [
            "mcp-engine.chessdb_eval",
            "mcp-engine.stockfish_multipv",
        ]
        fake.assert_called_once()

    def test_discovery_failure_is_swallowed(self):
        fake = MagicMock(side_effect=RuntimeError("MCP server unreachable"))
        with patch.object(config, "COACH_MCP_ENABLED", True), patch(
            "tools.mcp_tool.discover_mcp_tools", fake
        ):
            # Must NOT raise — a failed connect can never crash startup.
            result = server._maybe_discover_mcp_tools()
        assert result == []
        fake.assert_called_once()
