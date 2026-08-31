"""Dependency-free semantic tool subsetting for coach turns.

The coach ships every chess-tool schema on every turn, which is a large, mostly
irrelevant token payload. This selects a small, query-relevant subset via a
lightweight keyword/intent overlap score (no embedding model) while always
keeping a ``core`` set so coaching quality cannot collapse.

Kept intentionally simple and deterministic. Enabled only behind the
``COACH_TOOL_SUBSET`` flag; when off the coach sends the full toolset unchanged.
"""

import re

# Tools the coach needs for board setup + engine analysis on essentially every
# turn. Never dropped in the default (``full``) mode.
CORE_TOOLS = frozenset({"board_control", "analyze_position"})

# Board-render / FEN-parse tools that are redundant when the board is already
# rendered on the student's screen. Suppressed only in ``panel`` mode.
PANEL_SUPPRESSED_TOOLS = frozenset({"board_control"})

# High-frequency English words that carry no tool-selection signal.
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "is", "are", "of", "to", "in", "for", "on", "my", "me",
        "i", "what", "whats", "how", "do", "does", "did", "can", "could", "should",
        "would", "this", "that", "with", "and", "or", "get", "show", "please",
        "you", "your", "it", "at", "be", "was", "were", "here", "there", "about",
        "best", "good", "vs", "against", "play", "playing", "move", "moves",
    }
)


def _tokenize(text: str) -> set:
    """Lowercase alphanumeric tokens of *text* as a set."""
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _score(query_tokens: set, declaration: dict) -> int:
    """Overlap between the query tokens and a tool's name + description tokens."""
    haystack = _tokenize(declaration.get("name", "")) | _tokenize(
        declaration.get("description", "")
    )
    return len(query_tokens & haystack)


def select_tool_subset(
    declarations: list,
    query: str,
    topk: int = 7,
    mode: str = "full",
    core: frozenset = CORE_TOOLS,
    panel_suppressed: frozenset = PANEL_SUPPRESSED_TOOLS,
) -> list:
    """Return a query-relevant subset of *declarations*.

    Always includes the ``core`` tools (minus any suppressed in ``panel`` mode),
    then the ``topk`` highest-scoring remaining tools by keyword overlap with
    *query*. The result length is at most ``topk + len(core)``. Ordering is
    deterministic: core tools first (original order), then ranked others.

    In ``panel`` mode the board is already on screen, so board-render/FEN-parse
    tools in ``panel_suppressed`` are removed from the candidate pool and not
    force-included. Any other ``mode`` value behaves as ``full``.
    """
    if mode == "panel":
        declarations = [
            d for d in declarations if d.get("name") not in panel_suppressed
        ]
        core = core - panel_suppressed

    query_tokens = _tokenize(query) - _STOPWORDS

    core_decls = [d for d in declarations if d.get("name") in core]
    others = [d for d in declarations if d.get("name") not in core]

    # Stable sort keeps original relative order for equal scores -> deterministic.
    ranked = sorted(others, key=lambda d: _score(query_tokens, d), reverse=True)

    return core_decls + ranked[: max(topk, 0)]
