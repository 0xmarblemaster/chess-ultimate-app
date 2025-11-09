#!/usr/bin/env python3
"""
Simple TWIC Test Script
======================

This script tests the core TWIC functionality with a small, known set of archives
to validate that our approach works before running the full discovery.

Run this first to validate the system works correctly.
"""

import os
import sys
import requests
import tempfile
import zipfile
from pathlib import Path

def test_twic_urls():
    """Test a few known TWIC URLs to validate our approach"""
    print("🧪 Testing TWIC URL patterns...")
    
    # Test a few known recent TWIC numbers
    test_numbers = [920, 1000, 1200, 1400, 1500, 1560]
    
    patterns = [
        "https://theweekinchess.com/zips/twic{number}g.zip",
        "https://theweekinchess.com/zips/twic{number}.zip"
    ]
    
    # Set up proper browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    working_urls = []
    
    for number in test_numbers:
        print(f"\n📋 Testing TWIC #{number}...")
        
        for pattern in patterns:
            url = pattern.format(number=number)
            print(f"  🔗 Testing: {url}")
            
            try:
                response = requests.head(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    size = response.headers.get('content-length', 'Unknown')
                    print(f"  ✅ Found! Size: {size} bytes")
                    working_urls.append((number, url))
                    break
                else:
                    print(f"  ❌ Not found (Status: {response.status_code})")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    print(f"\n🎉 Found {len(working_urls)} working URLs:")
    for number, url in working_urls:
        print(f"  TWIC #{number}: {url}")
    
    return working_urls

def test_download_and_extract():
    """Test downloading and extracting a single TWIC archive"""
    print("\n📥 Testing download and extraction...")
    
    # Use a known working URL (TWIC 920)
    test_url = "https://theweekinchess.com/zips/twic920g.zip"
    print(f"🔗 Test URL: {test_url}")
    
    # Set up proper browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Download
        print("⬇️ Downloading...")
        try:
            response = requests.get(test_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            zip_file = temp_path / "twic920g.zip"
            with open(zip_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Downloaded {len(response.content)} bytes")
            
            # Extract
            print("📂 Extracting...")
            with zipfile.ZipFile(zip_file, 'r') as zf:
                files = zf.namelist()
                print(f"📋 Archive contains: {files}")
                
                # Find PGN file
                pgn_files = [f for f in files if f.endswith('.pgn')]
                if pgn_files:
                    pgn_file = pgn_files[0]
                    print(f"🎯 Found PGN file: {pgn_file}")
                    
                    # Extract and check first few lines
                    zf.extract(pgn_file, temp_path)
                    pgn_path = temp_path / pgn_file
                    
                    with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[:10]
                        print(f"📄 First few lines of PGN:")
                        for i, line in enumerate(lines, 1):
                            print(f"  {i:2}: {line.strip()}")
                    
                    print(f"✅ Successfully extracted and read PGN file!")
                    return True
                else:
                    print("❌ No PGN files found in archive")
                    return False
                    
        except Exception as e:
            print(f"❌ Error during download/extraction: {e}")
            return False

def test_pgn_parsing():
    """Test parsing PGN content with python-chess"""
    print("\n♟️ Testing PGN parsing...")
    
    try:
        import chess.pgn
        import io
        
        # Sample PGN content
        sample_pgn = '''[Event "Test Game"]
[Site "Test"]
[Date "2024.01.01"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0
'''
        
        print("📋 Testing with sample PGN...")
        game = chess.pgn.read_game(io.StringIO(sample_pgn))
        
        if game:
            print(f"✅ Successfully parsed game:")
            print(f"  Event: {game.headers.get('Event', 'Unknown')}")
            print(f"  White: {game.headers.get('White', 'Unknown')}")
            print(f"  Black: {game.headers.get('Black', 'Unknown')}")
            print(f"  Result: {game.headers.get('Result', 'Unknown')}")
            print(f"  Moves: {len(list(game.mainline_moves()))}")
            return True
        else:
            print("❌ Failed to parse PGN")
            return False
            
    except ImportError:
        print("❌ python-chess not available")
        return False
    except Exception as e:
        print(f"❌ Error parsing PGN: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 TWIC Simple Test Suite")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: URL patterns
    try:
        working_urls = test_twic_urls()
        if working_urls:
            print("✅ Test 1 PASSED: URL patterns work")
            success_count += 1
        else:
            print("❌ Test 1 FAILED: No working URLs found")
    except Exception as e:
        print(f"❌ Test 1 ERROR: {e}")
    
    # Test 2: Download and extraction
    try:
        if test_download_and_extract():
            print("✅ Test 2 PASSED: Download and extraction work")
            success_count += 1
        else:
            print("❌ Test 2 FAILED: Download/extraction failed")
    except Exception as e:
        print(f"❌ Test 2 ERROR: {e}")
    
    # Test 3: PGN parsing
    try:
        if test_pgn_parsing():
            print("✅ Test 3 PASSED: PGN parsing works")
            success_count += 1
        else:
            print("❌ Test 3 FAILED: PGN parsing failed")
    except Exception as e:
        print(f"❌ Test 3 ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Your system is ready for full TWIC expansion.")
        return True
    else:
        print("⚠️ Some tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 