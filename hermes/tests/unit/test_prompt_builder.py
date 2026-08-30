"""Unit tests for system prompt builder."""

import httpx
import chess
import pytest

import src.prompt_builder as prompt_builder
from src.prompt_builder import build_system_prompt, LOCALE_TO_LANGUAGE
from src.user_profile import UserProfile

MOCK_SOUL = "# Chess Coach\nYou are a chess coach."

CCP_BLOCK = "<detailed_board_analysis>MASTRA CCP fusion here</detailed_board_analysis>"
LOCAL_BLOCK = "LOCAL PYTHON PORT ANALYSIS"


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.unit
class TestPromptBuilder:
    def test_soul_only(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL)
        assert "Chess Coach" in prompt
        assert "Student Profile" not in prompt
        assert "Board Control" in prompt

    def test_with_user_profile(self):
        profile = UserProfile(
            user_id="u1",
            rating=1500,
            goals=["Improve tactics"],
            weaknesses=["Endgames"],
        )
        prompt = build_system_prompt(
            soul_content=MOCK_SOUL,
            user_profile=profile,
        )
        assert "Student Profile" in prompt
        assert "1500" in prompt
        assert "Improve tactics" in prompt
        assert "Endgames" in prompt

    def test_with_board_state(self):
        prompt = build_system_prompt(
            soul_content=MOCK_SOUL,
            board_fen=chess.STARTING_FEN,
        )
        assert "Current Board State" in prompt
        assert chess.STARTING_FEN in prompt

    def test_with_move_history(self):
        prompt = build_system_prompt(
            soul_content=MOCK_SOUL,
            board_fen=chess.STARTING_FEN,
            move_history=["e4", "e5", "Nf3", "Nc6"],
        )
        assert "Move history" in prompt
        assert "1. e4 e5" in prompt
        assert "2. Nf3 Nc6" in prompt

    def test_combines_all_sources(self):
        profile = UserProfile(user_id="u1", rating=2000, style="aggressive")
        prompt = build_system_prompt(
            soul_content=MOCK_SOUL,
            user_profile=profile,
            board_fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            move_history=["e4"],
        )
        assert "Chess Coach" in prompt
        assert "Student Profile" in prompt
        assert "2000" in prompt
        assert "aggressive" in prompt
        assert "Current Board State" in prompt
        assert "Board Control" in prompt

    def test_locale_russian_injects_directive(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL, locale="ru")
        assert "CRITICAL LANGUAGE RULE" in prompt
        assert "Russian" in prompt
        # Language directive must come before SOUL content
        lang_pos = prompt.index("CRITICAL LANGUAGE RULE")
        soul_pos = prompt.index("Chess Coach")
        assert lang_pos < soul_pos

    def test_locale_kazakh_injects_directive(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL, locale="kz")
        assert "CRITICAL LANGUAGE RULE" in prompt
        assert "Kazakh" in prompt

    def test_locale_english_no_directive(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL, locale="en")
        assert "CRITICAL LANGUAGE RULE" not in prompt

    def test_locale_none_no_directive(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL, locale=None)
        assert "CRITICAL LANGUAGE RULE" not in prompt

    def test_locale_unknown_uses_code(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL, locale="fr")
        assert "CRITICAL LANGUAGE RULE" in prompt
        assert "fr" in prompt

    def test_locale_to_language_mapping(self):
        assert LOCALE_TO_LANGUAGE["ru"] == "Russian"
        assert LOCALE_TO_LANGUAGE["kz"] == "Kazakh"
        assert LOCALE_TO_LANGUAGE["en"] == "English"

    def test_prompt_contains_set_fen_example(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL)
        assert "set_fen" in prompt
        assert "draw_arrows" in prompt
        assert "Scholar's Mate" in prompt

    def test_prompt_contains_example_fen(self):
        prompt = build_system_prompt(soul_content=MOCK_SOUL)
        assert "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4" in prompt


@pytest.mark.unit
class TestCcpAnalysisInjection:
    """Board analysis prefers the Mastra CCP service, falls back to local port."""

    def test_ccp_service_success_uses_mastra_block(self, monkeypatch):
        # CCP returns a valid analysis -> Mastra block appears...
        def fake_post(url, json=None, timeout=None):
            return _FakeResponse(200, {"valid": True, "board_analysis": CCP_BLOCK})

        monkeypatch.setattr(httpx, "post", fake_post)

        # ...and the local port must NOT be consulted.
        def boom(fen):
            raise AssertionError("local build_board_analysis must not be called")

        import src.tools.tactical_board as tactical_board
        monkeypatch.setattr(tactical_board, "build_board_analysis", boom)

        prompt = build_system_prompt(
            soul_content=MOCK_SOUL, board_fen=chess.STARTING_FEN
        )
        assert CCP_BLOCK in prompt

    def test_ccp_failure_falls_back_to_local_port(self, monkeypatch):
        # CCP raises (timeout/connection/non-200) -> fall back to local port.
        def fake_post(url, json=None, timeout=None):
            raise httpx.ConnectError("boom")

        monkeypatch.setattr(httpx, "post", fake_post)

        import src.tools.tactical_board as tactical_board
        monkeypatch.setattr(
            tactical_board, "build_board_analysis", lambda fen: LOCAL_BLOCK
        )

        prompt = build_system_prompt(
            soul_content=MOCK_SOUL, board_fen=chess.STARTING_FEN
        )
        assert LOCAL_BLOCK in prompt
        assert CCP_BLOCK not in prompt

    def test_ccp_non200_falls_back_to_local_port(self, monkeypatch):
        monkeypatch.setattr(
            httpx, "post", lambda *a, **k: _FakeResponse(503, {"error": "down"})
        )
        import src.tools.tactical_board as tactical_board
        monkeypatch.setattr(
            tactical_board, "build_board_analysis", lambda fen: LOCAL_BLOCK
        )
        prompt = build_system_prompt(
            soul_content=MOCK_SOUL, board_fen=chess.STARTING_FEN
        )
        assert LOCAL_BLOCK in prompt

    def test_both_paths_failing_does_not_raise(self, monkeypatch):
        # Invalid FEN with both paths failing -> build_prompt returns cleanly.
        def fake_post(url, json=None, timeout=None):
            raise httpx.ConnectError("boom")

        monkeypatch.setattr(httpx, "post", fake_post)

        import src.tools.tactical_board as tactical_board

        def boom(fen):
            raise ValueError("bad fen")

        monkeypatch.setattr(tactical_board, "build_board_analysis", boom)

        prompt = build_system_prompt(
            soul_content=MOCK_SOUL, board_fen="not-a-valid-fen"
        )
        assert "Chess Coach" in prompt

    def test_fetch_ccp_analysis_helper_returns_none_on_invalid_body(self, monkeypatch):
        monkeypatch.setattr(
            httpx, "post", lambda *a, **k: _FakeResponse(200, {"valid": False, "board_analysis": ""})
        )
        assert prompt_builder._fetch_ccp_analysis(chess.STARTING_FEN) is None
