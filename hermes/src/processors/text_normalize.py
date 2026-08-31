"""Unicode normalizer for inbound free-text user messages.

A small, pure hygiene pass that mirrors the upstream Mastra ``UnicodeNormalizer``
and pairs with Tirith prompt-injection defenses. It:

  * NFKC-normalizes text (folds compatibility homoglyphs such as fullwidth or
    styled letters back to their canonical form), and
  * strips zero-width joiners/spaces and control/format characters that are
    commonly used to smuggle invisible instructions past a reviewer.

Apply ONLY to free-text user content — never to FEN/PGN or structured tool
args, where an exact byte-for-byte value matters. Ordinary ASCII and legitimate
chess symbols (piece glyphs ♔–♟, board coordinates) pass through unchanged.
"""

import unicodedata

# Invisible format characters removed outright. NFKC alone does not delete
# these — several are category Cf and would otherwise survive normalization.
_ZERO_WIDTH_CHARS = frozenset(
    {
        "​",  # zero-width space
        "‌",  # zero-width non-joiner
        "‍",  # zero-width joiner
        "⁠",  # word joiner
        "﻿",  # BOM / zero-width no-break space
        "᠎",  # mongolian vowel separator
    }
)

# Whitespace control chars that are legitimate in free text and must be kept.
_ALLOWED_CONTROL = frozenset({"\n", "\r", "\t"})


def normalize_text(text: str) -> str:
    """Return *text* NFKC-normalized with zero-width/control chars stripped.

    Pure and idempotent. Empty/falsy input is returned unchanged. Newlines,
    carriage returns and tabs are preserved; all other control (Cc) and format
    (Cf) characters — including explicit zero-width joiners — are dropped.
    """
    if not text:
        return text

    normalized = unicodedata.normalize("NFKC", text)

    cleaned = []
    for ch in normalized:
        if ch in _ZERO_WIDTH_CHARS:
            continue
        if ch in _ALLOWED_CONTROL:
            cleaned.append(ch)
            continue
        if unicodedata.category(ch) in ("Cc", "Cf"):
            continue
        cleaned.append(ch)
    return "".join(cleaned)
