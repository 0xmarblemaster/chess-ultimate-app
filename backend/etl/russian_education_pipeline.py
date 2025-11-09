#!/usr/bin/env python3
"""
Russian Chess Education Material ETL Pipeline

Enhanced pipeline for processing Russian chess education books with:
- Advanced chess diagram processing
- FEN conversion with fallback strategies
- Intelligent content chunking
- Progressive difficulty assessment
- Batch processing capabilities
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

# Core services
from services.extract_service import ExtractService
from services.fen_converter_service import FENConverterService
from database.lesson_repository import LessonRepository
from etl.fen_converter import image_to_fen, process_extracted_data_for_fen
from etl.chunker import create_chunks_from_lesson

# Import existing configuration
from etl import config

logger = logging.getLogger(__name__)

@dataclass
class ProcessingProgress:
    """Track processing progress for resumability"""
    total_files: int = 0
    processed_files: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    total_chunks: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class RussianEducationPipeline:
    """
    Specialized ETL pipeline for Russian chess educational content
    """
    
    def __init__(self, 
                 input_dir: str = None,
                 output_dir: str = None,
                 enable_translation: bool = False,
                 batch_size: int = 10):
        """
        Initialize the Russian Education Pipeline
        
        Args:
            input_dir: Directory containing Russian educational materials
            output_dir: Directory for processed outputs
            enable_translation: Whether to enable translation to other languages
            batch_size: Number of documents to process in parallel
        """
        self.input_dir = Path(input_dir) if input_dir else Path(config.INPUT_DIR) / "russian_education"
        self.output_dir = Path(output_dir) if output_dir else Path(config.OUTPUT_DIR) / "russian_education"
        self.enable_translation = enable_translation
        self.batch_size = batch_size
        
        # Ensure directories exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "processed").mkdir(exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
        (self.output_dir / "chunks").mkdir(exist_ok=True)
        (self.output_dir / "progress").mkdir(exist_ok=True)
        
        # Initialize services
        self.extract_service = ExtractService(output_images_dir=str(self.output_dir / "images"))
        self.fen_service = FENConverterService()
        self.lesson_repository = LessonRepository()
        
        # Russian chess terminology mapping
        self.russian_terminology = {
            # Pieces
            "король": "king", "ладья": "rook", "слон": "bishop", 
            "ферзь": "queen", "конь": "knight", "пешка": "pawn",
            
            # Actions
            "ход": "move", "шах": "check", "мат": "checkmate", 
            "пат": "stalemate", "рокировка": "castling",
            
            # Tactical themes
            "вилка": "fork", "связка": "pin", "двойной удар": "double attack",
            "отвлечение": "deflection", "завлечение": "decoy",
            "устранение защиты": "removal of defender",
            "перегрузка": "overloading", "блокировка": "blockade",
            
            # Strategic concepts
            "центр": "center", "фланг": "flank", "инициатива": "initiative",
            "слабое поле": "weak square", "пешечная структура": "pawn structure",
            "активность фигур": "piece activity",
            
            # Educational terms
            "урок": "lesson", "задача": "problem", "упражнение": "exercise",
            "диаграмма": "diagram", "позиция": "position", "анализ": "analysis"
        }
        
        # Progress tracking
        self.progress = ProcessingProgress()
        
    def detect_russian_content_type(self, text: str) -> Dict[str, Any]:
        """
        Analyze Russian text to determine content type and difficulty
        
        Args:
            text: Russian text to analyze
            
        Returns:
            Dictionary with content type analysis
        """
        analysis = {
            "content_type": "explanation",
            "difficulty_level": "beginner",
            "tactical_themes": [],
            "contains_diagram": False,
            "estimated_reading_time": 0,
            "language_confidence": 0.0
        }
        
        text_lower = text.lower()
        
        # Check for Russian content confidence
        cyrillic_chars = len(re.findall(r'[а-яё]', text_lower))
        total_chars = len(re.findall(r'[а-яёa-z]', text_lower))
        analysis["language_confidence"] = cyrillic_chars / max(total_chars, 1)
        
        # Detect content type
        if any(keyword in text_lower for keyword in ["задача", "найдите", "сыграйте", "белые играют"]):
            analysis["content_type"] = "task"
        elif any(keyword in text_lower for keyword in ["диаграмма", "позиция", "на доске"]):
            analysis["contains_diagram"] = True
            
        # Detect difficulty level
        difficulty_indicators = {
            "beginner": ["основы", "начало", "простой", "легкий", "первые шаги"],
            "intermediate": ["средний", "продвинутый", "сложный", "комбинация"],
            "advanced": ["мастерский", "гроссмейстерский", "глубокий анализ", "тонкости"]
        }
        
        for level, indicators in difficulty_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                analysis["difficulty_level"] = level
                break
                
        # Detect tactical themes
        for russian_term, english_term in self.russian_terminology.items():
            if russian_term in text_lower:
                analysis["tactical_themes"].append(english_term)
                
        # Estimate reading time (words per minute for Russian)
        word_count = len(text.split())
        analysis["estimated_reading_time"] = max(1, word_count // 200)  # 200 WPM average
        
        return analysis
        
    def enhanced_diagram_processing(self, image_path: str, context_text: str = "") -> Dict[str, Any]:
        """
        Enhanced chess diagram processing with multiple strategies
        
        Args:
            image_path: Path to the chess diagram image
            context_text: Surrounding text for context
            
        Returns:
            Dictionary with FEN and analysis results
        """
        result = {
            "fen": None,
            "success": False,
            "method_used": None,
            "confidence": 0.0,
            "position_analysis": {},
            "errors": []
        }
        
        try:
            # Strategy 1: Use the neural network FEN converter
            image_filename = Path(image_path).name
            output_dir = str(Path(image_path).parent)
            
            fen, used_fallback = image_to_fen(
                image_filename=image_filename,
                output_images_dir=output_dir,
                use_fallback=True,
                task_id=f"russian_edu_{uuid.uuid4().hex[:8]}"
            )
            
            if fen and not used_fallback:
                result["fen"] = fen
                result["success"] = True
                result["method_used"] = "neural_network"
                result["confidence"] = 0.9
            elif fen and used_fallback:
                result["fen"] = fen
                result["success"] = True
                result["method_used"] = "fallback"
                result["confidence"] = 0.3
            else:
                result["errors"].append("FEN conversion failed")
                
            # Strategy 2: Analyze context for position hints
            if context_text and result["fen"]:
                context_analysis = self.detect_russian_content_type(context_text)
                result["position_analysis"] = {
                    "tactical_themes": context_analysis["tactical_themes"],
                    "difficulty": context_analysis["difficulty_level"],
                    "contains_solution_hint": any(hint in context_text.lower() 
                                                for hint in ["решение", "ответ", "лучший ход"])
                }
                
        except Exception as e:
            result["errors"].append(f"Processing error: {str(e)}")
            logger.error(f"Enhanced diagram processing failed for {image_path}: {e}")
            
        return result
        
    def process_single_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a single Russian educational document
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"Processing Russian educational document: {file_path.name}")
        
        result = {
            "file_path": str(file_path),
            "success": False,
            "extracted_data": None,
            "chunks": [],
            "fen_conversions": 0,
            "errors": []
        }
        
        try:
            # Step 1: Extract content from document
            extracted_data = self.extract_service.extract_content(str(file_path))
            
            if not extracted_data or not extracted_data.get("lessons"):
                result["errors"].append("No lessons extracted from document")
                return result
                
            result["extracted_data"] = extracted_data
            
            # Step 2: Enhanced processing for Russian content
            for lesson in extracted_data["lessons"]:
                # Analyze lesson content
                lesson_text = " ".join([item.get("text", "") for item in lesson.get("content", [])])
                content_analysis = self.detect_russian_content_type(lesson_text)
                
                # Add analysis to lesson metadata
                lesson["content_analysis"] = content_analysis
                lesson["language"] = "ru"
                
                # Step 3: Process diagrams with enhanced methods
                for content_item in lesson.get("content", []):
                    if content_item.get("image"):
                        image_path = self.output_dir / "images" / content_item["image"]
                        if image_path.exists():
                            diagram_result = self.enhanced_diagram_processing(
                                str(image_path), 
                                content_item.get("text", "")
                            )
                            
                            if diagram_result["success"]:
                                content_item["fen"] = diagram_result["fen"]
                                content_item["fen_analysis"] = diagram_result
                                result["fen_conversions"] += 1
                            else:
                                result["errors"].extend(diagram_result["errors"])
                                
            # Step 4: Create intelligent chunks
            all_chunks = []
            book_title = extracted_data.get("book_title", file_path.stem)
            
            for lesson in extracted_data["lessons"]:
                lesson_chunks = create_chunks_from_lesson(lesson, book_title, language="ru")
                
                # Enhance chunks with Russian-specific metadata
                for chunk in lesson_chunks:
                    if "content_analysis" in lesson:
                        chunk.update({
                            "difficulty_level": lesson["content_analysis"]["difficulty_level"],
                            "tactical_themes": lesson["content_analysis"]["tactical_themes"],
                            "estimated_reading_time": lesson["content_analysis"]["estimated_reading_time"],
                            "source_file": file_path.name,
                            "processing_timestamp": datetime.now().isoformat()
                        })
                        
                all_chunks.extend(lesson_chunks)
                
            result["chunks"] = all_chunks
            result["success"] = True
            
            # Save processed results
            output_file = self.output_dir / "processed" / f"{file_path.stem}_processed.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "extracted_data": extracted_data,
                    "chunks": all_chunks,
                    "processing_metadata": {
                        "file_path": str(file_path),
                        "fen_conversions": result["fen_conversions"],
                        "total_chunks": len(all_chunks),
                        "processing_time": datetime.now().isoformat()
                    }
                }, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Successfully processed {file_path.name}: {len(all_chunks)} chunks, {result['fen_conversions']} FEN conversions")
            
        except Exception as e:
            error_msg = f"Error processing {file_path.name}: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
            
        return result
        
    def batch_process_documents(self, file_paths: List[Path]) -> Dict[str, Any]:
        """
        Process multiple documents in batches with progress tracking
        
        Args:
            file_paths: List of document paths to process
            
        Returns:
            Batch processing results
        """
        self.progress.total_files = len(file_paths)
        batch_results = {
            "total_files": len(file_paths),
            "successful_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "total_fen_conversions": 0,
            "results": [],
            "errors": []
        }
        
        # Process in batches
        for i in range(0, len(file_paths), self.batch_size):
            batch = file_paths[i:i + self.batch_size]
            logger.info(f"Processing batch {i//self.batch_size + 1}: {len(batch)} files")
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=min(self.batch_size, 4)) as executor:
                batch_futures = [executor.submit(self.process_single_document, file_path) 
                               for file_path in batch]
                
                for future in batch_futures:
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per file
                        batch_results["results"].append(result)
                        
                        if result["success"]:
                            batch_results["successful_files"] += 1
                            batch_results["total_chunks"] += len(result["chunks"])
                            batch_results["total_fen_conversions"] += result["fen_conversions"]
                        else:
                            batch_results["failed_files"] += 1
                            batch_results["errors"].extend(result["errors"])
                            
                        self.progress.processed_files += 1
                        
                    except Exception as e:
                        error_msg = f"Batch processing error: {str(e)}"
                        batch_results["errors"].append(error_msg)
                        batch_results["failed_files"] += 1
                        logger.error(error_msg)
                        
            # Save progress after each batch
            self.save_progress()
            
        return batch_results
        
    def save_progress(self):
        """Save current processing progress"""
        progress_file = self.output_dir / "progress" / f"progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                "progress": {
                    "total_files": self.progress.total_files,
                    "processed_files": self.progress.processed_files,
                    "successful_conversions": self.progress.successful_conversions,
                    "failed_conversions": self.progress.failed_conversions,
                    "total_chunks": self.progress.total_chunks,
                    "errors": self.progress.errors
                },
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
            
    def process_directory(self, resume_from_progress: bool = False) -> Dict[str, Any]:
        """
        Process all documents in the input directory
        
        Args:
            resume_from_progress: Whether to resume from previous progress
            
        Returns:
            Complete processing results
        """
        logger.info(f"Starting Russian education content processing from: {self.input_dir}")
        
        # Find all supported documents
        supported_extensions = ['.pdf', '.docx', '.doc']
        file_paths = []
        
        for ext in supported_extensions:
            file_paths.extend(self.input_dir.glob(f"**/*{ext}"))
            
        if not file_paths:
            logger.warning(f"No supported documents found in {self.input_dir}")
            return {"error": "No documents found"}
            
        logger.info(f"Found {len(file_paths)} documents to process")
        
        # Process all documents
        results = self.batch_process_documents(file_paths)
        
        # Store all chunks in the vector database
        if results["total_chunks"] > 0:
            try:
                all_chunks = []
                for result in results["results"]:
                    if result["success"]:
                        all_chunks.extend(result["chunks"])
                        
                # Store in batches to avoid memory issues
                batch_size = 100
                stored_count = 0
                
                for i in range(0, len(all_chunks), batch_size):
                    chunk_batch = all_chunks[i:i + batch_size]
                    stored_ids = []
                    
                    for chunk in chunk_batch:
                        chunk_id = self.lesson_repository.store_chunk(chunk)
                        if chunk_id:
                            stored_ids.append(chunk_id)
                            
                    stored_count += len(stored_ids)
                    logger.info(f"Stored batch {i//batch_size + 1}: {len(stored_ids)} chunks")
                    
                results["stored_chunks"] = stored_count
                logger.info(f"Successfully stored {stored_count} chunks in vector database")
                
            except Exception as e:
                error_msg = f"Error storing chunks in database: {str(e)}"
                results["storage_error"] = error_msg
                logger.error(error_msg)
                
        # Save final results
        final_results_file = self.output_dir / f"final_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(final_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info("Russian education content processing complete!")
        logger.info(f"Results: {results['successful_files']} successful, {results['failed_files']} failed")
        logger.info(f"Generated {results['total_chunks']} chunks with {results['total_fen_conversions']} FEN conversions")
        
        return results

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Russian Chess Education ETL Pipeline")
    parser.add_argument("--input-dir", help="Directory containing Russian educational materials")
    parser.add_argument("--output-dir", help="Directory for processed outputs")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size for parallel processing")
    parser.add_argument("--enable-translation", action="store_true", help="Enable translation features")
    parser.add_argument("--resume", action="store_true", help="Resume from previous progress")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = RussianEducationPipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        enable_translation=args.enable_translation,
        batch_size=args.batch_size
    )
    
    # Process documents
    results = pipeline.process_directory(resume_from_progress=args.resume)
    
    # Print summary
    print("\n" + "="*50)
    print("RUSSIAN EDUCATION PROCESSING SUMMARY")
    print("="*50)
    print(f"Total files processed: {results.get('total_files', 0)}")
    print(f"Successful: {results.get('successful_files', 0)}")
    print(f"Failed: {results.get('failed_files', 0)}")
    print(f"Total chunks generated: {results.get('total_chunks', 0)}")
    print(f"FEN conversions: {results.get('total_fen_conversions', 0)}")
    if results.get('stored_chunks'):
        print(f"Chunks stored in database: {results['stored_chunks']}")
    print("="*50)

if __name__ == "__main__":
    main() 