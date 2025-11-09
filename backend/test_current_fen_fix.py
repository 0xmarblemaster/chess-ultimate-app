#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_current_fen_fix():
    print("Testing Current FEN Fix...")
    print("=" * 60)
    
    # Test scenario: User asks about "current FEN" but query contains a different FEN
    user_query = "Search games for the current FEN r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3"
    current_board_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # Starting position
    
    print(f"User query: {user_query}")
    print(f"Current board FEN (from UI): {current_board_fen}")
    print(f"FEN in query text: r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3")
    print()
    
    # Test the router agent
    print("Testing Router Agent...")
    try:
        from etl.agents import router_agent_instance
        
        test_state = {
            "user_query": user_query,
            "current_board_fen": current_board_fen,
            "raw_user_query": user_query,
            "chat_history": [],
            "retrieved_chunks": [],
            "answer_parts": [],
            "final_answer": None,
            "error_message": None,
            "query_type": None,
            "router_metadata": {},
            "fen_for_analysis": None,
            "diagram_number": None,
            "game_filters": None,
            "session_pgn": None
        }
        
        result_state = router_agent_instance.classify_query(test_state)
        
        print(f"✓ Query classified as: {result_state.get('query_type')}")
        print(f"✓ FEN for analysis: {result_state.get('fen_for_analysis')}")
        print(f"✓ Router metadata: {result_state.get('router_metadata')}")
        
        # Verify the fix worked
        expected_fen = current_board_fen  # Should use current board FEN, not query FEN
        actual_fen = result_state.get('fen_for_analysis')
        
        if actual_fen == expected_fen:
            print(f"✅ SUCCESS: Router correctly used current board FEN: {actual_fen}")
        else:
            print(f"❌ FAILED: Router used wrong FEN")
            print(f"   Expected: {expected_fen}")
            print(f"   Actual: {actual_fen}")
            return False
            
    except Exception as e:
        print(f"❌ Router agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # Test another scenario: User asks about specific FEN (not current)
    print("Testing specific FEN query (should use query FEN)...")
    specific_query = "Find games with FEN r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3"
    
    test_state2 = {
        "user_query": specific_query,
        "current_board_fen": current_board_fen,
        "raw_user_query": specific_query,
        "chat_history": [],
        "retrieved_chunks": [],
        "answer_parts": [],
        "final_answer": None,
        "error_message": None,
        "query_type": None,
        "router_metadata": {},
        "fen_for_analysis": None,
        "diagram_number": None,
        "game_filters": None,
        "session_pgn": None
    }
    
    result_state2 = router_agent_instance.classify_query(test_state2)
    
    print(f"✓ Query classified as: {result_state2.get('query_type')}")
    print(f"✓ FEN for analysis: {result_state2.get('fen_for_analysis')}")
    
    # This should use the FEN from the query, not current board
    expected_fen2 = "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3"
    actual_fen2 = result_state2.get('fen_for_analysis')
    
    if actual_fen2 == expected_fen2:
        print(f"✅ SUCCESS: Router correctly used query FEN for specific search: {actual_fen2}")
    else:
        print(f"❌ FAILED: Router used wrong FEN for specific search")
        print(f"   Expected: {expected_fen2}")
        print(f"   Actual: {actual_fen2}")
        return False
    
    print()
    print("🎉 All tests passed! Current FEN fix is working correctly.")
    return True

if __name__ == "__main__":
    test_current_fen_fix() 