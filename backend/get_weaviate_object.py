#!/usr/bin/env python3
import sys
from etl.weaviate_loader import get_weaviate_client
from etl import config

def get_object_by_uuid(uuid_str):
    """
    Get information about a Weaviate object by its UUID
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
        
        # Get the object by UUID
        try:
            print(f"Trying to fetch object with UUID: {uuid_str}")
            obj = collection.query.fetch_object_by_id(uuid_str)
            
            if obj is None:
                print(f"No object found with UUID: {uuid_str}")
                
                # Let's try to get a different object to confirm API works
                print("\nAttempting to fetch a random object as a test:")
                results = collection.query.fetch_objects(limit=1)
                if results and results.objects:
                    test_obj = results.objects[0]
                    print(f"Found test object with UUID: {test_obj.uuid}")
                    if hasattr(test_obj, 'properties'):
                        for key, value in test_obj.properties.items():
                            if isinstance(value, str) and len(value) > 100:
                                print(f"  {key}: {value[:100]}... (truncated)")
                            else:
                                print(f"  {key}: {value}")
                    else:
                        print("Test object has no properties attribute")
                else:
                    print("No objects found in collection")
                
                return
            
            print(f"Object found with UUID: {uuid_str}")
            print(f"Properties:")
            if hasattr(obj, 'properties'):
                for key, value in obj.properties.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"  {key}: {value[:100]}... (truncated)")
                    else:
                        print(f"  {key}: {value}")
            else:
                print("Object has no properties attribute")
                print(f"Object attributes: {dir(obj)}")
        except Exception as e:
            print(f"Error fetching object: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client connection
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get_weaviate_object.py <uuid>")
        sys.exit(1)
    
    uuid_str = sys.argv[1]
    get_object_by_uuid(uuid_str) 