#!/usr/bin/env python3
"""
Fix Content Mapping Issue
Reload Russian education data with proper field mapping
"""

import os
import json
import weaviate

def fix_content_mapping():
    """Fix the content mapping by reloading with correct field mapping"""
    try:
        print("🔧 FIXING CONTENT MAPPING ISSUE")
        print("=" * 40)
        
        # Connect to Weaviate
        client = weaviate.connect_to_local(host="localhost", port=8080)
        print("✅ Connected to Weaviate")
        
        # Delete existing collection and recreate
        print("🗑️ Deleting existing ChessLessonChunk collection...")
        try:
            client.collections.delete('ChessLessonChunk')
            print("✅ Deleted existing collection")
        except Exception as e:
            print(f"ℹ️ Collection may not exist: {e}")
        
        # Create collection with proper schema
        print("📋 Creating new ChessLessonChunk collection...")
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
        
        # Load and properly map the data
        results_file = 'russian_education_test_results.json'
        if not os.path.exists(results_file):
            print(f"❌ Error: {results_file} not found")
            return
        
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        print(f"📦 Loading {len(chunks)} chunks with CORRECTED field mapping...")
        
        # Insert objects with proper content mapping
        inserted_count = 0
        for i, chunk in enumerate(chunks):
            try:
                # FIXED: Map 'text' to 'content' field properly
                obj = {
                    "content": chunk.get("text", ""),  # ← FIX: was chunk.get("content", "")
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
                
                # Insert single object
                uuid = collection.data.insert(obj)
                inserted_count += 1
                
                # Show progress for first few items
                if i < 3:
                    print(f"   ✅ Object {i+1}: content='{obj['content'][:50]}...'")
                    
            except Exception as e:
                print(f"❌ Error inserting object {i+1}: {e}")
        
        print(f"✅ Successfully loaded {inserted_count} chunks with CORRECT content")
        
        # Verify the fix
        print("\n🔍 VERIFYING THE FIX...")
        total_objects = collection.aggregate.over_all(total_count=True)
        print(f"📊 Total objects: {total_objects.total_count}")
        
        # Test search with actual content
        sample_results = collection.query.bm25(
            query="шах",
            limit=2
        )
        
        print(f"📋 Sample search for 'шах': {len(sample_results.objects)} results")
        for i, obj in enumerate(sample_results.objects):
            content = obj.properties.get('content', '')[:100]
            print(f"  {i+1}. {content}...")
        
        # client.close() removed - Weaviate client manages connections automatically
        print("\n🎉 CONTENT MAPPING FIXED! The agent should now be able to answer questions about УРОК 2.")
        
    except Exception as e:
        print(f"❌ Error fixing content mapping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_content_mapping() 