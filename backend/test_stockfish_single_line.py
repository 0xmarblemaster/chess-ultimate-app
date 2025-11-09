#!/usr/bin/env python3
"""
Test script to verify Stockfish implementation returns exactly 1 analysis line.
This script tests both the direct analyzer and the API endpoint.
"""

import sys
import os
import requests
import json
import time

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from stockfish_analyzer import analyze_fen_with_stockfish, analyze_fen_with_stockfish_service, init_stockfish

def test_direct_stockfish_analyzer():
    """Test the direct Stockfish analyzer functions."""
    print("=" * 60)
    print("TESTING DIRECT STOCKFISH ANALYZER")
    print("=" * 60)
    
    # Initialize Stockfish
    print("1. Initializing Stockfish engine...")
    if not init_stockfish():
        print("❌ Failed to initialize Stockfish engine")
        return False
    print("✅ Stockfish engine initialized successfully")
    
    # Test positions
    test_positions = [
        {
            "name": "Starting Position",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        },
        {
            "name": "Mate in 1 Position",
            "fen": "4k3/7R/3KN3/8/8/8/8/8 w - - 0 1"
        },
        {
            "name": "Complex Middle Game",
            "fen": "r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        }
    ]
    
    for i, position in enumerate(test_positions, 1):
        print(f"\n{i}. Testing {position['name']}:")
        print(f"   FEN: {position['fen']}")
        
        # Test with legacy function
        print("   Testing legacy analyzer...")
        result_legacy = analyze_fen_with_stockfish(
            fen_string=position['fen'],
            time_limit=2.0,
            multipv=1,
            depth_limit=15
        )
        
        if result_legacy is None:
            print("   ❌ Legacy analyzer returned None")
            continue
        elif len(result_legacy) != 1:
            print(f"   ❌ Legacy analyzer returned {len(result_legacy)} lines (expected 1)")
            continue
        else:
            line = result_legacy[0]
            print(f"   ✅ Legacy analyzer returned 1 line:")
            print(f"      Evaluation: {line.get('evaluation_string', 'N/A')}")
            print(f"      Best line: {line.get('pv_san', 'N/A')}")
            print(f"      Depth: {line.get('depth', 'N/A')}")
        
        # Test with service function
        print("   Testing service analyzer...")
        result_service = analyze_fen_with_stockfish_service(
            fen_string=position['fen'],
            time_limit=2.0,
            multipv=1,
            depth_limit=15
        )
        
        if result_service is None:
            print("   ❌ Service analyzer returned None")
            continue
        elif len(result_service) != 1:
            print(f"   ❌ Service analyzer returned {len(result_service)} lines (expected 1)")
            continue
        else:
            line = result_service[0]
            print(f"   ✅ Service analyzer returned 1 line:")
            print(f"      Evaluation: {line.get('evaluation_string', 'N/A')}")
            print(f"      Best line: {line.get('pv_san', 'N/A')}")
            print(f"      Depth: {line.get('depth', 'N/A')}")
    
    return True

def test_api_endpoint():
    """Test the API endpoint for position analysis."""
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINT")
    print("=" * 60)
    
    base_url = "http://localhost:5001"
    endpoint = f"{base_url}/api/chess/analyze_position"
    
    # Check if server is running
    print("1. Checking if server is running...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print("✅ Server is running")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not running or not accessible: {e}")
        print("   Please start the backend server with: python backend/app.py")
        return False
    
    # Test positions
    test_positions = [
        {
            "name": "Starting Position",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        },
        {
            "name": "Mate in 1 Position", 
            "fen": "4k3/7R/3KN3/8/8/8/8/8 w - - 0 1"
        }
    ]
    
    for i, position in enumerate(test_positions, 1):
        print(f"\n{i}. Testing {position['name']} via API:")
        print(f"   FEN: {position['fen']}")
        
        try:
            # Make API request
            payload = {"fen": position['fen']}
            response = requests.post(endpoint, json=payload, timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ API returned status code {response.status_code}")
                print(f"   Response: {response.text}")
                continue
            
            data = response.json()
            
            # Check response structure
            if 'lines' not in data:
                print("   ❌ API response missing 'lines' field")
                continue
            
            lines = data['lines']
            if not isinstance(lines, list):
                print("   ❌ API 'lines' field is not a list")
                continue
            
            if len(lines) != 1:
                print(f"   ❌ API returned {len(lines)} lines (expected 1)")
                continue
            
            # Validate line structure
            line = lines[0]
            required_fields = ['pv_san', 'evaluation_string', 'evaluation_numerical', 'depth']
            missing_fields = [field for field in required_fields if field not in line]
            
            if missing_fields:
                print(f"   ❌ Line missing required fields: {missing_fields}")
                continue
            
            print(f"   ✅ API returned 1 line successfully:")
            print(f"      Evaluation: {line.get('evaluation_string', 'N/A')}")
            print(f"      Best line: {line.get('pv_san', 'N/A')}")
            print(f"      Depth: {line.get('depth', 'N/A')}")
            print(f"      Commentary: {data.get('commentary', 'N/A')}")
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ API request failed: {e}")
            continue
        except json.JSONDecodeError as e:
            print(f"   ❌ Failed to parse API response as JSON: {e}")
            continue
    
    return True

def main():
    """Run all tests."""
    print("STOCKFISH SINGLE LINE ANALYSIS TEST")
    print("Testing that Stockfish returns exactly 1 analysis line")
    print("=" * 60)
    
    # Test direct analyzer
    direct_success = test_direct_stockfish_analyzer()
    
    # Test API endpoint
    api_success = test_api_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Direct Analyzer: {'✅ PASSED' if direct_success else '❌ FAILED'}")
    print(f"API Endpoint: {'✅ PASSED' if api_success else '❌ FAILED'}")
    
    if direct_success and api_success:
        print("\n🎉 ALL TESTS PASSED! Stockfish is correctly configured to return 1 line.")
    else:
        print("\n⚠️  Some tests failed. Please check the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 