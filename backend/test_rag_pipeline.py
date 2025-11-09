#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.agents.orchestrator import run_pipeline
from etl.agents import router_agent_instance, retriever_agent_instance, answer_agent_instance

def test_rag_pipeline():
    # Test a simple FEN search query
    query = 'search for games with FEN rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'
    current_fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'
    
    print(f"Testing RAG pipeline with query: {query}")
    print("=" * 80)
    
    try:
        result = run_pipeline(
            initial_query=query,
            router_agent_instance=router_agent_instance,
            retriever_agent_instance=retriever_agent_instance,
            answer_agent_instance=answer_agent_instance,
            current_board_fen=current_fen
        )
        
        print('Pipeline Result:')
        print(f'Query Type: {result.get("query_type")}')
        print(f'Retrieved Chunks: {len(result.get("retrieved_chunks", []))}')
        print(f'Final Answer: {result.get("final_answer", "No answer")}')
        print(f'Error Message: {result.get("error_message", "None")}')
        
        # Print first few retrieved chunks for debugging
        chunks = result.get("retrieved_chunks", [])
        if chunks:
            print(f"\nFirst 2 retrieved chunks:")
            for i, chunk in enumerate(chunks[:2]):
                print(f"  Chunk {i+1}: {chunk}")
        
    except Exception as e:
        print(f"ERROR during RAG pipeline test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rag_pipeline() 