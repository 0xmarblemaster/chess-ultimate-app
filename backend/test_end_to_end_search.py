#!/usr/bin/env python3

from etl.agents.retriever_agent import RetrieverAgent
from etl.weaviate_loader import get_weaviate_client
from etl import config as etl_config

def test_end_to_end_search():
    print("Testing end-to-end Magnus Carlsen search through RetrieverAgent...")
    
    # Initialize the retriever agent
    client = get_weaviate_client()
    if not client:
        print("✗ Could not connect to Weaviate")
        return
    
    retriever = RetrieverAgent(
        client=client,
        opening_book_path=etl_config.OPENING_BOOK_PATH
    )
    
    # Test 1: Game search with any_player filter
    print("\n=== Test 1: Game search with any_player filter ===")
    metadata = {
        "query_type": "game_search",
        "game_filters": {"any_player": "Carlsen"},
        "k_results": 3
    }
    
    result = retriever.retrieve("Search for games by Carlsen", metadata)
    
    print(f"Query type: {result.get('query_type')}")
    print(f"Found {len(result.get('retrieved_chunks', []))} results")
    
    for i, game in enumerate(result.get('retrieved_chunks', [])[:3]):
        if 'error' in game or 'message' in game:
            print(f"{i+1}. {game}")
        else:
            white = game.get('white_player', 'Unknown')
            black = game.get('black_player', 'Unknown')
            event = game.get('event', 'Unknown')
            print(f"{i+1}. {white} vs {black} at {event}")
    
    # Test 2: Compare with old behavior (semantic search fallback)
    print("\n=== Test 2: Semantic search for comparison ===")
    metadata2 = {
        "query_type": "semantic_search",
        "k_results": 3
    }
    
    result2 = retriever.retrieve("Magnus Carlsen games", metadata2)
    
    print(f"Query type: {result2.get('query_type')}")
    print(f"Found {len(result2.get('retrieved_chunks', []))} results")
    
    for i, chunk in enumerate(result2.get('retrieved_chunks', [])[:3]):
        if isinstance(chunk, dict):
            if 'white_player' in chunk and 'black_player' in chunk:
                white = chunk.get('white_player', 'Unknown')
                black = chunk.get('black_player', 'Unknown')
                event = chunk.get('event', 'Unknown')
                print(f"{i+1}. {white} vs {black} at {event}")
            else:
                print(f"{i+1}. {chunk.get('type', 'Unknown type')}: {str(chunk)[:100]}...")
    
    # Test 3: Verify no false positives
    print("\n=== Test 3: Search for 'Marcus' (should not match Carlsen) ===")
    metadata3 = {
        "query_type": "game_search", 
        "game_filters": {"any_player": "Marcus"},
        "k_results": 3
    }
    
    result3 = retriever.retrieve("Search for games by Marcus", metadata3)
    
    print(f"Found {len(result3.get('retrieved_chunks', []))} results")
    
    for i, game in enumerate(result3.get('retrieved_chunks', [])[:3]):
        if 'error' in game or 'message' in game:
            print(f"{i+1}. {game}")
        else:
            white = game.get('white_player', 'Unknown')
            black = game.get('black_player', 'Unknown')
            event = game.get('event', 'Unknown')
            print(f"{i+1}. {white} vs {black} at {event}")
            # Check if this incorrectly matches Carlsen
            if 'carlsen' in white.lower() or 'carlsen' in black.lower():
                print(f"    ⚠️  WARNING: Found Carlsen in Marcus search!")

if __name__ == "__main__":
    test_end_to_end_search() 