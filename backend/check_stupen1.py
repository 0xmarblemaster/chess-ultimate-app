#!/usr/bin/env python3
from etl.weaviate_loader import get_weaviate_client
from etl import config
from collections import defaultdict

def check_stupen1():
    """
    Check statistics for Ступень 1 document
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
            
            # Initialize counters for each lesson
            lesson_stats = defaultdict(lambda: {
                'total': 0,
                'tasks': 0,
                'with_images': 0,
                'with_fen': 0,
                'tasks_with_images': 0,
                'tasks_with_fen': 0,
                'tasks_with_both': 0,
                'sample_tasks': []
            })
            
            # Track tasks with numbers in their text
            numbered_tasks = []
            
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
                    
                    # Only process objects from Ступень 1 (by checking if chunk_id contains "lesson")
                    book_title = props.get("book_title", "")
                    if "Ступень 1" not in book_title and "ступень 1" not in book_title and "Друзья" not in book_title:
                        continue
                        
                    # Get lesson number/name
                    lesson_number = props.get("lesson_number", "unknown")
                    lesson_key = f"Lesson {lesson_number}"
                    
                    # Count various properties
                    is_task = props.get("type") == "task" or props.get("type") == "general_task"
                    has_image = bool(props.get("image"))
                    has_fen = bool(props.get("fen"))
                    
                    # Update lesson statistics
                    lesson_stats[lesson_key]['total'] += 1
                    
                    if is_task:
                        lesson_stats[lesson_key]['tasks'] += 1
                    
                    if has_image:
                        lesson_stats[lesson_key]['with_images'] += 1
                    
                    if has_fen:
                        lesson_stats[lesson_key]['with_fen'] += 1
                    
                    if is_task and has_image:
                        lesson_stats[lesson_key]['tasks_with_images'] += 1
                    
                    if is_task and has_fen:
                        lesson_stats[lesson_key]['tasks_with_fen'] += 1
                    
                    if is_task and has_image and has_fen:
                        lesson_stats[lesson_key]['tasks_with_both'] += 1
                    
                    # Collect some sample tasks (especially with numbers)
                    task_text = props.get("text", "")
                    if is_task and task_text and len(lesson_stats[lesson_key]['sample_tasks']) < 5:
                        lesson_stats[lesson_key]['sample_tasks'].append({
                            'uuid': str(obj.uuid),
                            'text': task_text,
                            'has_image': has_image,
                            'has_fen': has_fen,
                            'image': props.get("image", "None")
                        })
                    
                    # Check for tasks with just numbers and underscores (like "43 ___________")
                    import re
                    if is_task and task_text and re.match(r'^\s*\d+\s*_+\s*$', task_text):
                        numbered_tasks.append({
                            'uuid': str(obj.uuid),
                            'text': task_text,
                            'has_image': has_image,
                            'has_fen': has_fen,
                            'image': props.get("image", "None")
                        })
                
                offset += limit
                
                if batch_size < limit:
                    break
            
            # Calculate totals across all lessons
            total_tasks = sum(stats['tasks'] for stats in lesson_stats.values())
            total_with_images = sum(stats['tasks_with_images'] for stats in lesson_stats.values())
            total_with_fen = sum(stats['tasks_with_fen'] for stats in lesson_stats.values())
            total_with_both = sum(stats['tasks_with_both'] for stats in lesson_stats.values())
            
            # Print summary for Ступень 1
            print("\n===== СТУПЕНЬ 1 STATISTICS =====")
            print(f"Total lessons: {len(lesson_stats)}")
            print(f"Total tasks: {total_tasks}")
            print(f"Tasks with images: {total_with_images} ({total_with_images/total_tasks*100:.1f}% of tasks)")
            print(f"Tasks with FEN: {total_with_fen} ({total_with_fen/total_tasks*100:.1f}% of tasks)")
            print(f"Tasks with both image and FEN: {total_with_both} ({total_with_both/total_tasks*100:.1f}% of tasks)")
            
            # Print numbered tasks analysis
            print(f"\nFound {len(numbered_tasks)} tasks with number-underscore format (e.g., '43 ___________')")
            print(f"Of these: {sum(1 for t in numbered_tasks if t['has_image'])} have images, {sum(1 for t in numbered_tasks if t['has_fen'])} have FEN")
            
            if numbered_tasks:
                print("\nSample number-underscore tasks:")
                for i, task in enumerate(numbered_tasks[:5]):
                    print(f"  {i+1}. Text: '{task['text']}', Image: {task['has_image']}, FEN: {task['has_fen']}, Image name: {task['image']}")
            
            # Print top 5 lessons with the most tasks
            print("\nTop lessons by task count:")
            top_lessons = sorted(lesson_stats.items(), key=lambda x: x[1]['tasks'], reverse=True)[:5]
            for lesson_name, stats in top_lessons:
                print(f"\nLesson: {lesson_name}")
                print(f"  Total tasks: {stats['tasks']}")
                print(f"  Tasks with images: {stats['tasks_with_images']} ({stats['tasks_with_images']/stats['tasks']*100:.1f}% if >0 else 0)")
                print(f"  Tasks with FEN: {stats['tasks_with_fen']} ({stats['tasks_with_fen']/stats['tasks']*100:.1f}% if >0 else 0)")
                
                if stats['sample_tasks']:
                    print(f"  Sample tasks:")
                    for i, task in enumerate(stats['sample_tasks'][:3]):
                        print(f"    {i+1}. '{task['text']}', Image: {task['has_image']}, FEN: {task['has_fen']}")
                
        except Exception as e:
            print(f"Error processing objects: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client connection
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    check_stupen1() 