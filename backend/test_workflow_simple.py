#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_workflow_step_by_step():
    print("Testing RAG workflow step by step...")
    print("=" * 60)
    
    # Step 1: Test Weaviate connection
    print("Step 1: Testing Weaviate connection...")
    try:
        from etl.weaviate_loader import get_weaviate_client
        client = get_weaviate_client()
        if client:
            print("✓ Weaviate connection successful")
            # client.close() removed - Weaviate client manages connections automatically
        else:
            print("✗ Weaviate connection failed")
            return
    except Exception as e:
        print(f"✗ Weaviate connection error: {e}")
        return
    
    # Step 2: Test router agent
    print("\nStep 2: Testing router agent...")
    try:
        from etl.agents import router_agent_instance
        if router_agent_instance:
            print("✓ Router agent initialized")
            
            # Test classification
            test_state = {
                "user_query": "search for games with FEN rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "current_board_fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "router_metadata": {}
            }
            result = router_agent_instance.classify_query(test_state)
            print(f"✓ Query classified as: {result.get('query_type')}")
        else:
            print("✗ Router agent not initialized")
    except Exception as e:
        print(f"✗ Router agent error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Test retriever agent
    print("\nStep 3: Testing retriever agent...")
    try:
        from etl.agents import retriever_agent_instance
        if retriever_agent_instance:
            print("✓ Retriever agent initialized")
            
            # Test FEN retrieval
            test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
            result = retriever_agent_instance.retrieve_by_fen(test_fen, k=2)
            chunks = result.get("retrieved_chunks", [])
            print(f"✓ Retrieved {len(chunks)} chunks for FEN")
            if chunks:
                print(f"  First chunk type: {type(chunks[0])}")
        else:
            print("✗ Retriever agent not initialized")
    except Exception as e:
        print(f"✗ Retriever agent error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Test answer agent
    print("\nStep 4: Testing answer agent...")
    try:
        from etl.agents import answer_agent_instance
        if answer_agent_instance:
            print("✓ Answer agent initialized")
            
            # Test simple answer generation
            test_answer = answer_agent_instance.generate_answer(
                query="Test query",
                retrieved_documents=[{"type": "test", "content": "test content"}],
                query_type="test"
            )
            print(f"✓ Generated answer (length: {len(test_answer) if test_answer else 0})")
        else:
            print("✗ Answer agent not initialized")
    except Exception as e:
        print(f"✗ Answer agent error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nWorkflow test completed!")

if __name__ == "__main__":
    test_workflow_step_by_step() 