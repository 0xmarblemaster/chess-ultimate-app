import os
import json
import glob
import time
from typing import Tuple

from . import config
from .extract import extract_content
from .fen_converter import process_extracted_data_for_fen
from .chunker import chunk_processed_data
from .weaviate_loader import get_weaviate_client, define_weaviate_schema, load_chunks_to_weaviate, check_collection_exists

def get_file_id(filepath: str) -> str:
    """Generates a unique ID from the filename without extension."""
    return os.path.splitext(os.path.basename(filepath))[0]

def run_pipeline_for_file(file_path: str) -> Tuple[bool, str]:
    """
    Runs the ETL pipeline for a single file.
    
    Args:
        file_path: Path to the file to process (DOCX or PDF)
    
    Returns:
        Tuple of (success, message)
    """
    start_time = time.time()
    file_id = get_file_id(file_path)
    
    print(f"\n--- Starting ETL Pipeline for: {os.path.basename(file_path)} (ID: {file_id}) ---")
    
    # 1. Extract Content
    print(f"[ETL Pipeline] Stage 1: Extracting content from {file_path}...")
    extracted_data_path = os.path.join(config.EXTRACTED_JSON_DIR, f"{file_id}_extracted.json")
    
    if not os.path.isabs(file_path):
        full_file_path = os.path.join(config.INPUT_DIR, file_path)
    else:
        full_file_path = file_path
        
    extracted_data = extract_content(full_file_path, config.OUTPUT_IMAGE_DIR)
    
    if extracted_data:
        with open(extracted_data_path, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        print(f"[ETL Pipeline] Content extracted and saved to {extracted_data_path}")
    else:
        error_msg = f"[ETL Pipeline] Error: Extraction failed for {file_path}. Skipping further processing."
        print(error_msg)
        return False, error_msg

    # 2. FEN Conversion
    fen_converted_data_path = os.path.join(config.FEN_CONVERTED_JSON_DIR, f"{file_id}_fen_converted.json")
    
    if config.FEN_CONVERTER_ENABLED and extracted_data:
        print(f"[ETL Pipeline] Stage 2: Converting images to FEN...")
        fen_data = process_extracted_data_for_fen(extracted_data.copy(), config.OUTPUT_IMAGE_DIR)
        
        with open(fen_converted_data_path, "w", encoding="utf-8") as f:
            json.dump(fen_data, f, ensure_ascii=False, indent=2)
        print(f"[ETL Pipeline] FEN conversion complete, data saved to {fen_converted_data_path}")
    elif extracted_data:
        # FEN converter disabled, just copy data
        fen_data = extracted_data.copy()
        with open(fen_converted_data_path, "w", encoding="utf-8") as f:
            json.dump(fen_data, f, ensure_ascii=False, indent=2)
        print(f"[ETL Pipeline] FEN conversion disabled. Copied extracted data for next stage.")
    else:
        error_msg = "[ETL Pipeline] Error: No data from extraction to process for FEN conversion."
        print(error_msg)
        return False, error_msg

    # 3. Chunk Data
    chunks_data_path = os.path.join(config.CHUNKS_JSON_DIR, f"{file_id}_chunks.json")
    
    if fen_data:
        print(f"[ETL Pipeline] Stage 3: Chunking data...")
        chunks = chunk_processed_data(fen_data)
        
        with open(chunks_data_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"[ETL Pipeline] Data chunked, chunks saved to {chunks_data_path}")
    else:
        error_msg = "[ETL Pipeline] Error: No data from FEN conversion to chunk."
        print(error_msg)
        return False, error_msg

    # 4. Load to Weaviate
    if config.WEAVIATE_ENABLED and chunks:
        print(f"[ETL Pipeline] Stage 4: Loading chunks to Weaviate...")
        
        try:
            client = get_weaviate_client()
            
            if client:
                if not check_collection_exists(client, config.WEAVIATE_CLASS_NAME):
                    print(f"[ETL Pipeline] Weaviate collection '{config.WEAVIATE_CLASS_NAME}' does not exist. Creating schema...")
                    define_weaviate_schema(client)
                
                load_chunks_to_weaviate(client, chunks)
                print(f"[ETL Pipeline] Chunks loaded to Weaviate.")
            else:
                print("[ETL Pipeline] Could not connect to Weaviate. Skipping loading.")
                
        except Exception as e:
            error_msg = f"[ETL Pipeline] Error during Weaviate operation: {e}"
            print(error_msg)
            return False, error_msg
    elif chunks:
        # Weaviate disabled
        print("[ETL Pipeline] Weaviate loading disabled. ETL pipeline finished (data not loaded to Weaviate).")
    else:
        error_msg = "[ETL Pipeline] Error: No chunks to load to Weaviate."
        print(error_msg)
        return False, error_msg

    end_time = time.time()
    success_msg = f"[ETL Pipeline] ETL Pipeline for: {os.path.basename(file_path)} finished in {end_time - start_time:.2f} seconds"
    print(success_msg)
    return True, success_msg

def run_full_etl_pipeline():
    """
    Runs the ETL pipeline for all supported files in the input directory.
    
    Returns:
        Tuple of (success_count, error_count, total_count)
    """
    print(f"Starting full ETL process. Input directory: {config.INPUT_DIR}")
    
    # Supported file types
    supported_patterns = ["*.docx", "*.pdf"]
    all_files = []
    
    for pattern in supported_patterns:
        all_files.extend(glob.glob(os.path.join(config.INPUT_DIR, pattern)))

    if not all_files:
        print(f"No supported files found in {config.INPUT_DIR}. Exiting.")
        return 0, 0, 0

    print(f"Found {len(all_files)} files to process.")
    
    success_count = 0
    error_count = 0
    
    for filepath in all_files:
        success, message = run_pipeline_for_file(filepath)
        if success:
            success_count += 1
        else:
            error_count += 1
    
    print(f"\n--- Full ETL Process Completed. Success: {success_count}, Error: {error_count}, Total: {len(all_files)} ---")
    return success_count, error_count, len(all_files)

if __name__ == "__main__":
    # This allows running the ETL pipeline directly
    print("Running ETL pipeline...")
    
    # Ensure input directory exists
    if not os.path.exists(config.INPUT_DIR):
        os.makedirs(config.INPUT_DIR)
        print(f"Created input directory: {config.INPUT_DIR}")
        print(f"Please add DOCX or PDF files to '{config.INPUT_DIR}' to run the pipeline.")
    
    # Check if OpenAI API key is set
    if config.OPENAI_API_KEY:
        print("OpenAI API Key is configured.")
    else:
        print("Warning: OpenAI API Key is NOT configured. Weaviate with text2vec-openai might fail.")
    
    # Run the pipeline
    success_count, error_count, total_count = run_full_etl_pipeline() 