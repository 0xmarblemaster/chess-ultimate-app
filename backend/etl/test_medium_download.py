#!/usr/bin/env python3
"""
Medium Scale TWIC Download Test
==============================

This script tests downloading a medium range of TWIC archives (e.g., 50-100)
to validate performance and identify any issues before the full expansion.
"""

import sys
import os
from pathlib import Path
import argparse

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twic_downloader import TWICDownloader, TWICArchive
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_medium_download(start_twic: int = 1000, count: int = 50):
    """Test downloading and processing a medium range of TWIC archives"""
    print(f"🧪 Medium Scale TWIC Download Test")
    print(f"📊 Range: TWIC #{start_twic} to #{start_twic + count - 1} ({count} archives)")
    print("=" * 70)
    
    # Initialize downloader
    downloader = TWICDownloader()
    
    # Create test archives for the range
    test_archives = []
    for i in range(count):
        twic_num = start_twic + i
        archive = TWICArchive(
            number=twic_num,
            url=f"https://theweekinchess.com/zips/twic{twic_num}g.zip",
            filename=f"twic{twic_num}g.zip"
        )
        test_archives.append(archive)
    
    print(f"📋 Will attempt to download {len(test_archives)} archives")
    print(f"⚠️  Note: Some archives may not exist - that's expected")
    
    try:
        # Step 1: Test downloading
        print(f"\n📥 Step 1: Testing download...")
        successful_downloads = downloader.download_all_archives(test_archives, max_workers=4)
        print(f"✅ Downloaded {len(successful_downloads)}/{len(test_archives)} archives")
        
        if not successful_downloads:
            print("❌ No archives downloaded successfully")
            return False
        
        # Show which ones succeeded
        print(f"\n📊 Successfully downloaded archives:")
        for archive in successful_downloads:
            print(f"  ✅ TWIC #{archive.number}")
        
        # Step 2: Test processing
        print(f"\n⚙️ Step 2: Testing processing and combination...")
        combined_file = downloader.process_all_archives(successful_downloads)
        print(f"✅ Created combined file: {combined_file}")
        
        # Step 3: Analyze results
        print(f"\n📊 Step 3: Analyzing results...")
        if combined_file.exists():
            file_size = combined_file.stat().st_size
            print(f"📁 Combined file size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
            
            # Get stats from the state
            if downloader.state.get('combined_files'):
                latest_stats = downloader.state['combined_files'][-1]
                total_games = latest_stats.get('game_count', 0)
                print(f"🎲 Total unique games: {total_games:,}")
                print(f"📅 Source archives: {len(latest_stats.get('source_archives', []))}")
            
            print(f"\n✅ Medium scale test completed successfully!")
            print(f"📍 Your combined file is ready at: {combined_file}")
            
            return True
        else:
            print("❌ Combined file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.error(f"Test failed with error: {e}")
        return False

def main():
    """Run the medium scale test with command line options"""
    parser = argparse.ArgumentParser(description="Medium scale TWIC download test")
    parser.add_argument('--start', type=int, default=1000, help='Starting TWIC number (default: 1000)')
    parser.add_argument('--count', type=int, default=50, help='Number of archives to test (default: 50)')
    
    args = parser.parse_args()
    
    success = test_medium_download(start_twic=args.start, count=args.count)
    
    if success:
        print(f"\n🎉 Medium scale test PASSED!")
        print(f"💡 You're ready for the full TWIC expansion:")
        print(f"   python run_twic_expansion.py --download-only")
        sys.exit(0)
    else:
        print(f"\n⚠️ Medium scale test had issues.")
        print(f"Consider investigating before full expansion.")
        sys.exit(1)

if __name__ == "__main__":
    main() 