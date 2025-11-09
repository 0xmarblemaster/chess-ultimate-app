#!/usr/bin/env python3

import sys
sys.path.insert(0, '/home/marblemaster/Desktop/Cursor/mvp1')
from backend.etl.agents.game_search_agent import find_games_by_criteria

# Test with starting position FEN
starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
print(f'Testing starting FEN: {starting_fen}')
results = find_games_by_criteria(fen_to_match=starting_fen, limit=3)
print(f'Found {len(results)} results')

if results:
    print(f'Results type: {type(results)}')
    for i, result in enumerate(results[:3]):
        print(f'Result {i+1}: {type(result)} - {result}')
        if isinstance(result, dict) and 'white_player' in result:
            print(f'  Game: {result.get("white_player")} vs {result.get("black_player")}')
else:
    print('No results returned')

# Also test a different approach - check if the issue is with the FEN format
print(f'\nTesting with a different FEN (after 1.e4):')
e4_fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'
results2 = find_games_by_criteria(fen_to_match=e4_fen, limit=3)
print(f'Found {len(results2)} results for e4 position') 