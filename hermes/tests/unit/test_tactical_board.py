"""Unit tests for the ported CCP tactical motif detector."""

import chess
import pytest

from src.tools.tactical_board import (
    TacticalBoard,
    build_board_analysis,
    detect_tactics,
)


@pytest.mark.unit
def test_absolute_pin_detected():
    """Black rook on e8 absolutely pins the white knight on e4 to the king on e1."""
    fen = "k3r3/8/8/8/4N3/8/8/4K3 w - - 0 1"
    result = detect_tactics(fen)
    black_pins = result["pins"]["black"]
    assert len(black_pins) == 1
    pin = black_pins[0]
    assert pin["isAbsolute"] is True
    assert pin["pinnedSquare"] == "e4"
    assert pin["pinningSquare"] == "e8"
    assert pin["targetSquare"] == "e1"
    assert "knight" in pin["pinnedPiece"]
    assert "king" in pin["targetPiece"]
    # No pins in the other direction.
    assert result["pins"]["white"] == []


@pytest.mark.unit
def test_relative_pin_detected():
    """Black bishop on a6 relatively pins the white knight on b5 to the queen on c4."""
    fen = "4k3/8/b7/1N6/2Q5/8/8/4K3 w - - 0 1"
    assert chess.Board(fen).is_valid()
    result = detect_tactics(fen)
    black_pins = result["pins"]["black"]
    assert len(black_pins) == 1
    pin = black_pins[0]
    assert pin["isAbsolute"] is False
    assert pin["pinnedSquare"] == "b5"
    assert pin["pinningSquare"] == "a6"
    assert pin["targetSquare"] == "c4"


@pytest.mark.unit
def test_hanging_piece_detected():
    """Black knight on e5 is attacked by the white d4 pawn and has no defenders."""
    fen = "4k3/8/8/4n3/3P4/8/8/4K3 w - - 0 1"
    result = detect_tactics(fen)
    hanging = result["hanging"]
    assert len(hanging) == 1
    assert hanging[0]["square"] == "e5"
    assert hanging[0]["color"] == "black"
    assert "knight" in hanging[0]["piece"]
    assert hanging[0]["defenders"] == 0
    assert hanging[0]["attackers"] >= 1


@pytest.mark.unit
def test_no_tactics_in_starting_position():
    """The starting position has no hanging/semi-protected pieces and no pins."""
    result = detect_tactics(chess.STARTING_FEN)
    assert result["hanging"] == []
    assert result["semi_protected"] == []
    assert result["pins"]["white"] == []
    assert result["pins"]["black"] == []


@pytest.mark.unit
def test_invalid_fen_handled_gracefully():
    """An invalid FEN returns empty findings without raising."""
    result = detect_tactics("not a fen")
    assert result["hanging"] == []
    assert result["semi_protected"] == []
    assert result["pins"] == {"white": [], "black": []}


@pytest.mark.unit
def test_semi_protected_piece_detected():
    """A piece with equal attackers and defenders is flagged as semi-protected."""
    # White pawn e4 and black pawn d5 attack each other; both are defended once.
    fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
    result = detect_tactics(fen)
    squares = {p["square"] for p in result["semi_protected"]}
    assert "e4" in squares or "d5" in squares


@pytest.mark.unit
def test_build_board_analysis_wraps_and_includes_tactics():
    """build_board_analysis returns a wrapped block with a tactical subsection."""
    fen = "k3r3/8/8/8/4N3/8/8/4K3 w - - 0 1"
    text = build_board_analysis(fen)
    assert isinstance(text, str)
    assert "<board_analysis>" in text
    assert "</board_analysis>" in text
    assert "<tactical_analysis>" in text
    # The absolute pin surfaces in the human-readable tactical section.
    assert "ABSOLUTE PIN" in text


@pytest.mark.unit
def test_build_board_analysis_invalid_fen_returns_empty():
    """An invalid FEN yields an empty string, never an exception."""
    assert build_board_analysis("garbage") == ""


@pytest.mark.unit
def test_tactical_board_class_findings_shape():
    """TacticalBoard.to_findings exposes the expected structure."""
    board = TacticalBoard(chess.STARTING_FEN)
    findings = board.to_findings()
    assert set(findings.keys()) == {"hanging", "semi_protected", "pins"}
    assert set(findings["pins"].keys()) == {"white", "black"}
