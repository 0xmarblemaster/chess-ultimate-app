#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_weaviate_data():
    """Quick test to see what's in Weaviate"""
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl import config as etl_config_module
        from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
        
        print("Connecting to Weaviate...")
        client = get_weaviate_client()
        if not client:
            print("❌ Failed to connect to Weaviate")
            return
            
        print("✅ Connected to Weaviate")
        
        # Check lesson chunks
        print(f"\n=== Checking {etl_config_module.WEAVIATE_CLASS_NAME} ===")
        try:
            lesson_collection = client.collections.get(etl_config_module.WEAVIATE_CLASS_NAME)
            lesson_results = lesson_collection.query.fetch_objects(limit=3)
            
            if lesson_results and lesson_results.objects:
                print(f"Found {len(lesson_results.objects)} lesson objects")
                for i, obj in enumerate(lesson_results.objects):
                    props = obj.properties
                    print(f"  {i+1}. ID: {obj.uuid}")
                    print(f"     FEN: {props.get('fen', 'N/A')}")
                    print(f"     Text: {props.get('text', 'N/A')[:100]}...")
                    print()
            else:
                print("❌ No lesson objects found")
        except Exception as e:
            print(f"❌ Error checking lesson collection: {e}")
        
        # Check openings
        print(f"\n=== Checking {CHESS_OPENING_CLASS_NAME} ===")
        try:
            opening_collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
            opening_results = opening_collection.query.fetch_objects(limit=3)
            
            if opening_results and opening_results.objects:
                print(f"Found {len(opening_results.objects)} opening objects")
                for i, obj in enumerate(opening_results.objects):
                    props = obj.properties
                    print(f"  {i+1}. ID: {obj.uuid}")
                    print(f"     Name: {props.get('opening_name', 'N/A')}")
                    print(f"     FEN: {props.get('fen', 'N/A')}")
                    print(f"     ECO: {props.get('eco_code', 'N/A')}")
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

def test_simple_retrieval():
    """Test the retrieve_by_fen function"""
    try:
        from backend.etl.agents.retriever_agent import retrieve_by_fen
        
        print("\n=== Testing retrieve_by_fen ===")
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        print(f"Testing FEN: {test_fen}")
        
        results = retrieve_by_fen(test_fen, limit=3)
        print(f"Results: {len(results)} items")
        
        for i, result in enumerate(results):
            print(f"  {i+1}. {result}")
            
    except Exception as e:
        print(f"❌ Error testing retrieval: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Quick Weaviate Test\n")
    test_weaviate_data()
    test_simple_retrieval() 