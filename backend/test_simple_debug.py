#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    print("Testing imports...")
    
    # Test 1: Weaviate connection
    try:
        from etl.weaviate_loader import get_weaviate_client
        client = get_weaviate_client()
        if client:
            print("✓ Weaviate connection works")
            # client.close() removed - Weaviate client manages connections automatically
        else:
            print("✗ Weaviate connection failed")
    except Exception as e:
        print(f"✗ Weaviate error: {e}")
    
    # Test 2: Router agent import
    try:
        from etl.agents import router_agent_instance
        print(f"✓ Router agent imported: {type(router_agent_instance)}")
    except Exception as e:
        print(f"✗ Router agent import error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Simple router test
    try:
        test_state = {
            "user_query": "test query",
            "current_board_fen": None,
            "router_metadata": {}
        }
        result = router_agent_instance.classify_query(test_state)
        print(f"✓ Router classification works: {result.get('query_type')}")
    except Exception as e:
        print(f"✗ Router classification error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_imports() 