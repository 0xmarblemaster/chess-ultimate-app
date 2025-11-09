#!/usr/bin/env python3

import re

def test_fen_regex():
    query = "Find games with this position rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    
    # Current regex from router_agent.py
    fen_pattern = r"([rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}\s+[wb]\s+([KQkq]{1,4}|-)\s+(-|[a-h][1-8])(\s+\d+\s+\d+)?)"
    
    match = re.search(fen_pattern, query)
    if match:
        print("✅ Match found!")
        print(f"Full match: {match.group(0)}")
        print(f"Group 1 (board): {match.group(1)}")
        return match.group(0)  # Return full FEN
    else:
        print("❌ No match found")
        
        # Try a simpler pattern
        simple_pattern = r"[rnbqkpRNBQKP1-8/]+\s+[wb]\s+[KQkq-]+\s+[a-h1-8-]+\s+\d+\s+\d+"
        simple_match = re.search(simple_pattern, query)
        if simple_match:
            print(f"✅ Simple pattern matched: {simple_match.group(0)}")
            return simple_match.group(0)
        else:
            print("❌ Even simple pattern failed")
        
        return None

if __name__ == "__main__":
    result = test_fen_regex()
    print(f"\nExtracted FEN: {result}") 