"""Tactical motif detection ported from Mastra's CCP tacticalBoard.ts.

Given a FEN, detect tactical motifs using a faithful port of the TypeScript
CCP (chess-coach-protocol) logic:
  - per-side attack/defense square maps (x-ray through same-colour sliders)
  - hanging pieces (attacked with zero defenders)
  - semi-protected pieces (equal attackers/defenders)
  - pins (absolute and relative) with pinned/pinning/target squares

Pure python-chess for validation; the attack-map and pin geometry are ported
directly so the semantics (batteries via x-ray, relative-pin value rule) match
the original TypeScript detector.

Coordinate convention mirrors the TS source: board[x][y] where x is the file
(0=a .. 7=h) and y=0 is the 8th rank (top), y=7 is the 1st rank.
"""

import logging

import chess

logger = logging.getLogger(__name__)

# Piece values matching the TS getPieceValueByType (note: queen = 8, king = 1000)
_PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 8, "K": 1000}
_PIECE_NAMES = {
    "P": "pawn",
    "N": "knight",
    "B": "bishop",
    "R": "rook",
    "Q": "queen",
    "K": "king",
}

_KNIGHT_MOVES = [
    (-2, -1), (-2, 1), (-1, -2), (1, -2),
    (2, -1), (2, 1), (-1, 2), (1, 2),
]
_DIAGONALS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
_LINES = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _in_board(x: int, y: int) -> bool:
    return 0 <= x <= 7 and 0 <= y <= 7


def _coords_to_square(x: int, y: int) -> str:
    file_ = chr(x + ord("a"))
    rank = chr((7 - y) + ord("1"))
    return f"{file_}{rank}"


class TacticalBoard:
    """Faithful Python port of the TS TacticlBoard tactical detector."""

    def __init__(self, fen: str) -> None:
        # board[x][y], "" = empty, uppercase = white, lowercase = black
        self.board = [["" for _ in range(8)] for _ in range(8)]
        self.fen = fen
        self.squares_attacked_by_white = [[0] * 8 for _ in range(8)]
        self.squares_attacked_by_black = [[0] * 8 for _ in range(8)]

        self.hanging_pieces: list[dict] = []
        self.semi_protected_pieces: list[dict] = []
        self.white_pins: list[dict] = []
        self.black_pins: list[dict] = []

        self._parse_fen(fen)
        self._calculate_defenders_and_attackers()
        self._calculate_piece_vulnerability()
        self._detect_pins()

    # --- FEN parsing (board field only) -----------------------------------
    def _parse_fen(self, fen: str) -> None:
        board_field = fen.split(" ")[0] if fen else ""
        rank = 0
        file_ = 0
        for char in board_field:
            if "1" <= char <= "8":
                file_ += int(char)
            elif char == "/":
                rank += 1
                file_ = 0
            else:
                if _in_board(file_, rank):
                    self.board[file_][rank] = char
                file_ += 1

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _piece_type(char: str) -> str:
        return char.upper()

    @staticmethod
    def _is_white(char: str) -> bool:
        return char == char.upper()

    def _piece_value(self, char: str) -> int:
        return _PIECE_VALUES.get(char.upper(), 0)

    # --- attack / defense square maps -------------------------------------
    def _add_attacked_square(self, squares: list, x: int, y: int) -> None:
        if _in_board(x, y):
            squares[x][y] += 1

    def _add_ray(self, squares: list, is_white: bool, x: int, y: int,
                 dx: int, dy: int, diagonal: bool) -> None:
        # x-ray through friendly sliders that share the ray's geometry
        if diagonal:
            xrays = ["B", "Q"] if is_white else ["b", "q"]
        else:
            xrays = ["R", "Q"] if is_white else ["r", "q"]

        i, j = x, y
        while True:
            i += dx
            j += dy
            if not _in_board(i, j):
                break
            squares[i][j] += 1
            occupant = self.board[i][j]
            if not occupant:
                continue
            if occupant in xrays:
                continue
            break

    def _calculate_defenders_and_attackers(self) -> None:
        for y in range(8):
            for x in range(8):
                char = self.board[x][y]
                if not char:
                    continue
                is_white = self._is_white(char)
                squares = (
                    self.squares_attacked_by_white
                    if is_white
                    else self.squares_attacked_by_black
                )
                piece = self._piece_type(char)

                if piece == "P":
                    direction = -1 if is_white else 1
                    self._add_attacked_square(squares, x - 1, y + direction)
                    self._add_attacked_square(squares, x + 1, y + direction)
                elif piece == "N":
                    for dx, dy in _KNIGHT_MOVES:
                        self._add_attacked_square(squares, x + dx, y + dy)
                elif piece == "B":
                    for dx, dy in _DIAGONALS:
                        self._add_ray(squares, is_white, x, y, dx, dy, True)
                elif piece == "R":
                    for dx, dy in _LINES:
                        self._add_ray(squares, is_white, x, y, dx, dy, False)
                elif piece == "Q":
                    for dx, dy in _DIAGONALS:
                        self._add_ray(squares, is_white, x, y, dx, dy, True)
                    for dx, dy in _LINES:
                        self._add_ray(squares, is_white, x, y, dx, dy, False)
                elif piece == "K":
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx != 0 or dy != 0:
                                self._add_attacked_square(squares, x + dx, y + dy)

    # --- hanging & semi-protected -----------------------------------------
    def _calculate_piece_vulnerability(self) -> None:
        for y in range(8):
            for x in range(8):
                char = self.board[x][y]
                if not char:
                    continue
                piece = self._piece_type(char)
                if piece == "K":
                    continue

                is_white = self._is_white(char)
                defenders_map = (
                    self.squares_attacked_by_white
                    if is_white
                    else self.squares_attacked_by_black
                )
                attackers_map = (
                    self.squares_attacked_by_black
                    if is_white
                    else self.squares_attacked_by_white
                )
                attackers = attackers_map[x][y]
                defenders = defenders_map[x][y]

                entry = {
                    "piece": f"{'white' if is_white else 'black'} {_PIECE_NAMES[piece]}",
                    "square": _coords_to_square(x, y),
                    "color": "white" if is_white else "black",
                    "attackers": attackers,
                    "defenders": defenders,
                }

                if attackers > defenders and defenders == 0:
                    self.hanging_pieces.append(entry)
                elif attackers == defenders and attackers > 0:
                    self.semi_protected_pieces.append(entry)

    # --- pins -------------------------------------------------------------
    def _detect_pins(self) -> None:
        self.white_pins = self._detect_pins_for_color(True)
        self.black_pins = self._detect_pins_for_color(False)

    def _directions_for_piece(self, piece: str) -> list:
        if piece == "B":
            return _DIAGONALS
        if piece == "R":
            return _LINES
        if piece == "Q":
            return _DIAGONALS + _LINES
        return []

    def _detect_pins_for_color(self, attacker_is_white: bool) -> list:
        pins: list[dict] = []
        for y in range(8):
            for x in range(8):
                char = self.board[x][y]
                if not char:
                    continue
                if self._is_white(char) != attacker_is_white:
                    continue
                piece = self._piece_type(char)
                if piece not in ("B", "R", "Q"):
                    continue

                pinning_square = _coords_to_square(x, y)
                for dx, dy in self._directions_for_piece(piece):
                    result = self._check_direction_for_pin(
                        x, y, dx, dy, attacker_is_white
                    )
                    if result:
                        color = "white" if attacker_is_white else "black"
                        pins.append({
                            "pinnedPiece": result["pinnedPiece"],
                            "pinnedSquare": result["pinnedSquare"],
                            "pinningPiece": f"{color} {_PIECE_NAMES[piece]}",
                            "pinningSquare": pinning_square,
                            "targetPiece": result["targetPiece"],
                            "targetSquare": result["targetSquare"],
                            "isAbsolute": result["isAbsolute"],
                        })
        return pins

    def _check_direction_for_pin(self, x: int, y: int, dx: int, dy: int,
                                 attacker_is_white: bool):
        first = None
        second = None
        cx, cy = x + dx, y + dy
        while _in_board(cx, cy):
            char = self.board[cx][cy]
            if char:
                if first is None:
                    first = (char, cx, cy)
                elif second is None:
                    second = (char, cx, cy)
                    break
            cx += dx
            cy += dy

        if not (first and second):
            return None

        first_char, fx, fy = first
        second_char, sx, sy = second
        first_is_white = self._is_white(first_char)
        second_is_white = self._is_white(second_char)

        # Both blockers must belong to the enemy of the attacker.
        if first_is_white == attacker_is_white or second_is_white == attacker_is_white:
            return None

        first_value = self._piece_value(first_char)
        second_value = self._piece_value(second_char)
        is_absolute = self._piece_type(second_char) == "K"

        # Absolute pins always report; relative pins need a more valuable piece behind.
        if is_absolute or second_value > first_value:
            enemy_color = "black" if attacker_is_white else "white"
            return {
                "pinnedPiece": f"{enemy_color} {_PIECE_NAMES[self._piece_type(first_char)]}",
                "pinnedSquare": _coords_to_square(fx, fy),
                "targetPiece": f"{enemy_color} {_PIECE_NAMES[self._piece_type(second_char)]}",
                "targetSquare": _coords_to_square(sx, sy),
                "isAbsolute": is_absolute,
            }
        return None

    # --- output -----------------------------------------------------------
    def to_findings(self) -> dict:
        return {
            "hanging": self.hanging_pieces,
            "semi_protected": self.semi_protected_pieces,
            "pins": {"white": self.white_pins, "black": self.black_pins},
        }

    def to_tactical_text(self) -> str:
        lines: list[str] = []
        lines.append("=== PIECE VULNERABILITY ===")
        lines.append("HANGING PIECES (attacked with zero defenders — free captures):")
        if self.hanging_pieces:
            for p in self.hanging_pieces:
                lines.append(f"• {p['piece']} at {p['square']} — IMMEDIATE THREAT")
        else:
            lines.append("• No hanging pieces detected")

        lines.append("")
        lines.append("SEMI-PROTECTED PIECES (equal attackers/defenders — contested):")
        if self.semi_protected_pieces:
            for p in self.semi_protected_pieces:
                lines.append(f"• {p['piece']} at {p['square']} — CONTESTED")
        else:
            lines.append("• No semi-protected pieces detected")

        lines.append("")
        lines.append("=== PIN DETECTION ===")
        lines.append("ABSOLUTE PINS: pinned to the King (cannot legally move)")
        lines.append("RELATIVE PINS: pinned to a more valuable piece (moving loses material)")
        lines.append("")
        lines.append("WHITE PINS (White pinning Black):")
        lines.extend(self._pin_lines(self.white_pins, "White"))
        lines.append("")
        lines.append("BLACK PINS (Black pinning White):")
        lines.extend(self._pin_lines(self.black_pins, "Black"))
        return "\n".join(lines)

    @staticmethod
    def _pin_lines(pins: list, side: str) -> list:
        if not pins:
            return [f"• No pins by {side} detected"]
        out = []
        for pin in pins:
            kind = "ABSOLUTE PIN" if pin["isAbsolute"] else "RELATIVE PIN"
            out.append(
                f"• {kind}: {pin['pinningPiece']} at {pin['pinningSquare']} "
                f"pins {pin['pinnedPiece']} at {pin['pinnedSquare']} "
                f"to {pin['targetPiece']} at {pin['targetSquare']}"
            )
        return out


def detect_tactics(fen: str) -> dict:
    """Detect tactical motifs for a FEN. Returns empty findings on invalid FEN."""
    empty = {"hanging": [], "semi_protected": [], "pins": {"white": [], "black": []}}
    try:
        board = chess.Board(fen)
        if not board.is_valid():
            return empty
    except (ValueError, IndexError):
        return empty
    try:
        return TacticalBoard(fen).to_findings()
    except Exception:  # defensive: never crash the caller
        logger.debug("Tactical detection failed for FEN %s", fen, exc_info=True)
        return empty


def build_board_analysis(fen: str) -> str:
    """Assemble a structured <board_analysis> block for a FEN.

    Mirrors positionPrompter.ts's <detailed_board_analysis>: reuses
    score_position_themes for material/mobility/space/king-safety and adds the
    ported tactical motif section. Falls back gracefully on invalid FEN.
    """
    try:
        board = chess.Board(fen)
        if not board.is_valid():
            return ""
    except (ValueError, IndexError):
        return ""

    try:
        from src.tools.position_themes import score_position_themes

        themes = score_position_themes(fen)
        tactical = TacticalBoard(fen)
    except Exception:
        logger.debug("build_board_analysis failed for FEN %s", fen, exc_info=True)
        return ""

    lines: list[str] = ["<board_analysis>"]
    lines.append(f"<game_status>\nFEN: {fen}\n"
                 f"Active Player: {'White to move' if board.turn else 'Black to move'}\n"
                 f"Legal Moves: {board.legal_moves.count()}\n</game_status>")

    mat = themes.get("material", {})
    lines.append("<material_analysis>")
    lines.append(f"White material: {mat.get('white_material')}  "
                 f"Black material: {mat.get('black_material')}  "
                 f"Balance (White - Black): {mat.get('balance')}")
    lines.append("</material_analysis>")

    mob = themes.get("mobility", {})
    lines.append("<piece_mobility>")
    lines.append(f"White legal moves: {mob.get('white_moves')}  "
                 f"Black legal moves: {mob.get('black_moves')}")
    lines.append("</piece_mobility>")

    space = themes.get("space_control", {})
    lines.append("<space_control>")
    lines.append(f"Center control — White: {space.get('white_center')}  "
                 f"Black: {space.get('black_center')}  "
                 f"(extended: White {space.get('white_extended_center')}, "
                 f"Black {space.get('black_extended_center')})")
    lines.append("</space_control>")

    ks = themes.get("king_safety", {})
    lines.append("<king_safety_analysis>")
    lines.append(f"White pawn shield: {ks.get('white_pawn_shield')}  "
                 f"open files near king: {ks.get('white_open_files_near_king')}")
    lines.append(f"Black pawn shield: {ks.get('black_pawn_shield')}  "
                 f"open files near king: {ks.get('black_open_files_near_king')}")
    lines.append("</king_safety_analysis>")

    lines.append("<tactical_analysis>")
    lines.append(tactical.to_tactical_text())
    lines.append("</tactical_analysis>")

    lines.append("</board_analysis>")
    return "\n".join(lines)
