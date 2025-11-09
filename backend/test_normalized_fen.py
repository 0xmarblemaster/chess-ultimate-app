#!/usr/bin/env python3

from etl.agents.retriever_agent import normalize_fen_for_matching, retrieve_by_fen

def test_normalized_fen():
    """Test the normalized FEN matching functionality."""
    
    # Test FEN with en passant that should match database FEN without en passant
    test_fen_with_en_passant = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
    test_fen_without_en_passant = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    
    print("=== Testing FEN Normalization ===")
    print(f"Original FEN (with en passant): {test_fen_with_en_passant}")
    print(f"Expected FEN (without en passant): {test_fen_without_en_passant}")
    
    normalized_1 = normalize_fen_for_matching(test_fen_with_en_passant)
    normalized_2 = normalize_fen_for_matching(test_fen_without_en_passant)
    
    print(f"Normalized FEN 1: {normalized_1}")
    print(f"Normalized FEN 2: {normalized_2}")
    print(f"Normalized FENs match: {normalized_1 == normalized_2}")
    
    print("\n=== Testing retrieve_by_fen with normalized matching ===")
    
    # Test the retrieve_by_fen function
    results = retrieve_by_fen(test_fen_with_en_passant, limit=5)
    
    print(f"Results found: {len(results)}")
    for i, result in enumerate(results, 1):
        if result.get('type') == 'chess_game_search_result':
            print(f"  {i}. Game: {result.get('white_player')} vs {result.get('black_player')}")
            print(f"     UUID: {result.get('game_id')}")
            print(f"     Match type: {result.get('fen_match_type')}")
            print(f"     Matched FEN: {result.get('matched_fen')}")
        else:
            print(f"  {i}. {result.get('type', 'Unknown')}: {result}")

if __name__ == '__main__':
    test_normalized_fen() 