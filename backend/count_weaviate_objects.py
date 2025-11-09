#!/usr/bin/env python3
from etl.weaviate_loader import get_weaviate_client
from etl import config

def count_weaviate_objects():
    """
    Count objects in Weaviate with different properties
    """
    # Initialize the Weaviate client
    client = get_weaviate_client()
    if not client:
        print("Error: Could not connect to Weaviate")
        return
    
    try:
        # Get the collection
        collection_name = config.WEAVIATE_CLASS_NAME
        print(f"Analyzing collection: {collection_name}")
        collection = client.collections.get(collection_name)
        
        # Get total count of objects
        try:
            total_count = collection.aggregate.over_all(total_count=True).total_count
            print(f"Total objects in collection: {total_count}")
            
            # We need to fetch objects in batches to count properties
            offset = 0
            limit = 100
            processed = 0
            
            # Initialize counters
            tasks_count = 0
            images_count = 0
            fen_count = 0
            tasks_with_images = 0
            tasks_with_fen = 0
            tasks_with_both = 0
            
            print("Scanning objects...")
            
            while processed < total_count:
                results = collection.query.fetch_objects(
                    offset=offset,
                    limit=limit,
                    include_vector=False
                )
                
                if not results or not results.objects:
                    break
                
                batch_size = len(results.objects)
                processed += batch_size
                print(f"Processing batch: {processed}/{total_count} objects")
                
                for obj in results.objects:
                    props = obj.properties
                    
                    # Count objects by type and properties
                    is_task = props.get("type") == "task" or props.get("type") == "general_task"
                    has_image = bool(props.get("image"))
                    has_fen = bool(props.get("fen"))
                    
                    if is_task:
                        tasks_count += 1
                    
                    if has_image:
                        images_count += 1
                    
                    if has_fen:
                        fen_count += 1
                    
                    if is_task and has_image:
                        tasks_with_images += 1
                    
                    if is_task and has_fen:
                        tasks_with_fen += 1
                    
                    if is_task and has_image and has_fen:
                        tasks_with_both += 1
                
                offset += limit
                
                if batch_size < limit:
                    break
            
            # Print summary
            print("\n===== WEAVIATE OBJECTS SUMMARY =====")
            print(f"Total objects: {processed}")
            print(f"Task objects: {tasks_count}")
            print(f"Objects with images: {images_count}")
            print(f"Objects with FEN: {fen_count}")
            print(f"Tasks with images: {tasks_with_images}")
            print(f"Tasks with FEN: {tasks_with_fen}")
            print(f"Tasks with both image and FEN: {tasks_with_both}")
            
            # Calculate percentages for expected extraction
            if tasks_count > 0:
                print("\n===== EXTRACTION EFFECTIVENESS =====")
                print(f"Tasks with images: {tasks_with_images}/{tasks_count} ({tasks_with_images/tasks_count*100:.1f}%)")
                print(f"Tasks with FEN: {tasks_with_fen}/{tasks_count} ({tasks_with_fen/tasks_count*100:.1f}%)")
                print(f"Tasks with both: {tasks_with_both}/{tasks_count} ({tasks_with_both/tasks_count*100:.1f}%)")
                
        except Exception as e:
            print(f"Error fetching objects: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client connection
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    count_weaviate_objects() 