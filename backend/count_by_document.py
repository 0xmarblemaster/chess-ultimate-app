#!/usr/bin/env python3
from etl.weaviate_loader import get_weaviate_client
from etl import config
from collections import defaultdict

def count_by_document():
    """
    Count objects in Weaviate grouped by document/book title
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
            
            # Initialize counters for each document
            document_stats = defaultdict(lambda: {
                'total': 0,
                'tasks': 0,
                'with_images': 0,
                'with_fen': 0,
                'tasks_with_images': 0,
                'tasks_with_fen': 0,
                'tasks_with_both': 0
            })
            
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
                    
                    # Get document title
                    book_title = props.get("book_title", "Unknown")
                    
                    # Count various properties
                    is_task = props.get("type") == "task" or props.get("type") == "general_task"
                    has_image = bool(props.get("image"))
                    has_fen = bool(props.get("fen"))
                    
                    # Update document statistics
                    document_stats[book_title]['total'] += 1
                    
                    if is_task:
                        document_stats[book_title]['tasks'] += 1
                    
                    if has_image:
                        document_stats[book_title]['with_images'] += 1
                    
                    if has_fen:
                        document_stats[book_title]['with_fen'] += 1
                    
                    if is_task and has_image:
                        document_stats[book_title]['tasks_with_images'] += 1
                    
                    if is_task and has_fen:
                        document_stats[book_title]['tasks_with_fen'] += 1
                    
                    if is_task and has_image and has_fen:
                        document_stats[book_title]['tasks_with_both'] += 1
                
                offset += limit
                
                if batch_size < limit:
                    break
            
            # Print summary for each document
            print("\n===== DOCUMENT STATISTICS =====")
            for doc_title, stats in sorted(document_stats.items()):
                print(f"\nDocument: {doc_title}")
                print(f"  Total objects: {stats['total']}")
                print(f"  Task objects: {stats['tasks']}")
                print(f"  Objects with images: {stats['with_images']}")
                print(f"  Objects with FEN: {stats['with_fen']}")
                
                # Calculate percentages if there are tasks
                if stats['tasks'] > 0:
                    img_pct = stats['tasks_with_images'] / stats['tasks'] * 100
                    fen_pct = stats['tasks_with_fen'] / stats['tasks'] * 100
                    both_pct = stats['tasks_with_both'] / stats['tasks'] * 100
                    
                    print(f"  Tasks with images: {stats['tasks_with_images']}/{stats['tasks']} ({img_pct:.1f}%)")
                    print(f"  Tasks with FEN: {stats['tasks_with_fen']}/{stats['tasks']} ({fen_pct:.1f}%)")
                    print(f"  Tasks with both: {stats['tasks_with_both']}/{stats['tasks']} ({both_pct:.1f}%)")
                
        except Exception as e:
            print(f"Error fetching objects: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client connection
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    count_by_document() 