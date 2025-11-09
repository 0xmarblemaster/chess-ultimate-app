#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_answer_agent_from_api():
    print("Testing Answer Agent from API context...")
    print("=" * 60)
    
    try:
        # Test the import exactly as the API does it
        from app import active_games, user_sessions
        from etl.agents import answer_agent_instance
        
        print(f"✓ Imported answer_agent_instance from etl.agents")
        print(f"✓ Answer agent type: {type(answer_agent_instance)}")
        print(f"✓ LLM client type: {type(answer_agent_instance.llm_client)}")
        print(f"✓ Has generate method: {hasattr(answer_agent_instance.llm_client, 'generate')}")
        
        if answer_agent_instance.llm_client:
            print(f"✓ LLM client is not None")
            
            # Test the generate method directly
            print("\nTesting LLM client generate method...")
            try:
                test_response = answer_agent_instance.llm_client.generate(
                    prompt="What is 2+2?",
                    system_message="You are a helpful assistant."
                )
                print(f"✓ LLM client generate method works: {test_response[:50]}...")
            except Exception as e:
                print(f"❌ LLM client generate method failed: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # Test the answer agent generate_answer method
            print("\nTesting Answer Agent generate_answer method...")
            try:
                test_answer = answer_agent_instance.generate_answer(
                    query="What is 2+2?",
                    retrieved_documents=[],
                    query_type="direct",
                    current_fen=None
                )
                print(f"✓ Answer agent generate_answer works: {test_answer[:50]}...")
            except Exception as e:
                print(f"❌ Answer agent generate_answer failed: {e}")
                import traceback
                traceback.print_exc()
                return False
                
        else:
            print(f"❌ LLM client is None")
            return False
            
    except Exception as e:
        print(f"❌ Failed to import or test answer agent: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 All tests passed!")
    return True

if __name__ == "__main__":
    test_answer_agent_from_api() 