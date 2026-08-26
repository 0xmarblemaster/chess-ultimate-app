"""Voice tool bridge — expose the chess tool registry to the Gemini Live coach.

The text coach reaches the ~20 chess tools through the Hermes agent loop. The
voice coach (Gemini Live) does its own function-calling, so it needs:

  * ``GET  /api/coach/tools``        — every chess tool's schema in Gemini
                                        ``functionDeclarations`` format.
  * ``POST /api/coach/tool/{name}``  — dispatch one tool and return its result
                                        (plus any board actions it emitted).

Both endpoints are generic: the registry is the single source of truth, so no
tool schema is ever hand-copied here.
"""

import json
import logging
from typing import Any, Optional

import chess
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.board_protocol import ActionType
from src.sessions import session_store

try:
    from tools.registry import registry
except ImportError:  # pragma: no cover - registry always present in deployment
    registry = None

logger = logging.getLogger("hermes.tool_bridge")

router = APIRouter()

CHESS_TOOLSET = "chess"

# Keys that are valid JSON Schema but rejected by Gemini's function-calling
# schema (an OpenAPI 3.0 subset). Stripped recursively from every tool schema.
_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {"$schema", "additionalProperties", "default", "$ref", "definitions", "$defs"}
)

# Argument names that identify a user. The model must never be able to set
# these — they are always overridden server-side with the authenticated user.
_IDENTITY_ARG_KEYS = frozenset({"user_id"})

_BOARD_ACTION_TYPES = frozenset(e.value for e in ActionType)


def clean_gemini_schema(node: Any) -> Any:
    """Recursively strip JSON-Schema keys Gemini's function-calling rejects."""
    if isinstance(node, dict):
        return {
            key: clean_gemini_schema(value)
            for key, value in node.items()
            if key not in _UNSUPPORTED_SCHEMA_KEYS
        }
    if isinstance(node, list):
        return [clean_gemini_schema(item) for item in node]
    return node


def to_function_declaration(schema: dict, name: Optional[str] = None) -> dict:
    """Convert a registry tool schema to a Gemini functionDeclaration.

    The registry key (*name*) is authoritative — the same rule the agent's
    ``get_definitions`` uses — so a schema with a missing/blank ``name`` still
    produces a valid declaration.
    """
    parameters = clean_gemini_schema(schema.get("parameters", {}))
    return {
        "name": name or schema.get("name", ""),
        "description": schema.get("description", ""),
        "parameters": parameters,
    }


def build_tool_declarations() -> list[dict]:
    """Return Gemini functionDeclarations for every registered chess tool."""
    if registry is None:
        return []
    declarations = []
    for name in registry.get_tool_names_for_toolset(CHESS_TOOLSET):
        if not name:
            continue
        schema = registry.get_schema(name)
        if not schema:
            continue
        declarations.append(to_function_declaration(schema, name=name))
    return declarations


def _is_chess_tool(name: str) -> bool:
    """True when *name* is a tool registered under the chess toolset."""
    if registry is None:
        return False
    return registry.get_toolset_for_tool(name) == CHESS_TOOLSET


def _override_identity_args(name: str, args: dict, user_id: str) -> dict:
    """Force user-identity args to the authenticated user before dispatch.

    Overrides any identity key the model supplied, and also injects the id when
    the tool's schema declares an identity param the model omitted.
    """
    safe_args = dict(args)
    schema = registry.get_schema(name) if registry else None
    declared = set()
    if isinstance(schema, dict):
        props = schema.get("parameters", {}).get("properties", {})
        if isinstance(props, dict):
            declared = set(props.keys())
    for key in _IDENTITY_ARG_KEYS:
        if key in safe_args or key in declared:
            safe_args[key] = user_id
    return safe_args


def _final_fen_from_pgn(pgn: str) -> Optional[str]:
    """Return the FEN of the final position of a PGN, or None if unparseable."""
    import io

    import chess.pgn

    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            return None
        board = game.end().board()
        return board.fen()
    except Exception:
        return None


def _extract_board_actions(result: Any) -> list[dict]:
    """Return board-action dicts embedded in a parsed tool result."""
    actions: list[dict] = []
    candidates = result if isinstance(result, list) else [result]
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("type") in _BOARD_ACTION_TYPES:
            actions.append(candidate)
    return actions


def _sync_session_board(session, board_actions: list[dict]) -> None:
    """Update a session's board_state from set_fen / set_puzzle / load_pgn actions."""
    for action in board_actions:
        atype = action.get("type")
        fen = None
        if atype in (ActionType.SET_FEN.value, ActionType.SET_PUZZLE.value):
            fen = action.get("fen")
        elif atype == ActionType.LOAD_PGN.value and action.get("pgn"):
            fen = _final_fen_from_pgn(action["pgn"])
        if not fen:
            continue
        try:
            session.set_board_state(fen)
        except (ValueError, TypeError):
            logger.debug("Skipping board sync for invalid FEN: %s", fen)


class ToolDispatchRequest(BaseModel):
    args: dict[str, Any] = {}
    session_id: Optional[str] = None


def _get_user_id(request: Request) -> str:
    """Extract the required X-User-Id header."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return user_id


@router.get("/api/coach/tools")
async def coach_tools() -> dict:
    """Return chess tool schemas as Gemini functionDeclarations."""
    return {"tools": build_tool_declarations()}


@router.post("/api/coach/tool/{name}")
async def coach_tool_dispatch(name: str, body: ToolDispatchRequest, request: Request):
    """Dispatch a single chess tool for the voice coach.

    Returns ``{"result": ..., "board_actions": [...]}`` on success, or
    ``{"error": ...}`` (HTTP 200) when the tool fails — the voice model always
    needs a tool response, even on failure. Unknown tool -> 404.
    """
    user_id = _get_user_id(request)

    if not _is_chess_tool(name):
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")

    args = _override_identity_args(name, body.args or {}, user_id)

    # registry.dispatch catches handler exceptions and returns a JSON error
    # string, so this never raises for tool-internal failures.
    raw = registry.dispatch(name, args)

    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        parsed = raw

    if isinstance(parsed, dict) and "error" in parsed:
        return {"error": parsed["error"]}

    board_actions = _extract_board_actions(parsed)

    if body.session_id and board_actions:
        session = session_store.get(body.session_id, user_id)
        if session is not None:
            _sync_session_board(session, board_actions)

    return {"result": parsed, "board_actions": board_actions}
