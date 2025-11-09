#!/usr/bin/env python
"""
Import Openings Script

This script imports chess openings data from JSON files into the database.
"""

import os
import sys
import logging
import argparse
import glob
import json
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import repositories
from backend.database.opening_repository import OpeningRepository

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Import chess openings from JSON files")
    parser.add_argument(
        "files",
        nargs="+",
        help="JSON files or glob patterns to import"
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

def validate_opening_data(data: List[Dict[str, Any]]) -> bool:
    """Validate openings data structure."""
    if not isinstance(data, list):
        logger.error("Opening data is not a list")
        return False
    
    for i, opening in enumerate(data):
        if not isinstance(opening, dict):
            logger.error(f"Opening at index {i} is not a dictionary")
            return False
        
        # Check required fields
        required_fields = ["eco", "name", "moves"]
        for field in required_fields:
            if field not in opening:
                logger.error(f"Opening at index {i} is missing required field: {field}")
                return False
    
    return True

def main():
    """Run the import process."""
    args = parse_args()
    
    # Get files from patterns
    files = get_files_from_patterns(args.files)
    
    if not files:
        logger.error("No files found matching the provided patterns")
        return 1
    
    logger.info(f"Found {len(files)} JSON files to import")
    
    # Create repository
    repo = OpeningRepository()
    
    # Check repository health
    if not repo.healthcheck():
        logger.error("Opening repository health check failed")
        return 1
    
    # Process each file
    total_processed = 0
    total_success = 0
    
    for file_path in files:
        logger.info(f"Processing file: {file_path}")
        
        try:
            # Load the JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                openings_data = json.load(f)
            
            # Validate the data
            if not validate_opening_data(openings_data):
                logger.error(f"Invalid openings data in file: {file_path}")
                continue
            
            # Import the openings
            processed, success = repo.store_openings_from_file(file_path)
            
            total_processed += processed
            total_success += success
            
            logger.info(f"File {file_path}: Processed {processed} openings, successfully stored {success}")
        
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    # Report results
    logger.info(f"Import complete: Processed {total_processed} openings, successfully stored {total_success}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 