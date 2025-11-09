import subprocess
import os
import json
import chess  # for FEN validation
import sys
import time
from typing import Dict, Any, List, Optional, Tuple

from . import config

def fallback_fen_generator() -> str:
    """
    A simple fallback FEN generator that returns a standard starting position.
    This is used when the board-to-fen tool fails due to CUDA issues or other errors.
    
    Returns:
        Standard starting position FEN string
    """
    # Standard starting position in FEN notation
    return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

def image_to_fen(image_filename: str, output_images_dir: str, use_fallback: bool = False, task_id: str = None) -> Tuple[Optional[str], bool]:
    """
    Converts a chess board image to FEN notation using the board-to-fen tool.
    Validates the FEN using python-chess.
    
    Args:
        image_filename: Filename of the image (not the full path)
        output_images_dir: Directory where the image is stored
        use_fallback: Whether to use the fallback FEN generator if the board-to-fen tool fails
        task_id: Optional task identifier for better logging
    
    Returns:
        Tuple of (FEN string or None, used_fallback flag)
    """
    # Include task info in logs if available
    task_info = f" for task: {task_id}" if task_id else ""
    
    # Full image path for debugging
    full_image_path = os.path.join(output_images_dir, image_filename)
    print(f"[FEN] Converting image: {full_image_path}{task_info}")
    
    # Check if we should force using fallback (skip neural network completely)
    if config.FEN_FORCE_FALLBACK:
        print(f"[FEN] Using fallback (forced by config) for {image_filename}{task_info}")
        return fallback_fen_generator(), True
    
    # Check if FEN conversion is enabled
    if not config.FEN_CONVERTER_ENABLED:
        print(f"[FEN] Conversion is disabled in configuration{task_info}")
        if use_fallback and config.FEN_FALLBACK_ENABLED:
            return fallback_fen_generator(), True
        return None, False
        
    # Get the paths
    fen_tool_path = config.BOARD_TO_FEN_TOOL_PATH
    python_executable = config.BOARD_TO_FEN_PYTHON_EXECUTABLE
    
    # Verify file existence
    if not os.path.exists(full_image_path):
        print(f"[FEN] Error: Image not found at {full_image_path}{task_info}")
        if use_fallback and config.FEN_FALLBACK_ENABLED:
            return fallback_fen_generator(), True
        return None, False
    
    if not os.path.exists(fen_tool_path):
        print(f"[FEN] Error: Board-to-FEN tool not found at {fen_tool_path}{task_info}")
        if use_fallback and config.FEN_FALLBACK_ENABLED:
            return fallback_fen_generator(), True
        return None, False
    
    # Track if we've seen CUDA errors before
    cuda_error_keywords = ["ptxas", "nvlink", "No PTX", "CUDA", "GPU"]
    
    try:
        # Run the board-to-fen tool with a timeout to prevent hanging
        command = [python_executable, fen_tool_path, full_image_path]
        print(f"[FEN] Running command: {' '.join(command)}{task_info}")
        
        # Use a shorter timeout if we've seen CUDA errors already
        timeout = 30  # Default timeout
        
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise an exception on non-zero exit, we'll handle it
            timeout=timeout
        )
        
        # Check for specific CUDA-related errors in stderr
        if process.returncode != 0:
            stderr_output = process.stderr.lower() if process.stderr else ""
            
            # Check if this is a CUDA-related error
            has_cuda_error = any(keyword.lower() in stderr_output for keyword in cuda_error_keywords)
            
            if has_cuda_error:
                print(f"[FEN] CUDA-related error detected when running board-to-fen{task_info}. "
                      f"This might be due to missing CUDA components (ptxas/nvlink).")
                print(f"[FEN] Error details: {process.stderr}")
                if use_fallback and config.FEN_FALLBACK_ENABLED:
                    print(f"[FEN] Using fallback FEN generator{task_info}")
                    return fallback_fen_generator(), True
                return None, False
            
            # Other errors
            print(f"[FEN] Error running FEN converter for {full_image_path}{task_info}: Exit code {process.returncode}")
            print(f"[FEN] Stdout: {process.stdout}")
            print(f"[FEN] Stderr: {process.stderr}")
            if use_fallback and config.FEN_FALLBACK_ENABLED:
                return fallback_fen_generator(), True
            return None, False
        
        # Extract the FEN from the output
        raw_fen = process.stdout.strip()
        
        if not raw_fen:
            print(f"[FEN] Error: Empty output from FEN converter for {full_image_path}{task_info}")
            if use_fallback and config.FEN_FALLBACK_ENABLED:
                return fallback_fen_generator(), True
            return None, False
        
        # Try to convert to a full FEN if we only got the piece positions
        if " " not in raw_fen:  # If it's just the piece positions without move info
            try:
                # Add standard assumptions about turn, castling, etc.
                full_fen = f"{raw_fen} w KQkq - 0 1"
                # Validate with python-chess
                board = chess.Board(full_fen)
                print(f"[FEN] Successfully converted raw FEN to full FEN: {full_fen}{task_info}")
                return board.fen(), False
            except ValueError as e:
                print(f"[FEN] Error: Invalid raw FEN '{raw_fen}' couldn't be converted to full FEN{task_info}: {e}")
                # Fall through to try the original FEN
        
        # Validate the original FEN
        try:
            board = chess.Board(raw_fen)
            print(f"[FEN] Successfully validated FEN: {raw_fen}{task_info}")
            return board.fen(), False  # Return the validated FEN
        except ValueError as e:
            print(f"[FEN] Error: Invalid FEN '{raw_fen}' produced for {full_image_path}{task_info}. Validation error: {e}")
            if use_fallback and config.FEN_FALLBACK_ENABLED:
                return fallback_fen_generator(), True
            return None, False
            
    except subprocess.TimeoutExpired:
        print(f"[FEN] Error: FEN conversion for {full_image_path}{task_info} timed out.")
        if use_fallback and config.FEN_FALLBACK_ENABLED:
            return fallback_fen_generator(), True
        return None, False
    except Exception as e:
        print(f"[FEN] Failed to convert {full_image_path}{task_info}: {e}")
        import traceback
        traceback.print_exc()
        if use_fallback and config.FEN_FALLBACK_ENABLED:
            return fallback_fen_generator(), True
        return None, False

def process_extracted_data_for_fen(extracted_data: Dict[str, Any], output_images_dir: str) -> Dict[str, Any]:
    """
    Processes the extracted data by converting chess diagrams to FEN notation.
    
    Args:
        extracted_data: Dictionary containing extracted content from documents
        output_images_dir: Directory where the images are stored
    
    Returns:
        Updated dictionary with FEN notation added to tasks with images
    """
    if not isinstance(extracted_data, dict) or "lessons" not in extracted_data:
        print("[FEN] Warning: Invalid data structure passed to process_extracted_data_for_fen.")
        return extracted_data  # Return original data if structure is not as expected
    
    print(f"[FEN] Processing {len(extracted_data.get('lessons', []))} lessons for FEN conversion")
    
    # Track statistics
    total_tasks = 0
    tasks_with_images = 0
    successful_fen_conversions = 0
    fallback_fen_conversions = 0
    
    # Check if we should use the fallback generator
    # After a few CUDA failures, switch to using fallback for all remaining conversions
    use_fallback = config.FEN_FORCE_FALLBACK  # Start with force_fallback setting
    cuda_error_count = 0
    max_cuda_errors = config.FEN_FALLBACK_AFTER_ERRORS
    
    for lesson_idx, lesson in enumerate(extracted_data.get("lessons", [])):
        if not isinstance(lesson, dict) or "content" not in lesson:
            continue
            
        lesson_number = lesson.get("lesson_number", lesson_idx + 1)
        lesson_title = lesson.get("title", f"Lesson {lesson_number}")
        print(f"[FEN] Processing lesson {lesson_number}: {lesson_title}")
            
        for content_idx, content_item in enumerate(lesson.get("content", [])):
            if not isinstance(content_item, dict):
                continue
                
            if content_item.get("type") == "task" or content_item.get("type") == "general_task":
                total_tasks += 1
                
                # Generate a task ID for logging purposes
                diagram_ref = content_item.get("diagram_number_reference", "unknown")
                task_id = f"L{lesson_number}T{content_idx+1}(#{diagram_ref})"
                content_item["id"] = task_id  # Store the ID in the content item
                
                if "image" in content_item:
                    image_filename = content_item["image"]
                    tasks_with_images += 1
                    
                    if image_filename:
                        print(f"[FEN] Processing task {task_id} with image: {image_filename}")
                        # Add a small delay between processing to avoid overwhelming the GPU
                        time.sleep(0.5)
                        
                        # Check if we should use fallback for this and all future images
                        # due to repeated CUDA errors
                        current_use_fallback = use_fallback
                        
                        fen, used_fallback = image_to_fen(
                            image_filename, 
                            output_images_dir, 
                            use_fallback=current_use_fallback,
                            task_id=task_id
                        )
                        
                        # If this conversion attempt had CUDA errors (but we didn't use fallback yet),
                        # increment our counter
                        if not current_use_fallback and fen is None and config.FEN_FALLBACK_ENABLED:
                            cuda_error_count += 1
                            # If we've now seen too many CUDA errors, switch to fallback for all future images
                            if cuda_error_count >= max_cuda_errors:
                                print(f"[FEN] Too many CUDA errors ({cuda_error_count}). Switching to fallback FEN generator for all remaining images.")
                                use_fallback = True
                                # Retry this image with fallback
                                fen, used_fallback = image_to_fen(
                                    image_filename, 
                                    output_images_dir, 
                                    use_fallback=True,
                                    task_id=task_id
                                )
                        
                        if fen:
                            content_item["fen"] = fen
                            if used_fallback:
                                fallback_fen_conversions += 1
                                content_item["fen_from_fallback"] = True
                                print(f"[FEN] Generated fallback FEN for task {task_id} with image {image_filename}: {fen}")
                            else:
                                successful_fen_conversions += 1
                                print(f"[FEN] Successfully generated FEN for task {task_id} with image {image_filename}: {fen}")
                        else:
                            # Add a placeholder to indicate we tried but failed
                            content_item["fen_conversion_attempted"] = True
                            content_item["fen_conversion_failed"] = True
                            print(f"[FEN] Could not generate FEN for task {task_id} with image {image_filename}")
                    else:
                        print(f"[FEN] Task {task_id} found with empty image filename")
    
    # Report statistics
    print(f"[FEN] Conversion Summary:")
    print(f"[FEN]   Total tasks: {total_tasks}")
    print(f"[FEN]   Tasks with images: {tasks_with_images}")
    print(f"[FEN]   Successful FEN conversions via neural network: {successful_fen_conversions}")
    print(f"[FEN]   Fallback FEN conversions: {fallback_fen_conversions}")
    print(f"[FEN]   Failed FEN conversions: {tasks_with_images - successful_fen_conversions - fallback_fen_conversions}")
    
    return extracted_data

if __name__ == "__main__":
    # Test code for direct execution of this module
    import json
    
    # Create a simple test structure
    test_data = {
        "book_title": "Test Book",
        "lessons": [
            {
                "lesson_number": 1,
                "title": "Test Lesson",
                "content": [
                    {
                        "type": "task",
                        "text": "Test task with image",
                        "image": "diagram_test.png"
                    }
                ]
            }
        ]
    }
    
    # Test the FEN conversion
    output_dir = config.OUTPUT_IMAGE_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a dummy test image if needed
    test_image_path = os.path.join(output_dir, "diagram_test.png")
    if not os.path.exists(test_image_path):
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (800, 800), color = (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((400, 400), "Test Chess Diagram", fill=(0, 0, 0))
        img.save(test_image_path)
    
    # Process the test data
    processed_data = process_extracted_data_for_fen(test_data, output_dir)
    
    # Output the results
    print(json.dumps(processed_data, indent=2)) 