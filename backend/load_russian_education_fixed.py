#!/usr/bin/env python3
"""
Load Russian Education Data to Knowledge Database - Fixed Version
Properly loads OpenAI API key from .env file and configures Weaviate
"""

import os
import json
import weaviate
from pathlib import Path
from weaviate.collections.classes.config import Configure, Property, DataType

# Load environment variables from the root .env file
try:
    from dotenv import load_dotenv
    # Load from the root directory (mvp1/.env)
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
    print(f"✅ Loaded environment variables from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, trying manual .env loading")
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print(f"✅ Manually loaded .env file from: {env_path}")

def get_weaviate_client():
    """Get Weaviate client with proper OpenAI API key"""
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("   Please ensure your .env file contains: OPENAI_API_KEY=your_key_here")
        return None
    
    print(f"✅ Using OpenAI API key: {openai_key[:20]}...")
    
    # Set up headers for OpenAI API
    headers = {"X-OpenAI-Api-Key": openai_key}
    
    try:
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True
        )
        print("✅ Connected to Weaviate successfully")
        return client
    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {e}")
        return None

def create_chess_lesson_schema(client):
    """Create the ChessLessonChunk collection schema with OpenAI vectorization"""
    try:
        # Define the collection schema with OpenAI text2vec
        collection = client.collections.create(
            name="ChessLessonChunk",
            description="Chess lesson chunks with Russian education content",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-small"
            ),
            properties=[
                Property(name="content", data_type=DataType.TEXT, description="The text content of the lesson chunk"),
                Property(name="book_title", data_type=DataType.TEXT, description="Title of the book or source"),
                Property(name="lesson_number", data_type=DataType.TEXT, description="Lesson number within the book"),
                Property(name="lesson_title", data_type=DataType.TEXT, description="Title of the lesson"),
                Property(name="type", data_type=DataType.TEXT, description="Type of chunk (e.g., 'explanation', 'task', 'example')"),
                Property(name="language", data_type=DataType.TEXT, description="Language of the content"),
                Property(name="content_type", data_type=DataType.TEXT, description="Content type classification"),
                Property(name="source_file", data_type=DataType.TEXT, description="Source file name"),
                Property(name="processing_method", data_type=DataType.TEXT, description="Processing method used"),
                Property(name="fen", data_type=DataType.TEXT, description="FEN string for chess position if any"),
                Property(name="image", data_type=DataType.TEXT, description="Associated image filename if any"),
            ]
        )
        print("✅ Created ChessLessonChunk collection schema with OpenAI vectorization")
        return True
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False

def load_russian_education_data():
    """Load Russian education data into the knowledge database"""
    try:
        # Get Weaviate client with proper API key
        client = get_weaviate_client()
        if not client:
            return
        
        # Check if collection exists, create if not
        collections = client.collections.list_all()
        if 'ChessLessonChunk' not in collections:
            print("📋 Creating ChessLessonChunk collection...")
            if not create_chess_lesson_schema(client):
                return
        else:
            print("📋 ChessLessonChunk collection already exists")
        
        # Load the processed data
        results_file = 'russian_education_test_results.json'
        if not os.path.exists(results_file):
            print(f"❌ Error: {results_file} not found")
            print("   Please run the Russian education test first to generate the data")
            return
        
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        print(f"📦 Loading {len(chunks)} chunks...")
        
        # Get the collection
        collection = client.collections.get("ChessLessonChunk")
        
        # Prepare data for insertion
        objects_to_insert = []
        for chunk in chunks:
            # Map chunk fields to collection properties
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
            objects_to_insert.append(obj)
        
        # Insert data in batches
        batch_size = 10
        inserted_count = 0
        
        for i in range(0, len(objects_to_insert), batch_size):
            batch = objects_to_insert[i:i + batch_size]
            try:
                result = collection.data.insert_many(batch)
                inserted_count += len(batch)
                print(f"📥 Inserted batch {i//batch_size + 1}: {len(batch)} objects")
            except Exception as e:
                print(f"❌ Error inserting batch {i//batch_size + 1}: {e}")
        
        print(f"✅ Successfully loaded {inserted_count} chunks into knowledge database")
        
        # Verify the data
        print("\n🔍 Verifying data...")
        total_objects = collection.aggregate.over_all(total_count=True)
        print(f"📊 Total objects in collection: {total_objects.total_count}")
        
        # Sample vector search query (now that we have OpenAI embeddings)
        try:
            response = collection.query.near_text(
                query="русский шахматы урок",
                limit=3
            )
            
            print(f"📋 Sample vector search results for 'русский шахматы урок': {len(response.objects)} results")
            for i, obj in enumerate(response.objects):
                content = obj.properties.get('content', '')[:100]
                print(f"  {i+1}. {content}...")
        except Exception as e:
            print(f"⚠️  Vector search test failed: {e}")
            # Fallback to keyword search
            response = collection.query.bm25(
                query="шахматы",
                limit=3
            )
            print(f"📋 Sample keyword search results for 'шахматы': {len(response.objects)} results")
            for i, obj in enumerate(response.objects):
                content = obj.properties.get('content', '')[:100]
                print(f"  {i+1}. {content}...")
        
        # client.close() removed - Weaviate client manages connections automatically
        print("\n🎉 Russian education data loaded successfully!")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Russian Education Data Loading (Fixed Version)")
    print("=" * 50)
    load_russian_education_data() 