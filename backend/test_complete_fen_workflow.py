#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_complete_fen_workflow():
    print("Testing complete FEN workflow...")
    print("=" * 60)
    
    # Test query: search for games with a specific FEN
    user_query = "search for games with FEN rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    current_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    
    print(f"User query: {user_query}")
    print(f"Current FEN: {current_fen}")
    print()
    
    # Step 1: Router Agent Classification
    print("Step 1: Router Agent Classification")
    try:
        from etl.agents import router_agent_instance
        
        test_state = {
            "user_query": user_query,
            "current_board_fen": current_fen,
            "router_metadata": {}
        }
        
        router_result = router_agent_instance.classify_query(test_state)
        print(f"✓ Query classified as: {router_result.get('query_type')}")
        print(f"  Metadata: {router_result.get('router_metadata', {})}")
        
        query_type = router_result.get('query_type')
        router_metadata = router_result.get('router_metadata', {})
        
    except Exception as e:
        print(f"✗ Router agent error: {e}")
        return
    
    print()
    
    # Step 2: Retriever Agent
    print("Step 2: Retriever Agent")
    try:
        from etl.agents import retriever_agent_instance
        
        # Prepare metadata for retriever
        retriever_metadata = {
            "query_type": query_type,
            "fen_for_analysis": current_fen,
            "k_results": 3,
            "target_class_name": "ChessGame"
        }
        retriever_metadata.update(router_metadata)
        
        retriever_result = retriever_agent_instance.retrieve(
            query=user_query,
            metadata=retriever_metadata
        )
        
        retrieved_chunks = retriever_result.get("retrieved_chunks", [])
        stockfish_analysis = retriever_result.get("stockfish_analysis", [])
        
        print(f"✓ Retrieved {len(retrieved_chunks)} chunks")
        print(f"✓ Stockfish analysis: {len(stockfish_analysis)} lines")
        
        # Show sample results
        if retrieved_chunks:
            for i, chunk in enumerate(retrieved_chunks[:2]):  # Show first 2
                if chunk.get("type") == "chess_game_search_result":
                    print(f"  Game {i+1}: {chunk.get('white_player')} vs {chunk.get('black_player')}")
                    print(f"    Event: {chunk.get('event')}")
                    print(f"    UUID: {chunk.get('uuid')}")
                else:
                    print(f"  Chunk {i+1}: {chunk.get('type', 'unknown')}")
        
    except Exception as e:
        print(f"✗ Retriever agent error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # Step 3: Answer Agent
    print("Step 3: Answer Agent")
    try:
        from etl.agents import answer_agent_instance
        
        answer = answer_agent_instance.generate_answer(
            query=user_query,
            retrieved_documents=retrieved_chunks,
            query_type=query_type,
            current_fen=current_fen
        )
        
        print(f"✓ Generated answer (length: {len(answer)})")
        print("Answer preview:")
        print("-" * 40)
        print(answer[:500] + "..." if len(answer) > 500 else answer)
        print("-" * 40)
        
    except Exception as e:
        print(f"✗ Answer agent error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("✓ Complete FEN workflow test successful!")

if __name__ == "__main__":
    test_complete_fen_workflow() 