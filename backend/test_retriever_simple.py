#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_retriever_agent():
    """Test the retriever agent instance"""
    try:
        from backend.etl.agents import retriever_agent_instance
        
        print("Retriever agent instance:", retriever_agent_instance)
        
        if retriever_agent_instance:
            test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
            print(f"Testing FEN: {test_fen}")
            
            # Test the retrieve_by_fen method
            result = retriever_agent_instance.retrieve_by_fen(test_fen, k=3)
            print(f"Result: {result}")
            
            # Test the retrieve method (used by orchestrator)
            metadata = {
                "query_type": "opening_lookup",
                "fen_for_analysis": test_fen,
                "k_results": 3
            }
            result2 = retriever_agent_instance.retrieve("Find games with this position", metadata)
            print(f"Retrieve method result: {result2}")
            
        else:
            print("❌ Retriever agent is None")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_retriever_agent() 