#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_chessgame_fen_search():
    """Test searching ChessGame collection for FEN matches"""
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl.agents.retriever_agent import normalize_fen_for_matching
        
        test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        normalized_test = normalize_fen_for_matching(test_fen)
        
        print(f"=== Testing ChessGame FEN Search ===")
        print(f"Test FEN: {test_fen}")
        print(f"Normalized: {normalized_test}")
        
        client = get_weaviate_client()
        collection = client.collections.get("ChessGame")
        
        # Get sample games to check their all_ply_fens
        results = collection.query.fetch_objects(limit=50)
        
        print(f"\\nChecking {len(results.objects)} games...")
        matches = []
        
        for obj in results.objects:
            props = obj.properties
            all_ply_fens = props.get('all_ply_fens', [])
            
            # Check if any FEN in the game matches our test FEN
            for fen in all_ply_fens:
                if fen == test_fen or normalize_fen_for_matching(fen) == normalized_test:
                    matches.append({
                        'uuid': obj.uuid,
                        'white_player': props.get('white_player', 'N/A'),
                        'black_player': props.get('black_player', 'N/A'),
                        'event': props.get('event', 'N/A'),
                        'eco': props.get('eco', 'N/A'),
                        'matched_fen': fen,
                        'pgn_moves': props.get('pgn_moves', '')[:100] + '...'  # First 100 chars
                    })
                    break  # Only count each game once
        
        print(f"\\n✅ Found {len(matches)} games with matching FEN:")
        for i, match in enumerate(matches[:5]):  # Show first 5 matches
            print(f"{i+1}. Game ID: {match['uuid']}")
            print(f"   Players: {match['white_player']} vs {match['black_player']}")
            print(f"   Event: {match['event']}")
            print(f"   ECO: {match['eco']}")
            print(f"   Matched FEN: {match['matched_fen']}")
            print(f"   PGN preview: {match['pgn_moves']}")
            print()
        
        # client.close() removed - Weaviate client manages connections automatically
        return len(matches) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chessgame_fen_search()
    if success:
        print("✅ ChessGame FEN search test PASSED")
    else:
        print("❌ ChessGame FEN search test FAILED") 