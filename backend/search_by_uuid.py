#!/usr/bin/env python3
import sys
from etl.weaviate_loader import get_weaviate_client
from etl import config

def search_by_uuid(uuid_str):
    """
    Search for an object with the given UUID in the Weaviate database
    and display all objects if not found
    """
    # Initialize the Weaviate client
    client = get_weaviate_client()
    if not client:
        print("Error: Could not connect to Weaviate")
        return
    
    try:
        # Get the collection
        collection_name = config.WEAVIATE_CLASS_NAME
        print(f"Querying collection: {collection_name}")
        collection = client.collections.get(collection_name)
        
        # Get all UUIDs in the collection
        print(f"Fetching all objects to look for UUID: {uuid_str}")
        
        # Paginate through all results in batches of 100
        offset = 0
        limit = 100
        total_objects = 0
        found = False
        all_uuids = []
        
        while True:
            results = collection.query.fetch_objects(
                offset=offset,
                limit=limit,
                include_vector=False
            )
            
            if not results or not results.objects or len(results.objects) == 0:
                break
                
            batch_size = len(results.objects)
            total_objects += batch_size
            print(f"Processing batch of {batch_size} objects (total so far: {total_objects})")
            
            for obj in results.objects:
                # Convert UUID object to string for comparison
                obj_uuid_str = str(obj.uuid)
                all_uuids.append(obj_uuid_str)
                
                if obj_uuid_str == uuid_str:
                    found = True
                    print(f"\nFOUND OBJECT WITH UUID: {uuid_str}")
                    print(f"Properties:")
                    for key, value in obj.properties.items():
                        if key == "text" and value and len(value) > 100:
                            print(f"  {key}: {value[:100]}... (truncated)")
                        else:
                            print(f"  {key}: {value}")
            
            offset += limit
            if batch_size < limit:
                break
        
        if not found:
            print(f"\nNo object found with UUID: {uuid_str}")
            print(f"Total objects searched: {total_objects}")
            
            # Suggest possible close matches (for typos)
            print("\nChecking for possible UUID typos...")
            similar_uuids = []
            for existing_uuid in all_uuids:
                # Simple matching algorithm - check if the first several characters match
                if existing_uuid.startswith(uuid_str[:8]):
                    similar_uuids.append(existing_uuid)
            
            if similar_uuids:
                print(f"Found {len(similar_uuids)} similar UUIDs that might be what you're looking for:")
                for i, similar_uuid in enumerate(similar_uuids[:5]):
                    print(f"  {i+1}. {similar_uuid}")
                if len(similar_uuids) > 5:
                    print(f"  ... and {len(similar_uuids) - 5} more")
            else:
                print("No similar UUIDs found")
                
            # Show some sample UUIDs from the collection
            print("\nSample UUIDs from the collection:")
            for i, sample_uuid in enumerate(all_uuids[:5]):
                print(f"  {i+1}. {sample_uuid}")
            if len(all_uuids) > 5:
                print(f"  ... and {len(all_uuids) - 5} more")
                
        print(f"\nTotal objects in collection: {total_objects}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client connection
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python search_by_uuid.py <uuid>")
        sys.exit(1)
    
    uuid_str = sys.argv[1]
    search_by_uuid(uuid_str) 