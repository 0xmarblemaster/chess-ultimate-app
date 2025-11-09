#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def check_fens():
    """Check what FENs exist in the database"""
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl import config as etl_config_module
        from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
        
        client = get_weaviate_client()
        if not client:
            print("❌ Failed to connect to Weaviate")
            return
            
        print("✅ Connected to Weaviate")
        
        # Check lesson chunks
        print(f"\n=== Sample FENs in {etl_config_module.WEAVIATE_CLASS_NAME} ===")
        try:
            collection = client.collections.get(etl_config_module.WEAVIATE_CLASS_NAME)
            results = collection.query.fetch_objects(limit=10)
            
            if results and results.objects:
                print(f"Found {len(results.objects)} lesson objects")
                for i, obj in enumerate(results.objects):
                    props = obj.properties
                    fen = props.get('fen', 'N/A')
                    text = props.get('text', 'N/A')[:50]
                    print(f"  {i+1}. FEN: {fen}")
                    print(f"      Text: {text}...")
                    print()
            else:
                print("❌ No lesson objects found")
        except Exception as e:
            print(f"❌ Error checking lesson collection: {e}")
        
        # Check openings
        print(f"\n=== Sample FENs in {CHESS_OPENING_CLASS_NAME} ===")
        try:
            collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
            results = collection.query.fetch_objects(limit=10)
            
            if results and results.objects:
                print(f"Found {len(results.objects)} opening objects")
                for i, obj in enumerate(results.objects):
                    props = obj.properties
                    fen = props.get('fen', 'N/A')
                    name = props.get('opening_name', 'N/A')
                    print(f"  {i+1}. FEN: {fen}")
                    print(f"      Opening: {name}")
                    print()
            else:
                print("❌ No opening objects found")
        except Exception as e:
            print(f"❌ Error checking opening collection: {e}")
            
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fens() 