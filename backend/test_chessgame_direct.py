#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.weaviate_loader import get_weaviate_client

def test_chessgame_search():
    client = get_weaviate_client()
    if not client:
        print("ERROR: Could not get Weaviate client")
        return
    
    try:
        # Check if ChessGame collection exists
        if not client.collections.exists("ChessGame"):
            print("ERROR: ChessGame collection does not exist")
            return
        
        print("SUCCESS: ChessGame collection exists")
        
        # Get the collection
        collection = client.collections.get("ChessGame")
        
        # Test search for "Masague"
        print("\nTesting search for 'Masague'...")
        results = collection.query.near_text(
            query="Masague",
            limit=3
        )
        
        if results.objects:
            print(f"Found {len(results.objects)} games:")
            for i, obj in enumerate(results.objects):
                props = obj.properties
                print(f"  Game {i+1}:")
                print(f"    White: {props.get('white_player', 'Unknown')} (ELO: {props.get('white_elo', 'N/A')})")
                print(f"    Black: {props.get('black_player', 'Unknown')} (ELO: {props.get('black_elo', 'N/A')})")
                print(f"    Event: {props.get('event', 'Unknown')}")
                print(f"    Result: {props.get('result', 'Unknown')}")
        else:
            print("No games found for 'Masague'")
        
        # Test search for "ELO"
        print("\nTesting search for 'ELO'...")
        results = collection.query.near_text(
            query="ELO rating",
            limit=3
        )
        
        if results.objects:
            print(f"Found {len(results.objects)} games:")
            for i, obj in enumerate(results.objects):
                props = obj.properties
                print(f"  Game {i+1}:")
                print(f"    White: {props.get('white_player', 'Unknown')} (ELO: {props.get('white_elo', 'N/A')})")
                print(f"    Black: {props.get('black_player', 'Unknown')} (ELO: {props.get('black_elo', 'N/A')})")
        else:
            print("No games found for 'ELO rating'")
            
    except Exception as e:
        print(f"ERROR during search: {e}")
    finally:
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    test_chessgame_search() 