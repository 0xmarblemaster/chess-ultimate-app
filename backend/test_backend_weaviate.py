#!/usr/bin/env python3

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_backend_weaviate_connection():
    """Test the backend's Weaviate connection using the same method as app.py"""
    print("Testing backend Weaviate connection...")
    
    try:
        # Import the same way as app.py does
        from backend.etl.agents import opening_agent
        
        print("✅ Successfully imported opening_agent")
        
        # Test the get_weaviate_client function
        client = opening_agent.get_weaviate_client()
        if client:
            print("✅ Successfully got Weaviate client")
            
            # Test if we can access the ChessGame collection
            if client.collections.exists("ChessGame"):
                print("✅ ChessGame collection exists")
                
                # Try to get one game
                collection = client.collections.get("ChessGame")
                games = collection.query.fetch_objects(limit=1)
                if games.objects:
                    print(f"✅ Successfully retrieved {len(games.objects)} game(s)")
                    print(f"   Sample game UUID: {games.objects[0].uuid}")
                else:
                    print("⚠️  No games found in collection")
            else:
                print("❌ ChessGame collection does not exist")
            
            # client.close() removed - Weaviate client manages connections automatically
        else:
            print("❌ Failed to get Weaviate client")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backend_weaviate_connection() 