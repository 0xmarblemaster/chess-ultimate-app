#!/usr/bin/env python3

from etl.weaviate_loader import get_weaviate_client
from etl import config as etl_config

def get_database_stats():
    """Get comprehensive statistics about the Weaviate database."""
    client = get_weaviate_client()
    if not client:
        print('Could not connect to Weaviate')
        return
    
    try:
        print("=== Weaviate Database Statistics ===\n")
        
        # Check ChessGame collection
        try:
            games_collection = client.collections.get('ChessGame')
            response = games_collection.aggregate.over_all(total_count=True)
            print(f"📋 ChessGame collection: {response.total_count:,} games")
        except Exception as e:
            print(f"❌ Error getting ChessGame count: {e}")
        
        # Check ChessLessonChunk collection
        try:
            lesson_collection = client.collections.get(etl_config.WEAVIATE_CLASS_NAME)
            response = lesson_collection.aggregate.over_all(total_count=True)
            print(f"📚 {etl_config.WEAVIATE_CLASS_NAME} collection: {response.total_count:,} chunks")
        except Exception as e:
            print(f"❌ Error getting {etl_config.WEAVIATE_CLASS_NAME} count: {e}")
        
        # Check ChessOpening collection
        try:
            opening_collection = client.collections.get('ChessOpening')
            response = opening_collection.aggregate.over_all(total_count=True)
            print(f"🏁 ChessOpening collection: {response.total_count:,} openings")
        except Exception as e:
            print(f"❌ Error getting ChessOpening count: {e}")
        
        # List all collections
        print(f"\n=== Available Collections ===")
        try:
            collections = client.collections.list_all()
            for collection_name in collections:
                print(f"  • {collection_name}")
        except Exception as e:
            print(f"❌ Error listing collections: {e}")
            
        # Sample a few games to show what data is available
        print(f"\n=== Sample Game Data ===")
        try:
            games_collection = client.collections.get('ChessGame')
            response = games_collection.query.fetch_objects(limit=3)
            if response.objects:
                for i, game in enumerate(response.objects, 1):
                    props = game.properties
                    print(f"Game {i}:")
                    print(f"  • Players: {props.get('white_player', 'Unknown')} vs {props.get('black_player', 'Unknown')}")
                    print(f"  • Event: {props.get('event', 'Unknown')}")
                    print(f"  • Date: {props.get('date_utc', 'Unknown')}")
                    print(f"  • Result: {props.get('result', 'Unknown')}")
                    print(f"  • ECO: {props.get('eco', 'Unknown')}")
                    print(f"  • UUID: {str(game.uuid)}")
                    print()
        except Exception as e:
            print(f"❌ Error getting sample games: {e}")
            
    except Exception as e:
        print(f'❌ General error: {e}')
    finally:
        if client:
            # client.close() removed - Weaviate client manages connections automatically

if __name__ == '__main__':
    get_database_stats() 