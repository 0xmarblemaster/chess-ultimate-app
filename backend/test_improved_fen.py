#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_improved_fen():
    """Test the improved FEN matching"""
    try:
        from backend.etl.agents.retriever_agent import retrieve_by_fen, normalize_fen_for_matching
        
        test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        print(f"Testing improved FEN matching...")
        print(f"Original FEN: {test_fen}")
        print(f"Normalized FEN: {normalize_fen_for_matching(test_fen)}")
        print()
        
        results = retrieve_by_fen(test_fen, limit=5)
        print(f"Results: {len(results)} items")
        
        for i, result in enumerate(results):
            print(f"\n{i+1}. Result:")
            if isinstance(result, dict):
                if result.get("type") == "chess_opening":
                    print(f"   Type: Opening")
                    print(f"   Name: {result.get('name', 'N/A')}")
                    print(f"   ECO: {result.get('eco', 'N/A')}")
                    print(f"   FEN: {result.get('fen', 'N/A')}")
                    print(f"   Moves: {result.get('san_moves', 'N/A')}")
                    print(f"   Match Type: {result.get('match_type', 'N/A')}")
                elif result.get("error"):
                    print(f"   Error: {result.get('error')}")
                elif result.get("message"):
                    print(f"   Message: {result.get('message')}")
                else:
                    print(f"   Data: {result}")
            else:
                print(f"   Raw: {result}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_improved_fen() 