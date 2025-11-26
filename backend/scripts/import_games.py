#!/usr/bin/env python
"""
Import Games Script

This script imports chess games from PGN files into the database.
"""

import os
import sys
import logging
import argparse
import glob
from typing import List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import repositories
from backend.database.game_repository import GameRepository

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Import chess games from PGN files")
    parser.add_argument(
        "files",
        nargs="+",
        help="PGN files or glob patterns to import"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="Script Import",
        help="Source label for imported games"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for importing games"
    )
    return parser.parse_args()

def get_files_from_patterns(patterns: List[str]) -> List[str]:
    """Expand glob patterns into file paths."""
    files = []
    for pattern in patterns:
        # If it's a direct file path, just add it
        if os.path.isfile(pattern):
            files.append(pattern)
        else:
            # Otherwise, treat as a glob pattern
            matching_files = glob.glob(pattern, recursive=True)
            files.extend([f for f in matching_files if os.path.isfile(f)])
    
    return files

def main():
    """Run the import process."""
    args = parse_args()
    
    # Get files from patterns
    files = get_files_from_patterns(args.files)
    
    if not files:
        logger.error("No files found matching the provided patterns")
        return 1
    
    logger.info(f"Found {len(files)} PGN files to import")
    
    # Create repository
    repo = GameRepository()
    
    # Check repository health
    if not repo.healthcheck():
        logger.error("Game repository health check failed")
        return 1
    
    # Process each file
    total_processed = 0
    total_success = 0
    
    for file_path in files:
        logger.info(f"Processing file: {file_path}")
        processed, success = repo.store_multiple_games(
            pgn_file_path=file_path,
            source=args.source,
            batch_size=args.batch_size
        )
        
        total_processed += processed
        total_success += success
        
        logger.info(f"File {file_path}: Processed {processed} games, successfully stored {success}")
    
    # Report results
    logger.info(f"Import complete: Processed {total_processed} games, successfully stored {total_success}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 