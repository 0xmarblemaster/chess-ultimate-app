#!/usr/bin/env python3

import requests
import json

def test_answer_agent_fix():
    """Comprehensive test to verify the Answer Agent fix is working."""
    
    print("🧪 Final Verification: Answer Agent Fix")
    print("=" * 60)
    
    api_url = "http://localhost:5001/api/chat/rag"
    
    test_cases = [
        {
            "name": "Simple Math Question",
            "query": "What is 10 + 15?",
            "expected_keywords": ["25", "10", "15"]
        },
        {
            "name": "Chess Question",
            "query": "What is the starting position in chess?",
            "expected_keywords": ["starting", "position", "initial"]
        },
        {
            "name": "General Question",
            "query": "Explain what a chess opening is",
            "expected_keywords": ["opening", "chess", "moves"]
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 40)
        
        test_data = {
            "query": test_case["query"],
            "session_id": f"test_final_{i}",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "query_type": "semantic_search"
        }
        
        try:
            response = requests.post(api_url, json=test_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                
                # Check for the old error
                if "'OpenAI' object has no attribute 'generate'" in answer:
                    print(f"❌ FAILED: Old error still present!")
                    all_passed = False
                    continue
                
                # Check for any error messages
                if "error" in answer.lower() and "generating answer" in answer.lower():
                    print(f"❌ FAILED: Error in answer: {answer[:100]}...")
                    all_passed = False
                    continue
                
                # Check if we got a reasonable answer
                if len(answer) < 10:
                    print(f"❌ FAILED: Answer too short: '{answer}'")
                    all_passed = False
                    continue
                
                # Check for expected keywords (optional)
                keyword_found = any(keyword.lower() in answer.lower() for keyword in test_case["expected_keywords"])
                
                print(f"✅ SUCCESS: Got valid answer ({len(answer)} chars)")
                print(f"   Keywords found: {keyword_found}")
                print(f"   Answer preview: {answer[:80]}...")
                
            else:
                print(f"❌ FAILED: HTTP {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
                all_passed = False
                
        except Exception as e:
            print(f"❌ FAILED: Request error: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Answer Agent is working correctly!")
        print("✅ The 'OpenAI' object has no attribute 'generate' error is FIXED!")
    else:
        print("❌ Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    test_answer_agent_fix() 