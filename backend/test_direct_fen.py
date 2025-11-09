#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_direct_fen():
    """Test retrieve_by_fen directly"""
    try:
        from backend.etl.agents.retriever_agent import retrieve_by_fen
        
        test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        print(f"Testing retrieve_by_fen directly...")
        print(f"FEN: {test_fen}")
        
        results = retrieve_by_fen(test_fen, limit=3)
        print(f"Results: {len(results)} items")
        
        for i, result in enumerate(results):
            print(f"{i+1}. {result}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_fen() 

# Test FEN search
test_fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'
print(f'Testing FEN search for: {test_fen}')
results = find_games_by_criteria(fen_to_match=test_fen, limit=3)
print(f'Found {len(results)} results')
for i, result in enumerate(results[:2]):
    print(f'Result {i+1}: {result}') 