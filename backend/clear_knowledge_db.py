#!/usr/bin/env python3
"""
Clear Knowledge Database for Fresh Processing
"""

import weaviate

def clear_chess_lesson_chunks():
    """Clear the ChessLessonChunk collection for fresh processing"""
    try:
        print('🗑️ CLEARING CHESS LESSON CHUNK COLLECTION')
        print('=' * 50)
        
        # Connect to Weaviate
        client = weaviate.connect_to_local(host="localhost", port=8080)
        print("✅ Connected to Weaviate")
        
        # Check if collection exists
        collections = client.collections.list_all()
        if 'ChessLessonChunk' in collections:
            # Get current count
            collection = client.collections.get("ChessLessonChunk")
            total_objects = collection.aggregate.over_all(total_count=True)
            print(f"📊 Current objects in ChessLessonChunk: {total_objects.total_count}")
            
            # Delete the collection
            client.collections.delete('ChessLessonChunk')
            print("✅ Deleted ChessLessonChunk collection")
        else:
            print("ℹ️ ChessLessonChunk collection doesn't exist")
        
        # Recreate the collection with proper schema
        print("📋 Creating fresh ChessLessonChunk collection...")
        collection = client.collections.create(
            name="ChessLessonChunk",
            description="Chess lesson chunks with Russian education content and FEN strings",
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
                weaviate.collections.classes.config.Property(
                    name="diagram_analysis", 
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
            ]
        )
        print("✅ Created fresh ChessLessonChunk collection with FEN support")
        
        # client.close() removed - Weaviate client manages connections automatically
        print("\n🎉 DATABASE CLEARED AND READY FOR FRESH PROCESSING!")
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clear_chess_lesson_chunks() 