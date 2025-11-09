#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

from backend.etl.weaviate_loader import get_weaviate_client
from backend.etl.agents.retriever_agent import normalize_fen_for_matching
import json

def test_specific_fen():
    client = get_weaviate_client()
    if not client:
        print("Failed to connect to Weaviate")
        return
    
    collection = client.collections.get('ChessGame')
    
    # Test our specific FEN
    test_fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'
    print(f'Searching for FEN: {test_fen}')
    
    # Search for exact FEN match
    response = collection.query.fetch_objects(
        where={
            'operator': 'ContainsAny',
            'path': ['all_ply_fens'],
            'valueTextArray': [test_fen]
        },
        limit=5
    )
    
    print(f'Found {len(response.objects)} games with exact FEN match')
    
    # Also try a broader search for games that start with 1.e4
    starting_fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'
    print(f'\nSearching for starting FEN: {starting_fen}')
    
    response2 = collection.query.fetch_objects(
        where={
            'operator': 'ContainsAny', 
            'path': ['all_ply_fens'],
            'valueTextArray': [starting_fen]
        },
        limit=5
    )
    
    print(f'Found {len(response2.objects)} games with starting FEN match')
    
    # Try semantic search for e4 games
    print(f'\nTrying semantic search for e4 games...')
    response3 = collection.query.near_text(
        query='e4 opening games',
        limit=5
    )
    
    print(f'Found {len(response3.objects)} games from semantic search')
    for i, obj in enumerate(response3.objects[:3]):
        print(f'  Game {i+1}: {obj.properties.get("white_player", "Unknown")} vs {obj.properties.get("black_player", "Unknown")}')
        print(f'    Opening: {obj.properties.get("opening", "Unknown")}')
    
    # Try to find any games that contain "e4" in their moves
    print(f'\nSearching for games with e4 in moves...')
    response4 = collection.query.fetch_objects(
        where={
            'operator': 'ContainsAny',
            'path': ['moves_san'],
            'valueTextArray': ['e4']
        },
        limit=5
    )
    
    print(f'Found {len(response4.objects)} games with e4 in moves')
    for i, obj in enumerate(response4.objects[:3]):
        print(f'  Game {i+1}: {obj.properties.get("white_player", "Unknown")} vs {obj.properties.get("black_player", "Unknown")}')
        print(f'    Moves: {obj.properties.get("moves_san", "Unknown")[:50]}...')
    
    # client.close() removed - Weaviate client manages connections automatically

if __name__ == '__main__':
    test_specific_fen() 