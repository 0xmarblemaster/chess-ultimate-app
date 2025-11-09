#!/usr/bin/env python3

from etl.weaviate_loader import get_weaviate_client
from etl import config
import json
import os

def get_weaviate_stats():
    """Get statistics about objects in the Weaviate database"""
    
    client = get_weaviate_client()
    if not client:
        print("Could not connect to Weaviate database")
        return
    
    try:
        # Get collection
        collection_name = config.WEAVIATE_CLASS_NAME
        collection = client.collections.get(collection_name)
        
        # Get total count
        total_count = collection.aggregate.over_all(total_count=True).total_count
        print(f"Total objects in collection {collection_name}: {total_count}")
        
        # Get counts of objects with images, FEN, etc.
        # We need to do this by fetching all objects and checking properties
        # since the v4 API doesn't support property existence filters directly
        
        print("Fetching objects to analyze properties (this might take a moment)...")
        # Fetch objects without vectors to save bandwidth/memory
        results = collection.query.fetch_objects(
            limit=total_count,  # Fetch all objects
            include_vector=False
        )
        
        # Count object types
        object_types = {}
        with_image = 0
        with_fen = 0
        with_both = 0
        
        for obj in results.objects:
            # Count by type
            obj_type = obj.properties.get('type', 'unknown')
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
            
            # Count special properties
            has_image = 'image' in obj.properties and obj.properties['image']
            has_fen = 'fen' in obj.properties and obj.properties['fen']
            
            if has_image:
                with_image += 1
            if has_fen:
                with_fen += 1
            if has_image and has_fen:
                with_both += 1
        
        # Print results
        print("\nObjects by type:")
        for obj_type, count in sorted(object_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {obj_type}: {count} ({count/total_count*100:.1f}%)")
        
        print("\nObjects with special properties:")
        print(f"  With image: {with_image} ({with_image/total_count*100:.1f}%)")
        print(f"  With FEN: {with_fen} ({with_fen/total_count*100:.1f}%)")
        print(f"  With both image and FEN: {with_both} ({with_both/total_count*100:.1f}%)")
        
        # Close client
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"Error getting Weaviate statistics: {e}")
        if client:
            # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    get_weaviate_stats() 