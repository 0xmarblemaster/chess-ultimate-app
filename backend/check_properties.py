#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.weaviate_loader import get_weaviate_client

def check_properties():
    print("Checking ChessGame properties...")
    
    client = get_weaviate_client()
    if not client:
        print("✗ Could not connect to Weaviate")
        return
    
    try:
        collection = client.collections.get('ChessGame')
        result = collection.query.fetch_objects(limit=1)
        if result.objects:
            print('ChessGame properties:')
            for prop in sorted(result.objects[0].properties.keys()):
                print(f'  - {prop}')
                
            # Check for FEN-related properties
            obj = result.objects[0]
            fen_props = [prop for prop in obj.properties.keys() if 'fen' in prop.lower()]
            print(f'\nFEN-related properties: {fen_props}')
            
            # Show sample values for FEN properties
            for prop in fen_props:
                value = obj.properties.get(prop)
                if isinstance(value, list) and value:
                    print(f'  {prop}: {value[0]} (list with {len(value)} items)')
                else:
                    print(f'  {prop}: {value}')
        else:
            print("No objects found in ChessGame collection")
        
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"✗ Error checking properties: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_properties() 