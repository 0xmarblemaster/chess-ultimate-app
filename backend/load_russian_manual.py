#!/usr/bin/env python3
"""
Load Russian Education Data Manually - No Vectorization
"""

import os
import json
import weaviate
from pathlib import Path

def load_russian_education_data():
    """Load Russian education data manually"""
    try:
        # Connect to Weaviate with minimal configuration
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            skip_init_checks=True
        )
        print("✅ Connected to Weaviate")
        
        # Check collections
        collections = client.collections.list_all()
        print(f"📋 Existing collections: {list(collections.keys())}")
        
        # Delete existing collection if it exists
        if 'ChessLessonChunk' in collections:
            client.collections.delete('ChessLessonChunk')
            print("🗑️ Deleted existing ChessLessonChunk collection")
        
        # Create collection with explicit no vectorizer configuration
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
        
        print("✅ Created ChessLessonChunk collection with NO vectorization")
        
        # Load the data
        results_file = 'russian_education_test_results.json'
        if not os.path.exists(results_file):
            print(f"❌ Error: {results_file} not found")
            return
        
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        print(f"📦 Loading {len(chunks)} chunks...")
        
        # Insert objects one by one to avoid batch issues
        inserted_count = 0
        for i, chunk in enumerate(chunks):
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
                
                # Insert single object
                uuid = collection.data.insert(obj)
                inserted_count += 1
                if (i + 1) % 5 == 0:
                    print(f"📥 Inserted {i + 1}/{len(chunks)} objects")
                    
            except Exception as e:
                print(f"❌ Error inserting object {i+1}: {e}")
        
        print(f"✅ Successfully loaded {inserted_count} chunks into knowledge database")
        
        # Verify the data
        print("\n🔍 Verifying data...")
        total_objects = collection.aggregate.over_all(total_count=True)
        print(f"📊 Total objects in collection: {total_objects.total_count}")
        
        # Test keyword search
        try:
            response = collection.query.bm25(
                query="шах",
                limit=5
            )
            print(f"📋 Search for 'шах' (check): {len(response.objects)} results")
            for i, obj in enumerate(response.objects):
                content = obj.properties.get('content', '')[:100]
                print(f"  {i+1}. {content}...")
        except Exception as e:
            print(f"⚠️ Search test failed: {e}")
        
        # client.close() removed - Weaviate client manages connections automatically
        print("\n🎉 Russian education data loaded successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Manual Russian Education Data Loading")
    print("=" * 40)
    load_russian_education_data() 