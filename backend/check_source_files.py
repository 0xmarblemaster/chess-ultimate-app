#!/usr/bin/env python3

import weaviate
import os
from collections import Counter

def check_source_files():
    """Check what source files have been loaded into ChessGame collection."""
    
    # Set up headers for OpenAI API key
    headers = {}
    openai_key = "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"
    if openai_key:
        headers["X-OpenAI-Api-Key"] = openai_key
    
    try:
        # Connect using HTTP only to avoid gRPC issues
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True  # Skip gRPC health checks
        )
        
        print("✅ Connected to Weaviate successfully")
        
        # Get the ChessGame collection
        games_collection = client.collections.get('ChessGame')
        
        # Get total count
        try:
            response = games_collection.aggregate.over_all(total_count=True)
            total_count = response.total_count
            print(f"📊 Total games in ChessGame collection: {total_count:,}")
        except Exception as e:
            print(f"⚠️ Could not get total count: {e}")
            total_count = "unknown"
        
        # Fetch a sample of games to check source files
        print(f"\n🔍 Analyzing source files...")
        
        # Fetch games in batches to check all source files
        all_source_files = []
        offset = 0
        batch_size = 1000
        
        while True:
            response = games_collection.query.fetch_objects(
                limit=batch_size,
                offset=offset,
                return_properties=["source_file"]
            )
            
            if not response.objects:
                break
                
            for obj in response.objects:
                source_file = obj.properties.get('source_file')
                if source_file:
                    all_source_files.append(source_file)
            
            offset += len(response.objects)
            print(f"   Processed {offset:,} games...")
            
            # Break if we got fewer objects than requested (end of data)
            if len(response.objects) < batch_size:
                break
        
        # Count source files
        source_counter = Counter(all_source_files)
        
        print(f"\n📁 Source Files Analysis:")
        print(f"   Total unique source files: {len(source_counter)}")
        print(f"   Total games with source info: {len(all_source_files):,}")
        
        print(f"\n📋 Source Files Loaded:")
        for source_file, count in sorted(source_counter.items()):
            print(f"   • {source_file}: {count:,} games")
        
        # Check for patterns
        twic_files = [f for f in source_counter.keys() if 'twic' in f.lower()]
        other_files = [f for f in source_counter.keys() if 'twic' not in f.lower()]
        
        print(f"\n🎯 Summary:")
        print(f"   TWIC files loaded: {len(twic_files)}")
        print(f"   Other PGN files loaded: {len(other_files)}")
        
        if twic_files:
            twic_games = sum(source_counter[f] for f in twic_files)
            print(f"   Games from TWIC files: {twic_games:,}")
        
        if other_files:
            other_games = sum(source_counter[f] for f in other_files)
            print(f"   Games from other files: {other_games:,}")
        
        return source_counter
        
    except Exception as e:
        print(f'❌ Error connecting to Weaviate: {e}')
        return None
    finally:
        try:
            # client.close() removed - Weaviate client manages connections automatically
        except:
            pass

if __name__ == "__main__":
    check_source_files() 