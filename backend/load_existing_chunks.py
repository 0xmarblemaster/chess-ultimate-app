#!/usr/bin/env python3
"""
Load existing processed chunks into Weaviate ChessLessonChunk collection.
"""

import json
import glob
import os
from etl.weaviate_loader import get_weaviate_client, define_weaviate_schema, load_chunks_to_weaviate, check_collection_exists
from etl import config

def load_existing_chunks():
    """Load all existing chunk files into Weaviate."""
    
    # Connect to Weaviate
    client = get_weaviate_client()
    if not client:
        print("❌ Could not connect to Weaviate")
        return False
    
    print("✅ Connected to Weaviate")
    
    # Ensure schema exists
    if not check_collection_exists(client, config.WEAVIATE_CLASS_NAME):
        print(f"Creating {config.WEAVIATE_CLASS_NAME} collection...")
        define_weaviate_schema(client)
        print("✅ Schema created")
    else:
        print(f"✅ {config.WEAVIATE_CLASS_NAME} collection exists")
    
    # Find all chunk files
    chunk_files = glob.glob(os.path.join(config.PROCESSED_DIR, "*_chunks.json"))
    
    if not chunk_files:
        print(f"❌ No chunk files found in {config.PROCESSED_DIR}")
        return False
    
    print(f"📁 Found {len(chunk_files)} chunk files:")
    for file in chunk_files:
        print(f"   - {os.path.basename(file)}")
    
    total_chunks = 0
    
    # Load each file
    for chunk_file in chunk_files:
        print(f"\n📤 Loading {os.path.basename(chunk_file)}...")
        
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            if chunks:
                load_chunks_to_weaviate(client, chunks)
                total_chunks += len(chunks)
                print(f"✅ Loaded {len(chunks)} chunks from {os.path.basename(chunk_file)}")
            else:
                print(f"⚠️  No chunks found in {os.path.basename(chunk_file)}")
                
        except Exception as e:
            print(f"❌ Error loading {os.path.basename(chunk_file)}: {e}")
    
    # Verify final count
    try:
        collection = client.collections.get(config.WEAVIATE_CLASS_NAME)
        response = collection.aggregate.over_all(total_count=True)
        print(f"\n📊 Final count in {config.WEAVIATE_CLASS_NAME}: {response.total_count} chunks")
        print(f"📈 Total chunks processed: {total_chunks}")
    except Exception as e:
        print(f"❌ Error getting final count: {e}")
    
    # client.close() removed - Weaviate client manages connections automatically
    return True

if __name__ == "__main__":
    print("🚀 Loading existing processed chunks into Weaviate...")
    success = load_existing_chunks()
    if success:
        print("✅ Chunk loading completed!")
    else:
        print("❌ Chunk loading failed!") 