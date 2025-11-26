#!/usr/bin/env python
"""
Import Lessons Script

This script imports chess lessons from document files (DOCX, PDF) into the database.
"""

import os
import sys
import logging
import argparse
import glob
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import repositories and services
from backend.database.lesson_repository import LessonRepository
from backend.services.extract_service import ExtractService

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Import chess lessons from document files")
    parser.add_argument(
        "files",
        nargs="+",
        help="Document files (DOCX, PDF) or glob patterns to import"
    )
    parser.add_argument(
        "--output-images-dir",
        type=str,
        help="Directory to save extracted images"
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

def process_lesson_document(file_path: str, extract_service: ExtractService, 
                          lesson_repository: LessonRepository) -> Dict[str, Any]:
    """Process a single lesson document."""
    # Extract content from document
    extracted_data = extract_service.extract_content(file_path)
    
    if not extracted_data:
        logger.error(f"Failed to extract content from document: {file_path}")
        return {
            "success": False,
            "message": "Extraction failed",
            "file": file_path,
            "chunks_stored": 0
        }
    
    # Process lessons and create chunks
    book_title = extracted_data.get("book_title", "Unknown Book")
    lessons = extracted_data.get("lessons", [])
    
    chunks = []
    for lesson in lessons:
        lesson_number = lesson.get("lesson_number", 0)
        lesson_title = lesson.get("title", f"Lesson {lesson_number}")
        
        for content_item in lesson.get("content", []):
            # Create chunk
            chunk = {
                "book": book_title,
                "lessonNumber": lesson_number,
                "lessonTitle": lesson_title,
                "content": content_item.get("text", ""),
                "chunkType": content_item.get("type", "explanation"),
                "source": os.path.basename(file_path),
                "sourceType": file_path.split(".")[-1].lower()
            }
            
            # Add diagram reference if it exists
            if "image" in content_item:
                chunk["diagramReference"] = content_item["image"]
            
            if "diagram_number_reference" in content_item:
                chunk["diagramNumber"] = content_item["diagram_number_reference"]
            
            chunks.append(chunk)
    
    # Store chunks
    chunk_count, _ = lesson_repository.store_chunks(chunks)
    
    return {
        "success": True,
        "message": "Processing successful",
        "file": file_path,
        "book_title": book_title,
        "lesson_count": len(lessons),
        "chunks_stored": chunk_count
    }

def main():
    """Run the import process."""
    args = parse_args()
    
    # Get files from patterns
    files = get_files_from_patterns(args.files)
    
    if not files:
        logger.error("No files found matching the provided patterns")
        return 1
    
    # Filter out non-supported file types
    supported_extensions = (".docx", ".pdf")
    files = [f for f in files if os.path.splitext(f)[1].lower() in supported_extensions]
    
    if not files:
        logger.error("No supported document files found (must be .docx or .pdf)")
        return 1
    
    logger.info(f"Found {len(files)} document files to import")
    
    # Create repository and service
    extract_service = ExtractService(output_images_dir=args.output_images_dir)
    lesson_repository = LessonRepository()
    
    # Check repository health
    if not lesson_repository.healthcheck():
        logger.error("Lesson repository health check failed")
        return 1
    
    # Check extract service health
    if not extract_service.healthcheck():
        logger.error("Extract service health check failed")
        return 1
    
    # Process each file
    total_lessons = 0
    total_chunks = 0
    successful_files = 0
    
    for file_path in files:
        logger.info(f"Processing document: {file_path}")
        
        try:
            result = process_lesson_document(file_path, extract_service, lesson_repository)
            
            if result["success"]:
                successful_files += 1
                total_lessons += result.get("lesson_count", 0)
                total_chunks += result.get("chunks_stored", 0)
                logger.info(f"File {file_path}: Processed {result.get('lesson_count', 0)} lessons, stored {result.get('chunks_stored', 0)} chunks")
            else:
                logger.error(f"Failed to process {file_path}: {result.get('message', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    # Report results
    logger.info(f"Import complete: Successfully processed {successful_files}/{len(files)} files")
    logger.info(f"Imported {total_lessons} lessons with {total_chunks} chunks")
    
    return 0 if successful_files > 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 