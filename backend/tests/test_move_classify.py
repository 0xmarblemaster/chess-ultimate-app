"""
Tests for the Game Review Phase 2 classification cascade, sacrifice detector,
opening/book detection, phase detection and estimated rating.

The cascade tests use HAND-BUILT ply context (no engine): each classification is
reachable, cascade order is respected, and Miss detection is stateful.
"""

import chess
import pytest

from services import move_classify as mc


# ---------------------------------------------------------------------------
# Context builder — a quiet, non-sacrificial default move (1. e4).
# ---------------------------------------------------------------------------
def make_ctx(**overrides):
    ctx = {
        "is_book": False,
        "board_before": chess.Board(),
        "move": chess.Move.from_uci("e2e4"),
        "played_uci": "e2e4",
        "best_uci": "e2e4",
        "win_before_mover": 50.0,
        "win_after_mover": 50.0,
        "second_win_mover": 48.0,
        "n_legal": 20,
    }
    ctx.update(overrides)
    return ctx


# ---------------------------------------------------------------------------
# Cascade — each classification reachable, order respected
# ---------------------------------------------------------------------------
def test_book_wins_over_best():
    # Even a played-best move is Book while still in the opening table.
    assert mc.classify_ply(make_ctx(is_book=True), None) == "book"


def test_forced_only_legal_move():
    assert mc.classify_ply(make_ctx(n_legal=1), None) == "forced"


def test_forced_by_wide_margin():
    # Best keeps the mover afloat; every alternative loses badly.
    ctx = make_ctx(win_before_mover=70.0, win_after_mover=70.0, second_win_mover=10.0)
    assert mc.classify_ply(ctx, None) == "forced"


def test_great_only_good_move():
    # Big gap best-vs-second, played best, not a sacrifice, not forced.
    ctx = make_ctx(win_before_mover=70.0, win_after_mover=70.0, second_win_mover=50.0)
    assert mc.classify_ply(ctx, None) == "great"


def test_best_plain():
    ctx = make_ctx(win_before_mover=55.0, win_after_mover=55.0, second_win_mover=52.0)
    assert mc.classify_ply(ctx, None) == "best"


def test_bucket_excellent_good_inaccuracy_mistake_blunder():
    base = dict(best_uci="a2a4", win_before_mover=60.0)  # played != best
    assert mc.classify_ply(make_ctx(**base, win_after_mover=59.0), None) == "excellent"
    assert mc.classify_ply(make_ctx(**base, win_after_mover=56.0), None) == "good"
    assert mc.classify_ply(make_ctx(**base, win_after_mover=52.0), None) == "inaccuracy"
    assert mc.classify_ply(make_ctx(**base, win_after_mover=45.0), None) == "mistake"
    assert mc.classify_ply(make_ctx(**base, win_after_mover=30.0), None) == "blunder"


def test_improving_move_is_excellent():
    # A move that raises the mover's win% has a negative drop → excellent.
    ctx = make_ctx(best_uci="a2a4", win_before_mover=50.0, win_after_mover=65.0)
    assert mc.classify_ply(ctx, None) == "excellent"


# ---------------------------------------------------------------------------
# Miss — stateful on the opponent's previous move
# ---------------------------------------------------------------------------
def test_miss_requires_prior_blunder():
    # Same big drop: a Miss only if the opponent just blundered, else a blunder.
    ctx = make_ctx(best_uci="a2a4", win_before_mover=80.0, win_after_mover=60.0)
    assert mc.classify_ply(ctx, "blunder") == "miss"
    assert mc.classify_ply(ctx, "mistake") == "miss"
    assert mc.classify_ply(ctx, None) == "blunder"
    assert mc.classify_ply(ctx, "best") == "blunder"


def test_classify_game_threads_previous():
    # ply1: white blunders (big drop). ply2: black fails to punish → miss.
    p1 = make_ctx(best_uci="a2a4", win_before_mover=70.0, win_after_mover=55.0)
    p2 = make_ctx(best_uci="a7a5", win_before_mover=80.0, win_after_mover=60.0)
    labels = mc.classify_game([p1, p2])
    assert labels == ["mistake", "miss"]


# ---------------------------------------------------------------------------
# POV-agnostic buckets (Black moves fed as mover-POV win% must classify right)
# ---------------------------------------------------------------------------
def test_mover_pov_black_blunder_and_good():
    # These win% are already in the (Black) mover's POV, as game_review supplies.
    blunder = make_ctx(best_uci="a7a5", win_before_mover=70.0, win_after_mover=40.0)
    assert mc.classify_ply(blunder, None) == "blunder"
    good = make_ctx(best_uci="a7a5", win_before_mover=50.0, win_after_mover=47.0)
    assert mc.classify_ply(good, None) == "good"


# ---------------------------------------------------------------------------
# Sacrifice detector
# ---------------------------------------------------------------------------
def test_greek_gift_is_a_sacrifice():
    # White Bd3 takes h7; Black king (g8) recaptures with no white support.
    board = chess.Board(
        "rnbq1rk1/ppp2ppp/4pn2/3p4/3P4/3BPN2/PPP2PPP/RNBQ1RK1 w - - 0 1"
    )
    move = chess.Move.from_uci("d3h7")
    assert board.is_capture(move)
    assert mc.move_sacrifices_material(board, move) is True


def test_even_capture_recapture_is_not_a_sacrifice():
    # exd5: pawn takes a pawn defended by a pawn (net 0 material).
    board = chess.Board(
        "rnbqkbnr/ppp2ppp/4p3/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 3"
    )
    move = chess.Move.from_uci("e4d5")
    assert board.is_capture(move)
    assert mc.move_sacrifices_material(board, move) is False


def test_brilliant_needs_the_sacrifice():
    board = chess.Board(
        "rnbq1rk1/ppp2ppp/4pn2/3p4/3P4/3BPN2/PPP2PPP/RNBQ1RK1 w - - 0 1"
    )
    ctx = make_ctx(
        board_before=board,
        move=chess.Move.from_uci("d3h7"),
        played_uci="d3h7",
        best_uci="d3h7",
        win_before_mover=60.0,
        win_after_mover=58.0,
        second_win_mover=40.0,
    )
    assert mc.classify_ply(ctx, None) == "brilliant"

    # Same numbers but not the sacrifice destination → falls through to best.
    quiet = dict(
        ctx, move=chess.Move.from_uci("g1f3"), played_uci="g1f3", best_uci="g1f3",
        second_win_mover=57.0,  # small gap → plain best, not great
    )
    assert mc.classify_ply(quiet, None) == "best"


def test_already_winning_sacrifice_is_not_brilliant():
    board = chess.Board(
        "rnbq1rk1/ppp2ppp/4pn2/3p4/3P4/3BPN2/PPP2PPP/RNBQ1RK1 w - - 0 1"
    )
    ctx = make_ctx(
        board_before=board,
        move=chess.Move.from_uci("d3h7"),
        played_uci="d3h7",
        best_uci="d3h7",
        win_before_mover=95.0,  # already completely winning
        win_after_mover=93.0,
        second_win_mover=90.0,
    )
    assert mc.classify_ply(ctx, None) != "brilliant"


# ---------------------------------------------------------------------------
# Opening / book detection
# ---------------------------------------------------------------------------
def _epds(sans):
    board = chess.Board()
    out = [board.epd()]
    for san in sans:
        board.push_san(san)
        out.append(board.epd())
    return out


def test_detect_italian_game():
    opening = mc.detect_opening(_epds(["e4", "e5", "Nf3", "Nc6", "Bc4"]))
    assert opening["eco"].startswith("C5")
    assert "Italian" in opening["name"]
    assert opening["lastBookPly"] == 5


def test_detect_opening_no_book_hit():
    # A nonsense sequence leaves book almost immediately.
    opening = mc.detect_opening(_epds(["a4", "b5", "axb5", "a6"]))
    assert opening["lastBookPly"] < 4


# ---------------------------------------------------------------------------
# Phase detection
# ---------------------------------------------------------------------------
def test_phase_opening_while_in_book():
    assert mc.phase_for_ply(3, last_book_ply=6, board_after=chess.Board()) == "opening"


def test_phase_endgame_when_queens_off():
    board = chess.Board("8/5k2/8/8/8/8/3K1R2/8 w - - 0 1")  # K+R vs K
    assert mc.is_endgame(board) is True
    assert mc.phase_for_ply(40, last_book_ply=8, board_after=board) == "endgame"


def test_phase_middlegame():
    # Full material, past the opening window, queens on → middlegame.
    board = chess.Board()  # start pos has queens + full material
    assert mc.is_endgame(board) is False
    assert mc.phase_for_ply(25, last_book_ply=8, board_after=board) == "middlegame"


# ---------------------------------------------------------------------------
# Estimated rating
# ---------------------------------------------------------------------------
def test_est_rating_monotonic():
    assert mc.est_rating(95.0, 30) > mc.est_rating(70.0, 30) > mc.est_rating(50.0, 30)


def test_est_rating_short_game_pulls_toward_neutral():
    # A 2-move game at high accuracy is unreliable → pulled toward ~1200.
    assert mc.est_rating(95.0, 2) < mc.est_rating(95.0, 30)


def test_est_rating_returns_int():
    r = mc.est_rating(82.5, 40)
    assert isinstance(r, int)
    assert 500 <= r <= 2800
