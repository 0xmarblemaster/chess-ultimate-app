#!/usr/bin/env python3

from etl.agents.game_search_agent import find_games_by_criteria

def test_carlsen_search():
    print("Testing Magnus Carlsen search...")
    
    # Test 1: Search for any player named Carlsen
    print("\n=== Test 1: any_player = 'Carlsen' ===")
    results = find_games_by_criteria(filters={'any_player': 'Carlsen'}, limit=5)
    print(f"Found {len(results)} results")
    
    for i, game in enumerate(results[:5]):
        if 'error' in game or 'message' in game:
            print(f"{i+1}. {game}")
        else:
            white = game.get('white_player', 'Unknown')
            black = game.get('black_player', 'Unknown')
            event = game.get('event', 'Unknown')
            print(f"{i+1}. {white} vs {black} at {event}")
    
    # Test 2: Search for Magnus specifically
    print("\n=== Test 2: any_player = 'Magnus' ===")
    results2 = find_games_by_criteria(filters={'any_player': 'Magnus'}, limit=5)
    print(f"Found {len(results2)} results")
    
    for i, game in enumerate(results2[:5]):
        if 'error' in game or 'message' in game:
            print(f"{i+1}. {game}")
        else:
            white = game.get('white_player', 'Unknown')
            black = game.get('black_player', 'Unknown')
            event = game.get('event', 'Unknown')
            print(f"{i+1}. {white} vs {black} at {event}")
    
    # Test 3: Search for a player that should NOT match (to verify precision)
    print("\n=== Test 3: any_player = 'Marcus' (should not match Carlsen) ===")
    results3 = find_games_by_criteria(filters={'any_player': 'Marcus'}, limit=5)
    print(f"Found {len(results3)} results")
    
    for i, game in enumerate(results3[:5]):
        if 'error' in game or 'message' in game:
            print(f"{i+1}. {game}")
        else:
            white = game.get('white_player', 'Unknown')
            black = game.get('black_player', 'Unknown')
            event = game.get('event', 'Unknown')
            print(f"{i+1}. {white} vs {black} at {event}")

if __name__ == "__main__":
    test_carlsen_search() 