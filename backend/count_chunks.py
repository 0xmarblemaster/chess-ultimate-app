#!/usr/bin/env python3

import json
import os
import re

def count_chunks(json_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        total_chunks = len(chunks)
        task_chunks = sum(1 for chunk in chunks if chunk.get('type') == 'task')
        fen_chunks = sum(1 for chunk in chunks if 'fen' in chunk)
        image_chunks = sum(1 for chunk in chunks if 'image' in chunk)
        diagram_ref_chunks = sum(1 for chunk in chunks if 'diagram_number_reference' in chunk)
        
        # Look for text containing diagram references
        diagram_pattern = re.compile(r'(диаграмм|diagram)[аыеa]?\s*(\d+)', re.IGNORECASE)
        text_with_diagram_ref = sum(1 for chunk in chunks if 'text' in chunk and diagram_pattern.search(chunk['text']))
        
        # Combined calculation
        diagrams = sum(1 for chunk in chunks if ('image' in chunk or 
                                               'fen' in chunk or 
                                               chunk.get('type') == 'task' or 
                                               'diagram_number_reference' in chunk or
                                               ('text' in chunk and diagram_pattern.search(chunk['text']))))
        
        print(f"File: {os.path.basename(json_file_path)}")
        print(f"Total chunks: {total_chunks}")
        print(f"Type='task' chunks: {task_chunks}")
        print(f"Chunks with FEN: {fen_chunks}")
        print(f"Chunks with images: {image_chunks}")
        print(f"Chunks with diagram references in properties: {diagram_ref_chunks}")
        print(f"Chunks with diagram references in text: {text_with_diagram_ref}")
        print(f"Total diagram/task chunks: {diagrams}")
        print(f"Percentage of diagram/tasks: {diagrams/total_chunks*100:.2f}%")
        
        # Print a sample of chunks with text diagram references
        if text_with_diagram_ref > 0:
            print("\nSample text with diagram references:")
            samples = 0
            for chunk in chunks:
                if 'text' in chunk and diagram_pattern.search(chunk['text']):
                    text = chunk['text']
                    match = diagram_pattern.search(text)
                    diagram_num = match.group(2)
                    print(f"  Diagram {diagram_num}: {text[:100]}...")
                    samples += 1
                    if samples >= 3:  # Limit to 3 samples
                        break
        
    except Exception as e:
        print(f"Error processing {json_file_path}: {e}")

if __name__ == "__main__":
    processed_data_dir = 'processed_data'
    for filename in os.listdir(processed_data_dir):
        if filename.endswith('_chunks.json'):
            file_path = os.path.join(processed_data_dir, filename)
            count_chunks(file_path)
            print("-" * 40) 