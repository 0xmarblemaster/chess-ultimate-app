#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.weaviate_loader import get_weaviate_client

def check_collections():
    print("Checking Weaviate collections...")
    
    client = get_weaviate_client()
    if not client:
        print("✗ Could not connect to Weaviate")
        return
    
    try:
        # Get all collections
        collections = client.collections.list_all()
        print(f"Found {len(collections)} collections:")
        
        for collection_name in collections:
            print(f"  - {collection_name}")
            
            # Get collection details
            try:
                collection = client.collections.get(collection_name)
                # Try to get a few objects to see the structure
                result = collection.query.fetch_objects(limit=1)
                if result.objects:
                    obj = result.objects[0]
                    print(f"    Sample properties: {list(obj.properties.keys())}")
                else:
                    print(f"    No objects found in collection")
            except Exception as e:
                print(f"    Error accessing collection: {e}")
        
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"✗ Error checking collections: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_collections() 