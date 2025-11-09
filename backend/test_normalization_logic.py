#!/usr/bin/env python3

# Test the FEN normalization logic to understand the mismatch

target_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
database_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq -"

print(f"=== FEN NORMALIZATION ANALYSIS ===")
print(f"User FEN:     '{target_fen}'")
print(f"Database FEN: '{database_fen}'")

print(f"\n=== BREAKING DOWN THE FENS ===")

# Break down user FEN
user_parts = target_fen.split()
print(f"User FEN parts: {user_parts}")
print(f"  Board: {user_parts[0]}")
print(f"  Active color: {user_parts[1]}")
print(f"  Castling: {user_parts[2]}")
print(f"  En passant: {user_parts[3]}")
print(f"  Halfmove: {user_parts[4]}")
print(f"  Fullmove: {user_parts[5]}")

# Break down database FEN
db_parts = database_fen.split()
print(f"\nDatabase FEN parts: {db_parts}")
print(f"  Board: {db_parts[0]}")
print(f"  Active color: {db_parts[1]}")
print(f"  Castling: {db_parts[2]}")
print(f"  En passant: {db_parts[3]}")
print(f"  No halfmove/fullmove counters!")

print(f"\n=== TESTING NORMALIZATION APPROACHES ===")

# Current normalization (what enhanced retriever does)
print(f"1. Enhanced retriever normalization:")
if len(user_parts) >= 4:
    normalized_fen = ' '.join(user_parts[:3] + ['-'] + user_parts[4:])
    print(f"   Result: '{normalized_fen}'")
    print(f"   Matches database: {normalized_fen == database_fen}")

# Correct normalization (remove move counters)
print(f"\n2. Correct normalization (remove move counters):")
if len(user_parts) >= 4:
    correct_normalized = ' '.join(user_parts[:4])
    print(f"   Result: '{correct_normalized}'")
    print(f"   Matches database: {correct_normalized == database_fen}")

# Board-only comparison
print(f"\n3. Board position only:")
user_board = user_parts[0]
db_board = db_parts[0]
print(f"   User board: '{user_board}'")
print(f"   DB board: '{db_board}'")
print(f"   Matches: {user_board == db_board}")

print(f"\n=== RECOMMENDED FIX ===")
print(f"The enhanced retriever should:")
print(f"1. First try exact FEN match")
print(f"2. If no match, try FEN without move counters: '{correct_normalized}'")
print(f"3. If still no match, try board position search with LIKE") 