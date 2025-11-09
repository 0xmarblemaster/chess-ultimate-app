#!/usr/bin/env python3
from etl.weaviate_loader import get_weaviate_client
from etl import config

def list_diagram_objects():
    """
    List objects in Weaviate that have diagrams (tasks with images and FEN)
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
        
        # Let's get all objects and filter locally
        print("Fetching all objects...")
        try:
            results = collection.query.fetch_objects(limit=100, include_vector=False)
            
            if results and results.objects:
                total_objects = len(results.objects)
                print(f"\nFound {total_objects} total objects in the collection.")
                
                # Count how many have images, FEN, and type=task
                tasks_with_images = []
                objects_with_fen = []
                
                for obj in results.objects:
                    props = obj.properties
                    
                    # Tasks with images
                    if props.get("type") == "task" and props.get("image"):
                        tasks_with_images.append(obj)
                    
                    # Objects with FEN
                    if props.get("fen"):
                        objects_with_fen.append(obj)
                
                # Report counts
                print(f"Tasks with images: {len(tasks_with_images)}")
                print(f"Objects with FEN: {len(objects_with_fen)}")
                
                # Display some sample tasks with images
                if tasks_with_images:
                    print(f"\nSample tasks with images (showing up to 5):")
                    for i, obj in enumerate(tasks_with_images[:5]):
                        print(f"\n--- Task with Image {i+1} ---")
                        print(f"UUID: {obj.uuid}")
                        print(f"Properties:")
                        for key, value in obj.properties.items():
                            if key == "text" and value and len(value) > 100:
                                print(f"  {key}: {value[:100]}... (truncated)")
                            else:
                                print(f"  {key}: {value}")
                
                # Display some sample objects with FEN
                if objects_with_fen:
                    print(f"\nSample objects with FEN (showing up to 5):")
                    for i, obj in enumerate(objects_with_fen[:5]):
                        print(f"\n--- Object with FEN {i+1} ---")
                        print(f"UUID: {obj.uuid}")
                        print(f"Properties:")
                        for key, value in obj.properties.items():
                            if key == "text" and value and len(value) > 100:
                                print(f"  {key}: {value[:100]}... (truncated)")
                            else:
                                print(f"  {key}: {value}")
            else:
                print("No objects found in the collection.")
                
        except Exception as e:
            print(f"Error fetching objects: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client connection
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    list_diagram_objects() 