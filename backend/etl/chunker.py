import json
import uuid
import re
import os
from typing import List, Dict, Any

from . import config

def sanitize_filename_for_id(name: str) -> str:
    """Sanitizes a string to be part of a chunk ID."""
    name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)  # Allow alphanumeric, underscore, hyphen
    return name[:50]  # Limit length for ID part

def split_into_sentences(text: str) -> List[str]:
    """Basic sentence splitter. A more robust NLP library would be better."""
    if not text:
        return []
    # Simplified regex for splitting sentences, handles basic cases.
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!|\n)\s', text)
    return [s.strip() for s in sentences if s.strip()]

def create_chunks_from_lesson(lesson_data: Dict[str, Any], book_title: str, language: str = "ru") -> List[Dict[str, Any]]:
    """
    Creates chunks from lesson data for vector storage.
    Enhanced to handle improved diagram associations.
    
    Args:
        lesson_data: Dictionary containing lesson data
        book_title: Title of the book/document
        language: Language code (default: ru for Russian)
    
    Returns:
        List of chunks ready for vector storage
    """
    chunks = []
    lesson_number_text = str(lesson_data.get("lesson_number", "N/A"))
    lesson_title = lesson_data.get("title", "Untitled Lesson")

    current_explanation_texts = []
    item_sequence = 0  # To help differentiate IDs if needed

    for content_item in lesson_data.get("content", []):
        item_sequence += 1
        item_type = content_item.get("type", "explanation")
        text = content_item.get("text", "")
        fen = content_item.get("fen")
        image = content_item.get("image")
        
        # Enhanced diagram association information
        diagram_number = content_item.get("diagram_number")
        association_confidence = content_item.get("association_confidence", 0.0)
        match_type = content_item.get("match_type", "unknown")

        task_type_heuristic = "general_task"  # Default if it's a task
        if item_type == "task" or item_type == "general_task":
            if fen:
                if "1 ход" in text.lower() or "one move" in text.lower() or "мат в 1" in text.lower():
                    task_type_heuristic = "mate_in_1"
                elif "2 хода" in text.lower() or "two moves" in text.lower() or "мат в 2" in text.lower():
                    task_type_heuristic = "mate_in_2"
                # Add more specific task types based on keywords

            # If there was pending explanation text, chunk it first
            if current_explanation_texts:
                expl_chunk_id = f"lesson{lesson_number_text}_explanation_{str(uuid.uuid4())[:6]}"
                chunks.append({
                    "id": expl_chunk_id,
                    "book_title": book_title,
                    "lesson_number": lesson_number_text,
                    "lesson_title": lesson_title,
                    "type": "explanation_group",
                    "language": language,
                    "text": "\n".join(current_explanation_texts)
                })
                current_explanation_texts = []

            base_id_part = f"lesson{lesson_number_text}_task"
            if image:
                img_name_part = sanitize_filename_for_id(os.path.splitext(image)[0])
                chunk_id = f"{base_id_part}_{img_name_part}"
            elif fen:
                chunk_id = f"{base_id_part}_fen_{str(uuid.uuid4())[:6]}"
            else:
                chunk_id = f"{base_id_part}_text_{item_sequence}_{str(uuid.uuid4())[:6]}"

            chunk = {
                "id": chunk_id,
                "book_title": book_title,
                "lesson_number": lesson_number_text,
                "lesson_title": lesson_title,
                "type": task_type_heuristic,
                "language": language,
                "text": text
            }
            
            # Add FEN if available
            if fen: 
                chunk["fen"] = fen
                
            # Add image with enhanced metadata
            if image: 
                chunk["image"] = image  # image filename, not path
                if diagram_number:
                    chunk["diagram_number"] = diagram_number
                if association_confidence > 0:
                    chunk["association_confidence"] = association_confidence
                    chunk["match_type"] = match_type
                    
                    # Add confidence-based quality indicator
                    if association_confidence >= 0.9:
                        chunk["diagram_quality"] = "high"
                    elif association_confidence >= 0.6:
                        chunk["diagram_quality"] = "medium"
                    else:
                        chunk["diagram_quality"] = "low"
            
            chunks.append(chunk)
        elif item_type == "explanation":
            current_explanation_texts.append(text)

    # Add any remaining explanation text as a final chunk for the lesson
    if current_explanation_texts:
        final_expl_chunk_id = f"lesson{lesson_number_text}_explanation_final_{str(uuid.uuid4())[:6]}"
        chunks.append({
            "id": final_expl_chunk_id,
            "book_title": book_title,
            "lesson_number": lesson_number_text,
            "lesson_title": lesson_title,
            "type": "explanation_group",
            "language": language,
            "text": "\n".join(current_explanation_texts)
        })

    return chunks

def chunk_processed_data(processed_data: Dict[str, Any], language_code: str = None) -> List[Dict[str, Any]]:
    """
    Chunks processed data into manageable sizes for vector database storage.
    
    Args:
        processed_data: Dictionary containing processed data with FEN
        language_code: Language code (default from config if None)
    
    Returns:
        List of chunk dictionaries for vector storage
    """
    if language_code is None:
        language_code = config.DEFAULT_LANGUAGE
        
    all_chunks = []
    book_title = processed_data.get("book_title", "Unknown Book")

    for lesson in processed_data.get("lessons", []):
        lesson_chunks = create_chunks_from_lesson(lesson, book_title, language=language_code)
        all_chunks.extend(lesson_chunks)
    
    print(f"Generated {len(all_chunks)} chunks from {len(processed_data.get('lessons', []))} lessons")
    return all_chunks

if __name__ == "__main__":
    # Test code for direct execution
    print("Chunker Module Test")
    print("------------------")
    
    # Create a simple test structure
    test_data = {
        "book_title": "Test Chess Book",
        "lessons": [
            {
                "lesson_number": 1,
                "title": "Introduction to Chess",
                "content": [
                    {
                        "type": "explanation",
                        "text": "Chess is a strategic board game played between two opponents."
                    },
                    {
                        "type": "task",
                        "text": "Diagram 1: Find the best move.",
                        "image": "diagram_test.png",
                        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
                    }
                ]
            }
        ]
    }
    
    # Process the test data
    chunks = chunk_processed_data(test_data)
    
    # Print the result
    print(f"Generated {len(chunks)} chunks")
    for chunk in chunks:
        print(f"\nChunk ID: {chunk['id']}")
        print(f"Type: {chunk['type']}")
        if "fen" in chunk:
            print(f"FEN: {chunk['fen']}")
        print(f"Text: {chunk['text'][:50]}..." if len(chunk['text']) > 50 else f"Text: {chunk['text']}") 