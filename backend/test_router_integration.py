#!/usr/bin/env python3

from etl.agents.router_agent import RouterAgent
from etl.agents.retriever_agent import RetrieverAgent
from etl.weaviate_loader import get_weaviate_client
from etl import config as etl_config

def test_router_integration():
    print("🔍 Testing complete pipeline: Router → Retriever → Game Search")
    
    # Initialize components
    client = get_weaviate_client()
    if not client:
        print("❌ Could not connect to Weaviate")
        return
    
    router = RouterAgent()
    retriever = RetrieverAgent(
        client=client,
        opening_book_path=etl_config.OPENING_BOOK_PATH
    )
    
    # Test query that should trigger game search with player filter
    test_query = "Show me games by Magnus Carlsen"
    
    print(f"🎯 Test query: '{test_query}'")
    
    # Step 1: Router extracts metadata
    print("\n📋 Step 1: Router extracting metadata...")
    metadata = router.route(test_query)
    print(f"   Query type: {metadata.get('query_type')}")
    print(f"   Game filters: {metadata.get('game_filters', {})}")
    
    # Step 2: Retriever processes the query
    print("\n🔍 Step 2: Retriever processing query...")
    results = retriever.retrieve(test_query, metadata)
    
    # Step 3: Analyze results
    print(f"\n📊 Step 3: Analyzing results...")
    games = results.get('games', [])
    print(f"   Found {len(games)} games")
    
    carlsen_count = 0
    other_count = 0
    
    for i, game in enumerate(games[:5]):  # Check first 5 games
        if isinstance(game, dict):
            white = game.get('white_player', 'Unknown')
            black = game.get('black_player', 'Unknown')
            
            is_carlsen = ('Carlsen,M' in white or 'Carlsen,M' in black or 
                         'Magnus Carlsen' in white or 'Magnus Carlsen' in black)
            
            if is_carlsen:
                carlsen_count += 1
                print(f"   ✅ {white} vs {black}")
            else:
                other_count += 1
                print(f"   ❌ {white} vs {black} - NOT Magnus Carlsen!")
    
    print(f"\n🎯 Final Results:")
    print(f"   Magnus Carlsen games: {carlsen_count}")
    print(f"   Other games: {other_count}")
    
    if other_count == 0 and carlsen_count > 0:
        print("🎉 SUCCESS: Complete pipeline working correctly!")
    else:
        print("⚠️  ISSUE: Pipeline not filtering correctly")

if __name__ == "__main__":
    test_router_integration() 