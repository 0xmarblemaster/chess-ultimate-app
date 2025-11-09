#!/usr/bin/env python3
"""
TWIC Database Expansion Runner
=============================

This script orchestrates the complete TWIC database expansion process:
1. Downloads all TWIC archives
2. Processes and combines them chronologically  
3. Loads the combined dataset into Weaviate

Usage:
    python run_twic_expansion.py [options]

Options:
    --download-only     Only download and process, don't load to Weaviate
    --load-only         Only load existing combined file to Weaviate
    --start-twic N      Start from TWIC number N (default: 1)
    --end-twic N        End at TWIC number N (default: auto-detect)
    --max-workers N     Number of parallel downloads (default: 4)
    --combined-file     Path to existing combined file for load-only mode
"""

import argparse
import sys
import os
from pathlib import Path
import logging

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twic_downloader import TWICDownloader, main as download_main
try:
    from games_loader import load_pgn_games_to_weaviate, get_weaviate_client, create_chess_game_collection_if_not_exists
    import config as etl_config
except ImportError as e:
    print(f"Warning: Could not import games_loader: {e}")
    print("This may limit some functionality.")
    etl_config = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_combined_file_to_weaviate(combined_file_path: Path) -> int:
    """
    Load a combined TWIC PGN file into Weaviate
    
    Args:
        combined_file_path: Path to the combined PGN file
        
    Returns:
        Number of games loaded
    """
    if not combined_file_path.exists():
        raise FileNotFoundError(f"Combined file not found: {combined_file_path}")
    
    logger.info(f"Loading combined TWIC file into Weaviate: {combined_file_path}")
    
    # Check if we have etl_config
    if etl_config is None:
        raise Exception("ETL configuration not available. Cannot proceed with Weaviate loading.")
    
    # Temporarily modify config to point to our combined file
    original_pgn_dir = etl_config.PGN_DATA_DIR
    temp_dir = combined_file_path.parent
    etl_config.PGN_DATA_DIR = str(temp_dir)
    
    try:
        # Ensure Weaviate connection and schema
        client = get_weaviate_client()
        if not client:
            raise Exception("Could not connect to Weaviate")
        
        create_chess_game_collection_if_not_exists(client)
        
        # Load the combined file
        # We need to temporarily move/copy the file to match expected naming
        temp_pgn_file = temp_dir / "twic_combined.pgn"
        if temp_pgn_file != combined_file_path:
            import shutil
            shutil.copy2(combined_file_path, temp_pgn_file)
        
        try:
            games_loaded = load_pgn_games_to_weaviate()
            logger.info(f"Successfully loaded {games_loaded} games into Weaviate")
            return games_loaded
        finally:
            # Clean up temp file if we created it
            if temp_pgn_file != combined_file_path and temp_pgn_file.exists():
                temp_pgn_file.unlink()
        
    finally:
        # Restore original config
        etl_config.PGN_DATA_DIR = original_pgn_dir
        if 'client' in locals() and client:
            # client.close() removed - Weaviate client manages connections automatically

def run_complete_expansion(start_twic: int = 1, end_twic: int = None, max_workers: int = 4) -> Path:
    """
    Run the complete TWIC expansion process
    
    Args:
        start_twic: Starting TWIC number
        end_twic: Ending TWIC number (None for auto-detect)
        max_workers: Number of parallel downloads
        
    Returns:
        Path to the combined PGN file
    """
    downloader = TWICDownloader()
    
    # Step 1: Discover archives
    logger.info("🔍 Discovering TWIC archives...")
    all_archives = downloader.discover_archives()
    
    # Filter archives based on start_twic and end_twic
    if start_twic > 1 or end_twic is not None:
        filtered_archives = []
        for archive in all_archives:
            if archive.number >= start_twic:
                if end_twic is None or archive.number <= end_twic:
                    filtered_archives.append(archive)
        archives = filtered_archives
        logger.info(f"✅ Filtered to {len(archives)} archives (TWIC #{start_twic} to {end_twic or 'latest'})")
    else:
        archives = all_archives
        logger.info(f"✅ Discovered {len(archives)} archives")
    
    # Step 2: Download archives
    logger.info("📥 Downloading archives...")
    successful_downloads = downloader.download_all_archives(archives, max_workers=max_workers)
    logger.info(f"✅ Downloaded {len(successful_downloads)} archives")
    
    # Step 3: Process and combine
    logger.info("⚙️ Processing and combining archives...")
    combined_file = downloader.process_all_archives(successful_downloads)
    logger.info(f"✅ Created combined file: {combined_file}")
    
    return combined_file

def get_latest_combined_file() -> Path:
    """Find the most recent combined TWIC file"""
    if etl_config is None:
        raise Exception("ETL configuration not available. Cannot locate combined files.")
        
    data_dir = Path(etl_config.PGN_DATA_DIR)
    combined_dir = data_dir / "twic_combined"
    
    if not combined_dir.exists():
        raise FileNotFoundError("No combined TWIC files found")
    
    combined_files = list(combined_dir.glob("twic_complete_*.pgn"))
    if not combined_files:
        raise FileNotFoundError("No combined TWIC files found")
    
    # Return the most recent file
    return max(combined_files, key=lambda f: f.stat().st_mtime)

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="TWIC Database Expansion Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Complete expansion (download + load)
  python run_twic_expansion.py
  
  # Download only, don't load to Weaviate
  python run_twic_expansion.py --download-only
  
  # Load existing combined file
  python run_twic_expansion.py --load-only
  
  # Download specific range
  python run_twic_expansion.py --start-twic 1000 --end-twic 1500
  
  # Load specific combined file
  python run_twic_expansion.py --load-only --combined-file /path/to/file.pgn
        """
    )
    
    parser.add_argument(
        '--download-only', 
        action='store_true',
        help='Only download and process, do not load to Weaviate'
    )
    
    parser.add_argument(
        '--load-only', 
        action='store_true',
        help='Only load existing combined file to Weaviate'
    )
    
    parser.add_argument(
        '--start-twic', 
        type=int, 
        default=1,
        help='Starting TWIC number (default: 1)'
    )
    
    parser.add_argument(
        '--end-twic', 
        type=int, 
        default=None,
        help='Ending TWIC number (default: auto-detect latest)'
    )
    
    parser.add_argument(
        '--max-workers', 
        type=int, 
        default=4,
        help='Number of parallel downloads (default: 4)'
    )
    
    parser.add_argument(
        '--combined-file', 
        type=Path,
        help='Path to existing combined file for load-only mode'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.download_only and args.load_only:
        parser.error("Cannot specify both --download-only and --load-only")
    
    try:
        if args.load_only:
            # Load existing combined file
            if args.combined_file:
                combined_file = args.combined_file
            else:
                logger.info("Finding latest combined file...")
                combined_file = get_latest_combined_file()
            
            logger.info(f"Loading file: {combined_file}")
            games_loaded = load_combined_file_to_weaviate(combined_file)
            
            print(f"\n🎉 Load Complete!")
            print(f"📁 File loaded: {combined_file}")
            print(f"🎲 Games loaded: {games_loaded}")
            
        elif args.download_only:
            # Download and process only
            combined_file = run_complete_expansion(
                start_twic=args.start_twic,
                end_twic=args.end_twic,
                max_workers=args.max_workers
            )
            
            print(f"\n🎉 Download Complete!")
            print(f"📁 Combined file: {combined_file}")
            print(f"💡 To load into Weaviate, run:")
            print(f"   python run_twic_expansion.py --load-only --combined-file {combined_file}")
            
        else:
            # Complete process: download + load
            combined_file = run_complete_expansion(
                start_twic=args.start_twic,
                end_twic=args.end_twic,
                max_workers=args.max_workers
            )
            
            logger.info("🚀 Loading into Weaviate...")
            games_loaded = load_combined_file_to_weaviate(combined_file)
            
            print(f"\n🎉 Complete Expansion Finished!")
            print(f"📁 Combined file: {combined_file}")
            print(f"🎲 Games loaded: {games_loaded}")
            print(f"💡 Your Weaviate database now contains the complete TWIC archive!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        logger.info("Process interrupted, partial progress may be saved")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during expansion: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 