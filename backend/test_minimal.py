#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_minimal():
    print("Starting minimal test...")
    
    # Test 1: Basic imports
    try:
        print("Testing basic imports...")
        from etl.weaviate_loader import get_weaviate_client
        print("✓ Weaviate loader imported")
        
        from etl.agents.router_agent import RouterAgent
        print("✓ RouterAgent class imported")
        
        from llm.openai_llm import OpenAILLM
        print("✓ OpenAILLM class imported")
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Create instances manually
    try:
        print("Testing manual instance creation...")
        
        # Create router agent without LLM client first
        router = RouterAgent(llm_client=None)
        print("✓ RouterAgent created without LLM client")
        
        # Test simple classification
        test_state = {
            "user_query": "test query",
            "current_board_fen": None,
            "router_metadata": {}
        }
        result = router.classify_query(test_state)
        print(f"✓ Router classification works: {result.get('query_type')}")
        
    except Exception as e:
        print(f"✗ Manual instance creation error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("Minimal test completed successfully!")

if __name__ == "__main__":
    test_minimal() 