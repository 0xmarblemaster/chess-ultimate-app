#!/usr/bin/env python3
"""
Final Fix for Content Mapping
Debug and explicitly fix the content field mapping
"""

import os
import json
import weaviate

def final_fix_content():
    """Final fix with explicit debugging"""
    try:
        print("🔧 FINAL CONTENT MAPPING FIX")
        print("=" * 40)
        
        # Load the data first and debug it
        results_file = 'russian_education_test_results.json'
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        print(f"📦 Found {len(chunks)} chunks to process")
        
        # Debug first chunk
        first_chunk = chunks[0]
        print(f"\n🔍 DEBUGGING FIRST CHUNK:")
        print(f"   Keys: {list(first_chunk.keys())}")
        print(f"   'text' field: '{first_chunk.get('text', 'NOT_FOUND')[:100]}...'")
        
        # Connect to Weaviate
        client = weaviate.connect_to_local(host="localhost", port=8080)
        print("\n✅ Connected to Weaviate")
        
        # Delete and recreate collection
        try:
            client.collections.delete('ChessLessonChunk')
            print("🗑️ Deleted existing collection")
        except:
            pass
        
        # Create collection
        collection = client.collections.create(
            name="ChessLessonChunk",
            description="Chess lesson chunks with Russian education content",
            vectorizer_config=weaviate.collections.classes.config.Configure.Vectorizer.none(),
            properties=[
                weaviate.collections.classes.config.Property(
                    name="content", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="book_title", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="lesson_number", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="lesson_title", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="type", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="language", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="content_type", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="source_file", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="processing_method", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="fen", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
                weaviate.collections.classes.config.Property(
                    name="image", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
            ]
        )
        print("✅ Created new collection")
        
        # Insert with explicit debugging
        inserted_count = 0
        for i, chunk in enumerate(chunks):
            try:
                # Extract text content explicitly
                text_content = chunk.get("text", "")
                
                print(f"\n📝 Processing chunk {i+1}:")
                print(f"   Raw text: '{text_content[:50]}...' (length: {len(text_content)})")
                
                # Create object with explicit field mapping
                obj = {
                    "content": text_content,  # Explicit assignment
                    "book_title": chunk.get("book_title", ""),
                    "lesson_number": str(chunk.get("lesson_number", "")),
                    "lesson_title": chunk.get("lesson_title", ""),
                    "type": chunk.get("type", ""),
                    "language": chunk.get("language", "ru"),
                    "content_type": chunk.get("content_type", ""),
                    "source_file": chunk.get("source_file", ""),
                    "processing_method": chunk.get("processing_method", ""),
                    "fen": chunk.get("fen", "") if chunk.get("fen") else "",
                    "image": chunk.get("image", "") if chunk.get("image") else "",
                }
                
                print(f"   Mapped content: '{obj['content'][:50]}...' (length: {len(obj['content'])})")
                
                # Insert object
                uuid = collection.data.insert(obj)
                inserted_count += 1
                print(f"   ✅ Inserted with UUID: {uuid}")
                
                if i >= 2:  # Limit debug output
                    break
                    
            except Exception as e:
                print(f"❌ Error inserting chunk {i+1}: {e}")
        
        # Insert remaining chunks without debug output
        print(f"\n📦 Inserting remaining {len(chunks) - 3} chunks...")
        for i, chunk in enumerate(chunks[3:], start=3):
            try:
                obj = {
                    "content": chunk.get("text", ""),
                    "book_title": chunk.get("book_title", ""),
                    "lesson_number": str(chunk.get("lesson_number", "")),
                    "lesson_title": chunk.get("lesson_title", ""),
                    "type": chunk.get("type", ""),
                    "language": chunk.get("language", "ru"),
                    "content_type": chunk.get("content_type", ""),
                    "source_file": chunk.get("source_file", ""),
                    "processing_method": chunk.get("processing_method", ""),
                    "fen": chunk.get("fen", "") if chunk.get("fen") else "",
                    "image": chunk.get("image", "") if chunk.get("image") else "",
                }
                uuid = collection.data.insert(obj)
                inserted_count += 1
            except Exception as e:
                print(f"❌ Error inserting chunk {i+1}: {e}")
        
        print(f"\n✅ Successfully loaded {inserted_count} chunks")
        
        # Final verification
        print("\n🔍 FINAL VERIFICATION...")
        total_objects = collection.aggregate.over_all(total_count=True)
        print(f"📊 Total objects: {total_objects.total_count}")
        
        # Get sample objects to verify content
        sample_results = collection.query.fetch_objects(limit=2)
        print(f"\n📋 Sample objects:")
        for i, obj in enumerate(sample_results.objects):
            content = obj.properties.get('content', 'NO_CONTENT')
            print(f"  {i+1}. Content: '{content[:100]}...' (length: {len(content)})")
        
        # Test search
        search_results = collection.query.bm25(query="шах", limit=1)
        print(f"\n🔍 Search test for 'шах': {len(search_results.objects)} results")
        if search_results.objects:
            content = search_results.objects[0].properties.get('content', 'NO_CONTENT')
            print(f"   Found: '{content[:100]}...'")
        
        # client.close() removed - Weaviate client manages connections automatically
        print("\n🎉 FINAL FIX COMPLETE!")
        
    except Exception as e:
        print(f"❌ Error in final fix: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_fix_content() 