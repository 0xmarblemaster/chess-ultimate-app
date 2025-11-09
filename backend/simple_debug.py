#!/usr/bin/env python3

import sys
sys.path.insert(0, '/home/marblemaster/Desktop/Cursor/mvp1')

def test_fen_hypothesis():
    """Test the hypothesis about FEN storage in database"""
    print("🔍 TESTING FEN HYPOTHESIS")
    print("=" * 50)
    
    try:
        from backend.etl.agents.game_search_agent import find_games_by_criteria
        
        # Test 1: Standard starting position (should exist in starting_fen)
        starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        print(f"🎯 TEST 1: Standard starting position")
        print(f"   FEN: {starting_fen}")
        
        games = find_games_by_criteria(
            filters={},
            fen_to_match=starting_fen,
            limit=3
        )
        
        print(f"   ✅ Found {len(games)} results")
        if games and len(games) > 0 and isinstance(games[0], dict):
            if 'white_player' in games[0] and games[0]['white_player'] != 'N/A':
                print(f"   🎮 Sample game: {games[0]['white_player']} vs {games[0]['black_player']}")
                print("   ✅ SUCCESS: Starting position found games!")
            elif 'message' in games[0]:
                print(f"   📝 Message: {games[0]['message']}")
            elif 'error' in games[0]:
                print(f"   ❌ Error: {games[0]['error']}")
        
        # Test 2: User's problematic FEN (should NOT exist)
        problem_fen = "r1bqkbnr/pp1ppppp/2n5/2p5/4P3/2P2N2/PP1P1PPP/RNBQKB1R b KQkq - 0 3"
        print(f"\n🎯 TEST 2: User's problematic FEN (move 3 position)")
        print(f"   FEN: {problem_fen}")
        
        games2 = find_games_by_criteria(
            filters={},
            fen_to_match=problem_fen,
            limit=3
        )
        
        print(f"   ✅ Found {len(games2)} results")
        if games2 and len(games2) > 0 and isinstance(games2[0], dict):
            if 'white_player' in games2[0] and games2[0]['white_player'] != 'N/A':
                print(f"   🎮 Sample game: {games2[0]['white_player']} vs {games2[0]['black_player']}")
                print("   😲 UNEXPECTED: Mid-game position found games!")
            elif 'message' in games2[0]:
                print(f"   📝 Message: {games2[0]['message']}")
                print("   ✅ EXPECTED: Mid-game position not found (as hypothesis predicts)")
            elif 'error' in games2[0]:
                print(f"   ❌ Error: {games2[0]['error']}")
        
        # Test 3: Check what FEN types exist in database
        print(f"\n🎯 TEST 3: Examine database FEN structure")
        from backend.etl.weaviate_loader import get_weaviate_client
        
        client = get_weaviate_client()
        if client:
            games_collection = client.collections.get("ChessGame")
            
            # Sample a few games to see their FEN patterns
            response = games_collection.query.fetch_objects(limit=3)
            
            print("   📋 Sample FEN patterns in database:")
            for i, game in enumerate(response.objects):
                props = game.properties
                starting = props.get('starting_fen', 'N/A')[:50] + "..."
                ending = props.get('ending_fen', 'N/A')[:50] + "..."
                
                print(f"   Game {i+1}:")
                print(f"     Starting: {starting}")
                print(f"     Ending:   {ending}")
                
            # client.close() removed - Weaviate client manages connections automatically
        
        # Summary
        print(f"\n📊 HYPOTHESIS ANALYSIS:")
        print(f"   1. Database stores only starting_fen and ending_fen")
        print(f"   2. No intermediate positions during games are stored")
        print(f"   3. User's FEN is a mid-game position (move 3)")
        print(f"   4. Therefore, search fails for any position except start/end")
        print(f"   5. This explains why RAG can't find games for specific positions")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fen_hypothesis() 