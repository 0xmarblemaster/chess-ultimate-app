#!/usr/bin/env python3
"""
Test script to verify Stockfish implementation works correctly with 3-line analysis.
This will test both the service and legacy methods to ensure they work properly.
"""

import sys
import os
import logging
import time

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from stockfish_analyzer import (
    analyze_fen_with_stockfish,
    analyze_fen_with_stockfish_service,
    init_stockfish
)
from services.stockfish_engine import StockfishEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_stockfish_initialization():
    """Test that Stockfish can be initialized properly."""
    print("=" * 60)
    print("TEST 1: Stockfish Initialization")
    print("=" * 60)
    
    try:
        result = init_stockfish(force_reinit=True)
        if result:
            print("✅ Stockfish initialized successfully")
            return True
        else:
            print("❌ Stockfish initialization failed")
            return False
    except Exception as e:
        print(f"❌ Stockfish initialization error: {e}")
        return False

def test_stockfish_service():
    """Test the StockfishEngine service."""
    print("\n" + "=" * 60)
    print("TEST 2: StockfishEngine Service")
    print("=" * 60)
    
    try:
        engine = StockfishEngine()
        
        # Test healthcheck
        health = engine.healthcheck()
        if not health:
            print("❌ Stockfish service healthcheck failed")
            return False
        print("✅ Stockfish service healthcheck passed")
        
        # Test analysis with starting position
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        print(f"Testing analysis with FEN: {test_fen}")
        
        start_time = time.time()
        result = engine.analyze_fen(
            fen=test_fen,
            multipv=3,  # Three lines
            depth_limit=12,
            time_limit=3.0
        )
        end_time = time.time()
        
        if result is None:
            print("❌ Analysis returned None")
            return False
        
        if not isinstance(result, list):
            print(f"❌ Analysis returned wrong type: {type(result)}")
            return False
        
        if len(result) != 3:
            print(f"❌ Expected 3 analysis lines, got {len(result)}")
            return False
        
        print(f"✅ Analysis completed in {end_time - start_time:.2f}s")
        for i, line in enumerate(result):
            print(f"   Line {i+1}: {line.get('pv_san', 'N/A')} (Eval: {line.get('evaluation_string', 'N/A')})")
        
        engine.quit()
        return True
        
    except Exception as e:
        print(f"❌ StockfishEngine service error: {e}")
        return False

def test_legacy_analyzer():
    """Test the legacy analyze_fen_with_stockfish function."""
    print("\n" + "=" * 60)
    print("TEST 3: Legacy Stockfish Analyzer")
    print("=" * 60)
    
    try:
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        print(f"Testing analysis with FEN: {test_fen}")
        
        start_time = time.time()
        result = analyze_fen_with_stockfish(
            fen_string=test_fen,
            multipv=3,  # Three lines
            depth_limit=12,
            time_limit=3.0
        )
        end_time = time.time()
        
        if result is None:
            print("❌ Analysis returned None")
            return False
        
        if not isinstance(result, list):
            print(f"❌ Analysis returned wrong type: {type(result)}")
            return False
        
        if len(result) != 3:
            print(f"❌ Expected 3 analysis lines, got {len(result)}")
            return False
        
        print(f"✅ Analysis completed in {end_time - start_time:.2f}s")
        for i, line in enumerate(result):
            print(f"   Line {i+1}: {line.get('pv_san', 'N/A')} (Eval: {line.get('evaluation_string', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy analyzer error: {e}")
        return False

def test_service_analyzer():
    """Test the analyze_fen_with_stockfish_service function."""
    print("\n" + "=" * 60)
    print("TEST 4: Service Analyzer Function")
    print("=" * 60)
    
    try:
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        print(f"Testing analysis with FEN: {test_fen}")
        
        start_time = time.time()
        result = analyze_fen_with_stockfish_service(
            fen_string=test_fen,
            multipv=3,  # Three lines
            depth_limit=12,
            time_limit=3.0
        )
        end_time = time.time()
        
        if result is None:
            print("❌ Analysis returned None")
            return False
        
        if not isinstance(result, list):
            print(f"❌ Analysis returned wrong type: {type(result)}")
            return False
        
        if len(result) != 3:
            print(f"❌ Expected 3 analysis lines, got {len(result)}")
            return False
        
        print(f"✅ Analysis completed in {end_time - start_time:.2f}s")
        for i, line in enumerate(result):
            print(f"   Line {i+1}: {line.get('pv_san', 'N/A')} (Eval: {line.get('evaluation_string', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Service analyzer error: {e}")
        return False

def test_api_endpoint():
    """Test the HTTP API endpoint."""
    print("\n" + "=" * 60)
    print("TEST 5: HTTP API Endpoint")
    print("=" * 60)
    
    try:
        import requests
        
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        url = "http://localhost:5001/api/chess/analyze_position"
        
        print(f"Testing API endpoint: {url}")
        print(f"With FEN: {test_fen}")
        
        start_time = time.time()
        response = requests.post(
            url,
            json={"fen": test_fen},
            timeout=10
        )
        end_time = time.time()
        
        if response.status_code != 200:
            print(f"❌ API returned status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        data = response.json()
        
        if "lines" not in data:
            print("❌ API response missing 'lines' field")
            return False
        
        lines = data["lines"]
        if not isinstance(lines, list):
            print(f"❌ API lines field is not a list: {type(lines)}")
            return False
        
        if len(lines) != 3:
            print(f"❌ Expected 3 analysis lines from API, got {len(lines)}")
            return False
        
        print(f"✅ API analysis completed in {end_time - start_time:.2f}s")
        for i, line in enumerate(lines):
            print(f"   Line {i+1}: {line.get('pv_san', 'N/A')} (Eval: {line.get('evaluation_string', 'N/A')})")
        print(f"   Commentary: {data.get('commentary', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint error: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Starting Stockfish 3-Line Analysis Tests")
    print("=" * 60)
    
    tests = [
        ("Stockfish Initialization", test_stockfish_initialization),
        ("StockfishEngine Service", test_stockfish_service),
        ("Legacy Analyzer", test_legacy_analyzer),
        ("Service Analyzer Function", test_service_analyzer),
        ("HTTP API Endpoint", test_api_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Stockfish is working correctly with 3 lines.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 