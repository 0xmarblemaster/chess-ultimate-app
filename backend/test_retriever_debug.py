#!/usr/bin/env python3
"""
Test script to debug retriever agent FEN search issues
"""
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

import logging
from backend.etl.agents.retriever_agent import retrieve_by_fen, extract_fen_from_query, is_fen_like

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fen_extraction():
    """Test FEN extraction from query"""
    test_queries = [
        "What's the best move in position rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "Analyze this position: r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3",
        "Just a regular chess question without FEN"
    ]
    
    print("=== Testing FEN Extraction ===")
    for query in test_queries:
        extracted_fen = extract_fen_from_query(query)
        print(f"Query: {query[:50]}...")
        print(f"Extracted FEN: {extracted_fen}")
        if extracted_fen:
            print(f"Is FEN-like: {is_fen_like(extracted_fen)}")
        print()

def test_weaviate_connection():
    """Test Weaviate connection"""
    print("=== Testing Weaviate Connection ===")
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        client = get_weaviate_client()
        if client:
            print("✅ Weaviate connection successful")
            
            # Check collections
            try:
                from backend.etl import config as etl_config_module
                from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
                
                print(f"Checking collection: {etl_config_module.WEAVIATE_CLASS_NAME}")
                lesson_collection = client.collections.get(etl_config_module.WEAVIATE_CLASS_NAME)
                lesson_results = lesson_collection.query.fetch_objects(limit=3)
                print(f"Found {len(lesson_results.objects) if lesson_results.objects else 0} lesson objects")
                
                print(f"Checking collection: {CHESS_OPENING_CLASS_NAME}")
                opening_collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
                opening_results = opening_collection.query.fetch_objects(limit=3)
                print(f"Found {len(opening_results.objects) if opening_results.objects else 0} opening objects")
                
                # client.close() removed - Weaviate client manages connections automatically
            except Exception as e:
                print(f"❌ Error checking collections: {e}")
                if client: # client.close() removed - Weaviate client manages connections automatically
        else:
            print("❌ Failed to connect to Weaviate")
    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {e}")

def test_retrieve_by_fen():
    """Test retrieve_by_fen function"""
    print("=== Testing retrieve_by_fen Function ===")
    
    # Test with starting position
    test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    print(f"Testing with starting position FEN: {test_fen}")
    
    try:
        results = retrieve_by_fen(test_fen, limit=5)
        print(f"Results: {len(results)} items found")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result}")
        print()
    except Exception as e:
        print(f"❌ Error in retrieve_by_fen: {e}")
        import traceback
        traceback.print_exc()

def test_config():
    """Test ETL config"""
    print("=== Testing ETL Config ===")
    try:
        from backend.etl import config as etl_config_module
        print(f"WEAVIATE_CLASS_NAME: {etl_config_module.WEAVIATE_CLASS_NAME}")
        print(f"WEAVIATE_URL: {etl_config_module.WEAVIATE_URL}")
        print(f"Has STOCKFISH_PATH: {hasattr(etl_config_module, 'STOCKFISH_PATH')}")
        if hasattr(etl_config_module, 'STOCKFISH_PATH'):
            print(f"STOCKFISH_PATH: {etl_config_module.STOCKFISH_PATH}")
    except Exception as e:
        print(f"❌ Error loading ETL config: {e}")

if __name__ == "__main__":
    print("🔍 Starting Retriever Agent Debug Test\n")
    
    test_config()
    print()
    
    test_fen_extraction()
    print()
    
    test_weaviate_connection()
    print()
    
    test_retrieve_by_fen()
    
    print("✅ Debug test completed") 