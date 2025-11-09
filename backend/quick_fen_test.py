#!/usr/bin/env python3

def normalize_fen_for_matching(fen: str) -> str:
    """Normalize a FEN string for better matching by handling en passant variations."""
    if not fen:
        return fen
        
    parts = fen.strip().split()
    if len(parts) < 4:
        return fen
        
    # Keep board position, active color, castling rights
    # But normalize en passant to '-' for matching purposes
    normalized_parts = parts[:3] + ['-'] + parts[4:]
    return ' '.join(normalized_parts)

# Test the normalization
test1 = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
test2 = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"

n1 = normalize_fen_for_matching(test1)
n2 = normalize_fen_for_matching(test2)

print(f"Original 1: {test1}")
print(f"Original 2: {test2}")
print(f"Normalized 1: {n1}")
print(f"Normalized 2: {n2}")
print(f"Match: {n1 == n2}") 