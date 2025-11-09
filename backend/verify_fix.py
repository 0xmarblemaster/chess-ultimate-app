#!/usr/bin/env python3

from etl.agents.game_search_agent import find_games_by_criteria

def verify_carlsen_fix():
    print("🔍 Verifying Magnus Carlsen search fix...")
    
    # Test the any_player filter with "Carlsen"
    results = find_games_by_criteria(filters={'any_player': 'Carlsen'}, limit=10)
    
    print(f"Found {len(results)} games")
    
    carlsen_games = 0
    other_games = 0
    
    for i, game in enumerate(results):
        if 'error' in game or 'message' in game:
            print(f"❌ Error: {game}")
            continue
            
        white = game.get('white_player', 'Unknown')
        black = game.get('black_player', 'Unknown')
        event = game.get('event', 'Unknown')
        
        # Check if this is actually a Magnus Carlsen game
        is_carlsen_game = ('Carlsen,M' in white or 'Carlsen,M' in black or 
                          'Magnus Carlsen' in white or 'Magnus Carlsen' in black)
        
        if is_carlsen_game:
            carlsen_games += 1
            print(f"✅ {white} vs {black} ({event})")
        else:
            other_games += 1
            print(f"❌ {white} vs {black} ({event}) - NOT Magnus Carlsen!")
    
    print(f"\n📊 Results:")
    print(f"   Magnus Carlsen games: {carlsen_games}")
    print(f"   Other games: {other_games}")
    
    if other_games == 0:
        print("🎉 SUCCESS: Only Magnus Carlsen games returned!")
    else:
        print("⚠️  ISSUE: Non-Carlsen games still being returned")
    
    return other_games == 0

if __name__ == "__main__":
    verify_carlsen_fix() 