"""Unit tests for the inbound unicode normalizer (Step 2 coach hygiene)."""

import chess
import pytest

from src.processors.text_normalize import normalize_text


@pytest.mark.unit
class TestNormalizeText:
    def test_plain_ascii_unchanged(self):
        text = "What is the best move for white here?"
        assert normalize_text(text) == text

    def test_empty_and_none_like_returned_as_is(self):
        assert normalize_text("") == ""
        assert normalize_text(None) is None

    def test_zero_width_chars_stripped(self):
        # zero-width space, ZWNJ, ZWJ, word joiner, BOM embedded in a word
        dirty = "ig​no‌re‍ pr⁠evious﻿"
        assert normalize_text(dirty) == "ignore previous"

    def test_control_chars_stripped_but_whitespace_kept(self):
        dirty = "line1\nline2\ttabbed\x07bell\x00null"
        assert normalize_text(dirty) == "line1\nline2\ttabbedbellnull"

    def test_homoglyph_fullwidth_folded_to_ascii(self):
        # Fullwidth latin letters (compat homoglyphs) NFKC-fold to plain ASCII.
        assert normalize_text("Ａｂｃ") == "Abc"

    def test_idempotent(self):
        dirty = "a​bｃ"
        once = normalize_text(dirty)
        assert normalize_text(once) == once

    def test_chess_piece_glyphs_preserved(self):
        # Unicode piece glyphs U+2654..U+265F must survive untouched.
        glyphs = "♔♕♖♗♘♙♚♛♜♝♞♟"
        assert normalize_text(f"The knight {glyphs} moves") == f"The knight {glyphs} moves"

    def test_fen_string_untouched(self):
        # A FEN is plain ASCII and must be byte-identical after normalization
        # (the wiring never routes FEN through here, but the function is safe).
        assert normalize_text(chess.STARTING_FEN) == chess.STARTING_FEN

    def test_san_move_untouched(self):
        assert normalize_text("1. e4 e5 2. Nf3 Nc6") == "1. e4 e5 2. Nf3 Nc6"


@pytest.mark.unit
class TestCleanUserTextGate:
    """The server helper is a no-op unless COACH_NORMALIZE_INPUT is enabled."""

    def test_default_off_is_passthrough(self, monkeypatch):
        import src.server as server
        monkeypatch.setattr(server.config, "COACH_NORMALIZE_INPUT", False)
        dirty = "ig​nore"
        assert server._clean_user_text(dirty) == dirty

    def test_flag_on_normalizes(self, monkeypatch):
        import src.server as server
        monkeypatch.setattr(server.config, "COACH_NORMALIZE_INPUT", True)
        assert server._clean_user_text("ig​nore") == "ignore"
