"""
Game Review — Phase 2 move classification cascade + opening/book detection.

Pure logic (no engine calls): given per-ply context built by ``game_review``
(evals already computed), assign each ply a Chess.com-style classification and
detect the opening / book plies from a bundled ECO table.

The cascade is evaluated IN ORDER, first match wins (Part A Step 5 of the
teardown spec):

    book → forced → brilliant → great → best → miss → win%-drop bucket

Everything is computed in WIN% space from the MOVER's point of view so Black
moves get the same sign treatment as White ones. Thresholds are module-level
constants so they are easy to tune.
"""

from __future__ import annotations

import csv
import glob
import io
import os

import chess
import chess.pgn

# ---------------------------------------------------------------------------
# Tunable thresholds (all in win% points unless noted)
# ---------------------------------------------------------------------------
# Forced: every alternative loses.
FORCED_SECOND_MAX_WIN = 20.0   # 2nd-best line leaves the mover losing
FORCED_BEST_MIN_WIN = 45.0     # ...while the best move keeps the mover afloat

# Great: the uniquely good move (best line dominates the 2nd line).
GREAT_GAP = 15.0

# Brilliant: a sound sacrifice that the engine also approves of.
BRILLIANT_MAX_DROP = 2.0       # played move ≈ engine best
BRILLIANT_MAX_WINNING = 90.0   # not already completely winning before
BRILLIANT_MIN_SOUND = 50.0     # position stays sound (mover still >= equal) after

# Miss: fails to punish the opponent's just-played mistake/blunder.
MISS_GAP = 15.0

# Win%-drop buckets (mover POV): drop = winBefore - winAfter.
EXCELLENT_MAX = 2.0
GOOD_MAX = 5.0
INACCURACY_MAX = 10.0
MISTAKE_MAX = 20.0
# ...anything worse is a blunder.

# Sacrifice detector: net raw material (pawns) the move must give up.
SAC_MIN = 2.0

# Book detection: how far into the game to look, and how many consecutive
# out-of-book plies to tolerate before declaring book over (handles small gaps
# in the ECO table without letting a late transposition re-open the book).
MAX_BOOK_PLY = 40
BOOK_GAP_TOLERANCE = 2

# Endgame detection.
ENDGAME_NONPAWN = 20  # total non-pawn, non-king material (both sides) at/below → endgame
OPENING_FALLBACK_PLIES = 20  # "first ~10 full moves" when no book was detected

# The full set of tally buckets (also the frozen order for the schema).
CLASSIFICATIONS = (
    "brilliant", "great", "best", "excellent", "good", "book",
    "inaccuracy", "mistake", "miss", "blunder", "forced",
)
KEY_MOMENT_CLASSES = frozenset({"brilliant", "great", "mistake", "miss", "blunder"})

_PIECE_VALUE = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100,
}

_OPENINGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "openings"
)


# ---------------------------------------------------------------------------
# Opening / book detection
# ---------------------------------------------------------------------------
_OPENING_TABLE: dict[str, tuple[str, str]] | None = None


def _load_opening_table() -> dict[str, tuple[str, str]]:
    """Lazily build {position-epd: (eco, name)} from the bundled ECO TSVs.

    The EPD (pieces + side + castling + en-passant, no move counters) uniquely
    identifies a position, so transposing into a known line still matches.
    """
    global _OPENING_TABLE
    if _OPENING_TABLE is not None:
        return _OPENING_TABLE

    table: dict[str, tuple[str, str]] = {}
    for path in sorted(glob.glob(os.path.join(_OPENINGS_DIR, "*.tsv"))):
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                game = chess.pgn.read_game(io.StringIO(row["pgn"]))
                if game is None:
                    continue
                board = game.board()
                for mv in game.mainline_moves():
                    board.push(mv)
                # First writer wins (stable, deterministic file/line order).
                table.setdefault(board.epd(), (row["eco"], row["name"]))
    _OPENING_TABLE = table
    return table


def detect_opening(epds: list[str]) -> dict:
    """Detect the opening and last book ply from the game's position EPDs.

    ``epds`` is the EPD of every position P0..PN (index 0 = start position).
    Returns ``{"eco", "name", "lastBookPly"}``. A ply ``i`` is a book move while
    ``i <= lastBookPly``.
    """
    table = _load_opening_table()
    eco: str | None = None
    name: str | None = None
    last_book_ply = 0
    misses = 0
    for j in range(1, min(len(epds) - 1, MAX_BOOK_PLY) + 1):
        hit = table.get(epds[j])
        if hit is not None:
            eco, name = hit
            last_book_ply = j
            misses = 0
        else:
            misses += 1
            if misses > BOOK_GAP_TOLERANCE:
                break
    return {"eco": eco, "name": name, "lastBookPly": last_book_ply}


# ---------------------------------------------------------------------------
# Sacrifice detector (static exchange evaluation)
# ---------------------------------------------------------------------------
def _see(board: chess.Board, square: int, side: bool) -> int:
    """Material ``side`` can win by initiating captures on ``square``.

    Classic static-exchange swap: always grab with the least-valuable attacker,
    recurse, and let each side stand pat if continuing would lose material.
    Sliding x-ray attackers are revealed automatically because ``attackers`` is
    recomputed from occupancy after each capture.
    """
    victim = board.piece_at(square)
    if victim is None:
        return 0
    attackers = board.attackers(side, square)
    if not attackers:
        return 0
    from_sq = min(attackers, key=lambda s: _PIECE_VALUE[board.piece_type_at(s)])
    piece_type = board.piece_type_at(from_sq)

    nxt = board.copy(stack=False)
    nxt.remove_piece_at(from_sq)
    nxt.set_piece_at(square, chess.Piece(piece_type, side))
    nxt.turn = not side
    gain = _PIECE_VALUE[victim.piece_type] - _see(nxt, square, not side)
    return max(0, gain)  # option to not recapture


def move_sacrifices_material(board_before: chess.Board, move: chess.Move) -> bool:
    """True if the move gives up raw material (>= SAC_MIN pawns) that the
    opponent can win by force on the moved piece's destination square."""
    captured = 0
    if board_before.is_capture(move):
        if board_before.is_en_passant(move):
            captured = _PIECE_VALUE[chess.PAWN]
        else:
            taken = board_before.piece_at(move.to_square)
            captured = _PIECE_VALUE[taken.piece_type] if taken else 0

    after = board_before.copy(stack=False)
    after.push(move)
    opponent = after.turn  # side to move after our move
    see_loss = _see(after, move.to_square, opponent)
    net = captured - see_loss
    return net <= -SAC_MIN


# ---------------------------------------------------------------------------
# Classification cascade
# ---------------------------------------------------------------------------
def _bucket(drop: float) -> str:
    if drop < EXCELLENT_MAX:
        return "excellent"
    if drop < GOOD_MAX:
        return "good"
    if drop < INACCURACY_MAX:
        return "inaccuracy"
    if drop < MISTAKE_MAX:
        return "mistake"
    return "blunder"


def classify_ply(ctx: dict, prev_classification: str | None) -> str:
    """Classify one ply. ``ctx`` keys:

        is_book            bool   — position before the move is still in book
        board_before       Board  — position the move is played from
        move               Move
        played_uci         str
        best_uci           str|None
        win_before_mover   float  — mover-POV win% before the move (== best line)
        win_after_mover    float  — mover-POV win% after the move
        second_win_mover   float|None — mover-POV win% of the engine's 2nd line
        n_legal            int    — legal moves in the position before the move

    ``prev_classification`` is the classification of the OPPONENT's previous ply
    (None for ply 1) — the cascade is stateful for Miss detection.
    """
    if ctx["is_book"]:
        return "book"

    played_best = ctx["best_uci"] is not None and ctx["played_uci"] == ctx["best_uci"]
    drop = ctx["win_before_mover"] - ctx["win_after_mover"]

    # 2 — Forced: only legal move, or every alternative loses.
    if played_best:
        second = ctx["second_win_mover"]
        only_move = ctx["n_legal"] <= 1 or second is None
        margin_forced = (
            second is not None
            and second <= FORCED_SECOND_MAX_WIN
            and ctx["win_before_mover"] >= FORCED_BEST_MIN_WIN
        )
        if only_move or margin_forced:
            return "forced"

    # 3 — Brilliant: a sound sacrifice the engine also plays.
    if (
        (played_best or drop <= BRILLIANT_MAX_DROP)
        and ctx["win_before_mover"] < BRILLIANT_MAX_WINNING
        and ctx["win_after_mover"] >= BRILLIANT_MIN_SOUND
        and move_sacrifices_material(ctx["board_before"], ctx["move"])
    ):
        return "brilliant"

    # 4 — Great: the uniquely good (non-sacrificial) move.
    if played_best and ctx["second_win_mover"] is not None:
        if ctx["win_before_mover"] - ctx["second_win_mover"] >= GREAT_GAP:
            return "great"

    # 5 — Best.
    if played_best:
        return "best"

    # 6 — Miss: opponent just erred and the mover fails to punish.
    if prev_classification in ("mistake", "blunder") and drop >= MISS_GAP:
        return "miss"

    # 7 — Win%-drop bucket (negative drop = improvement → excellent).
    return _bucket(max(0.0, drop))


def classify_game(ply_contexts: list[dict]) -> list[str]:
    """Classify every ply in order, threading the previous classification
    through so Miss detection is stateful across plies."""
    out: list[str] = []
    prev: str | None = None
    for ctx in ply_contexts:
        label = classify_ply(ctx, prev)
        out.append(label)
        prev = label
    return out


# ---------------------------------------------------------------------------
# Phase detection
# ---------------------------------------------------------------------------
def non_pawn_material(board: chess.Board) -> int:
    """Total non-pawn, non-king material on the board (both colors)."""
    total = 0
    for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        total += _PIECE_VALUE[pt] * (
            len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK))
        )
    return total


def is_endgame(board: chess.Board) -> bool:
    """Endgame once the queens are off OR non-pawn material is low."""
    queens = board.pieces(chess.QUEEN, chess.WHITE) or board.pieces(
        chess.QUEEN, chess.BLACK
    )
    return not queens or non_pawn_material(board) <= ENDGAME_NONPAWN


def phase_for_ply(ply: int, last_book_ply: int, board_after: chess.Board) -> str:
    """Phase of a ply: opening (while in book / first moves) → endgame → middlegame."""
    opening_limit = last_book_ply if last_book_ply > 0 else OPENING_FALLBACK_PLIES
    if ply <= opening_limit:
        return "opening"
    if is_endgame(board_after):
        return "endgame"
    return "middlegame"


# ---------------------------------------------------------------------------
# Estimated rating (calibrated accuracy → Elo lookup)
# ---------------------------------------------------------------------------
# (min game accuracy, Elo) anchor points; interpolated between anchors.
_RATING_TABLE = [
    (99.0, 2700),
    (95.0, 2400),
    (90.0, 2100),
    (85.0, 1850),
    (80.0, 1600),
    (75.0, 1400),
    (70.0, 1200),
    (60.0, 1000),
    (50.0, 800),
    (0.0, 600),
]


def est_rating(accuracy: float, move_count: int) -> int:
    """Estimate Elo from a player's game accuracy, nudged toward a neutral
    1200 for very short games where accuracy is unreliable."""
    elo = float(_RATING_TABLE[-1][1])
    for i, (acc_lo, elo_lo) in enumerate(_RATING_TABLE):
        if accuracy >= acc_lo:
            if i == 0:
                elo = float(elo_lo)
            else:
                acc_hi, elo_hi = _RATING_TABLE[i - 1]
                frac = (accuracy - acc_lo) / (acc_hi - acc_lo)
                elo = elo_lo + frac * (elo_hi - elo_lo)
            break

    # Short-game confidence blend toward 1200 (full weight from ~12 moves up).
    if move_count < 12:
        w = move_count / 12.0
        elo = w * elo + (1.0 - w) * 1200.0

    return int(round(elo / 10.0) * 10)


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------
def empty_tally() -> dict[str, dict[str, int]]:
    return {
        "w": {c: 0 for c in CLASSIFICATIONS},
        "b": {c: 0 for c in CLASSIFICATIONS},
    }
