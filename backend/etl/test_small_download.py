#!/usr/bin/env python3
"""
Small Scale TWIC Download Test
=============================

This script tests the complete TWIC downloader pipeline with just a few archives
to validate everything works before doing the full expansion.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twic_downloader import TWICDownloader, TWICArchive
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_small_download():
    """Test downloading and processing a small set of TWIC archives"""
    print("🧪 Small Scale TWIC Download Test")
    print("=" * 50)
    
    # Initialize downloader
    downloader = TWICDownloader()
    
    # Create test archives for a small range
    test_archives = [
        TWICArchive(
            number=920,
            url="https://theweekinchess.com/zips/twic920g.zip",
            filename="twic920g.zip"
        ),
        TWICArchive(
            number=921,
            url="https://theweekinchess.com/zips/twic921g.zip",
            filename="twic921g.zip"
        ),
        TWICArchive(
            number=922,
            url="https://theweekinchess.com/zips/twic922g.zip",
            filename="twic922g.zip"
        )
    ]
    
    print(f"📋 Testing with {len(test_archives)} archives:")
    for archive in test_archives:
        print(f"  • TWIC #{archive.number}: {archive.url}")
    
    try:
        # Step 1: Test downloading
        print("\n📥 Step 1: Testing download...")
        successful_downloads = downloader.download_all_archives(test_archives, max_workers=2)
        print(f"✅ Downloaded {len(successful_downloads)}/{len(test_archives)} archives")
        
        if not successful_downloads:
            print("❌ No archives downloaded successfully")
            return False
        
        # Step 2: Test processing
        print("\n⚙️ Step 2: Testing processing and combination...")
        combined_file = downloader.process_all_archives(successful_downloads)
        print(f"✅ Created combined file: {combined_file}")
        
        # Step 3: Analyze results
        print(f"\n📊 Step 3: Analyzing results...")
        if combined_file.exists():
            file_size = combined_file.stat().st_size
            print(f"📁 Combined file size: {file_size:,} bytes")
            
            # Count lines in the file to estimate games
            with open(combined_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = sum(1 for _ in f)
            print(f"📄 Total lines in combined file: {lines:,}")
            
            # Show sample of the file
            print(f"\n📖 Sample from combined file:")
            with open(combined_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= 20:  # Show first 20 lines
                        break
                    print(f"  {i+1:2}: {line.rstrip()}")
            
            print(f"\n✅ Small scale test completed successfully!")
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
    """Run the small scale test"""
    success = test_small_download()
    
    if success:
        print(f"\n🎉 Small scale test PASSED!")
        print(f"💡 You're ready to run the full TWIC expansion:")
        print(f"   python run_twic_expansion.py --download-only")
        print(f"   # OR for complete expansion:")
        print(f"   python run_twic_expansion.py")
        sys.exit(0)
    else:
        print(f"\n⚠️ Small scale test FAILED!")
        print(f"Please fix issues before proceeding with full expansion.")
        sys.exit(1)

if __name__ == "__main__":
    main() 