#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_orchestrator_debug():
    print("Testing Orchestrator Debug...")
    print("=" * 50)
    
    try:
        from etl.agents import router_agent_instance, retriever_agent_instance, answer_agent_instance
        from etl.agents.orchestrator import run_pipeline
        
        query = "What is 2+2?"
        current_board_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        print(f"Testing query: '{query}'")
        print(f"Current board FEN: {current_board_fen}")
        print()
        
        # Test router directly first
        print("1. Testing Router Agent directly:")
        state = {
            'user_query': query,
            'current_board_fen': current_board_fen,
            'router_metadata': {}
        }
        
        router_result = router_agent_instance.classify_query(state)
        print(f"   Router classification: {router_result.get('query_type')}")
        print(f"   Router metadata: {router_result.get('router_metadata')}")
        print()
        
        # Test orchestrator
        print("2. Testing Orchestrator:")
        pipeline_result = run_pipeline(
            initial_query=query,
            router_agent_instance=router_agent_instance,
            retriever_agent_instance=retriever_agent_instance,
            answer_agent_instance=answer_agent_instance,
            current_board_fen=current_board_fen,
            session_pgn=None,
            override_query_type=None
        )
        
        print(f"   Pipeline query type: {pipeline_result.get('query_type')}")
        print(f"   Pipeline sources: {len(pipeline_result.get('retrieved_chunks', []))}")
        print(f"   Pipeline answer: {pipeline_result.get('final_answer', 'No answer')[:100]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_orchestrator_debug() 