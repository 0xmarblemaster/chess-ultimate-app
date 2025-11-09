#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_mimic():
    """Test that mimics exactly what the API does."""
    
    print("Testing API Mimic...")
    print("=" * 50)
    
    try:
        # Import exactly as the API does
        from app import active_games, user_sessions
        from etl.agents import answer_agent_instance
        from etl.agents.orchestrator import run_pipeline
        from etl.agents import router_agent_instance, retriever_agent_instance
        
        # Use the same data as the API test
        query = "What is 2+2?"
        session_id = "test_api_mimic"
        received_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        query_type = None  # No override, let router decide
        
        print(f"Query: '{query}'")
        print(f"Session ID: {session_id}")
        print(f"Received FEN: {received_fen}")
        print(f"Query type override: {query_type}")
        print()
        
        # Mimic the API's FEN handling logic
        current_board_fen_for_rag = received_fen
        current_pgn_for_rag = None
        
        print(f"Current board FEN for RAG: {current_board_fen_for_rag}")
        print(f"Current PGN for RAG: {current_pgn_for_rag}")
        print()
        
        # Call the orchestrator exactly as the API does
        print("Calling orchestrator...")
        pipeline_state = run_pipeline(
            initial_query=query,
            router_agent_instance=router_agent_instance,
            retriever_agent_instance=retriever_agent_instance,
            answer_agent_instance=answer_agent_instance,
            current_board_fen=current_board_fen_for_rag,
            session_pgn=current_pgn_for_rag
        )
        
        print("Pipeline result:")
        print(f"  Query type: {pipeline_state.get('query_type')}")
        print(f"  Retrieved chunks: {len(pipeline_state.get('retrieved_chunks', []))}")
        print(f"  Final answer: {pipeline_state.get('final_answer', 'No answer')[:100]}")
        print(f"  Router metadata: {pipeline_state.get('router_metadata', {})}")
        
        # Check if the answer contains chess game information
        answer = pipeline_state.get('final_answer', '')
        chess_indicators = ["Retrieved Information:", "🎮 Games Found:", "Event:", "ECO:", "View Game"]
        has_chess_info = any(indicator in answer for indicator in chess_indicators)
        print(f"  Contains chess info: {has_chess_info}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_mimic() 