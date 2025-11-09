#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.agents.retriever_agent import RetrieverAgent
from etl.utils.weaviate_utils import get_weaviate_client
from etl import config as etl_config_module

def test_fen_search_format():
    """Test that FEN search returns the correct format for chess games"""
    
    print("🔍 Testing FEN search format fix...")
    
    # Get Weaviate client
    client = get_weaviate_client()
    if not client:
        print("❌ Could not connect to Weaviate")
        return False
    
    # Create retriever agent
    retriever = RetrieverAgent(
        client=client,
        opening_book_path=etl_config_module.OPENING_BOOK_PATH
    )
    
    # Test FEN that should exist in the database
    test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    
    print(f"🔍 Searching for FEN: {test_fen}")
    
    # Test the retrieve method with game_search
    metadata = {
        "query_type": "game_search",
        "fen_for_analysis": test_fen,
        "k_results": 3,
        "target_class_name": "ChessGame"
    }
    
    result = retriever.retrieve("Find games with this position", metadata)
    
    print(f"📊 Result type: {type(result)}")
    print(f"📊 Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    
    retrieved_chunks = result.get("retrieved_chunks", [])
    print(f"📊 Retrieved {len(retrieved_chunks)} chunks")
    
    if retrieved_chunks:
        for i, chunk in enumerate(retrieved_chunks):
            print(f"\n--- Chunk {i+1} ---")
            print(f"Type: {chunk.get('type', 'No type')}")
            print(f"Source: {chunk.get('source', 'No source')}")
            
            if chunk.get('type') == 'chess_game_search_result':
                print("✅ Correct type: chess_game_search_result")
                print(f"Game ID: {chunk.get('game_id', 'Missing')}")
                print(f"UUID: {chunk.get('uuid', 'Missing')}")
                print(f"Players: {chunk.get('white_player', '?')} vs {chunk.get('black_player', '?')}")
                print(f"Event: {chunk.get('event', 'Missing')}")
                print(f"Date: {chunk.get('date_utc', 'Missing')}")
                print(f"Result: {chunk.get('result', 'Missing')}")
                print(f"ECO: {chunk.get('eco', 'Missing')}")
                print(f"Opening: {chunk.get('opening_name', 'Missing')}")
                print(f"Final FEN: {chunk.get('final_fen', 'Missing')}")
                print(f"Match type: {chunk.get('fen_match_type', 'Missing')}")
                return True
            else:
                print(f"❌ Wrong type: {chunk.get('type', 'No type')}")
                print(f"Full chunk: {chunk}")
    else:
        print("❌ No chunks retrieved")
    
    return False

if __name__ == "__main__":
    success = test_fen_search_format()
    if success:
        print("\n✅ FEN search format fix successful!")
    else:
        print("\n❌ FEN search format fix failed!") 