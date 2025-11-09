#!/usr/bin/env python3
"""
Simple ETL with FEN Conversion
Based on the working ETL process we used before
"""

import os
import sys
import json
import weaviate
from pathlib import Path

def extract_and_process_with_fen():
    """Extract УРОК 2.docx and process with FEN conversion"""
    try:
        print('🚀 SIMPLE ETL WITH FEN CONVERSION')
        print('=' * 50)
        
        # Use the working extract.py approach
        sys.path.insert(0, 'etl')
        from etl.extract import extract_content
        
        # Document path
        doc_path = "/home/marblemaster/Desktop/Cursor/mvp1/backend/input/russian_education/УРОК 2.docx"
        
        if not os.path.exists(doc_path):
            print(f"❌ Document not found: {doc_path}")
            return False
            
        print(f"📄 Extracting content from: {doc_path}")
        
        # Extract lesson data (this was working before)
        result = extract_content(doc_path, output_images_dir="./output_images")
        
        # Check result - it may not have 'success' field but still work
        if not result:
            print("❌ Content extraction failed - no result")
            return False
            
        lessons = result.get('lessons', [])
        if not lessons:
            print("❌ No lessons found in result")
            print(f"Result keys: {list(result.keys())}")
            return False
            
        print(f"✅ Extracted {len(lessons)} lessons")
        
        # Process the first lesson (УРОК 2)
        lesson = lessons[0]
        print(f"📚 Processing lesson: {lesson.get('title', 'УРОК 2')}")
        
        # Create chunks using the working chunker
        from etl.chunker import create_chunks_from_lesson
        chunks = create_chunks_from_lesson(lesson, book_title="Шахматы - первый год")
        
        print(f"📦 Created {len(chunks)} chunks")
        
        # Process chunks with FEN conversion for diagrams
        processed_chunks = []
        diagram_count = 0
        fen_success_count = 0
        
        for i, chunk in enumerate(chunks):
            processed_chunk = chunk.copy()
            
            # Check if chunk has an image (chess diagram)
            if chunk.get('image'):
                diagram_count += 1
                image_file = chunk['image']
                print(f"🖼️ Processing diagram {diagram_count}: {image_file}")
                
                # Try FEN conversion
                try:
                    from etl.fen_converter import image_to_fen
                    output_dir = "./output_images"
                    
                    # Ensure the image exists in output_images
                    image_path = os.path.join(output_dir, image_file)
                    if os.path.exists(image_path):
                        print(f"   📍 Found image at: {image_path}")
                        
                        # Convert to FEN
                        fen_result, used_fallback = image_to_fen(
                            image_filename=image_file,
                            output_images_dir=output_dir,
                            use_fallback=True
                        )
                        
                        if fen_result and fen_result != "Error":
                            processed_chunk['fen'] = fen_result
                            processed_chunk['fen_method'] = 'fallback' if used_fallback else 'neural_network'
                            fen_success_count += 1
                            print(f"   ✅ FEN: {fen_result}")
                        else:
                            processed_chunk['fen'] = ""
                            processed_chunk['fen_method'] = 'failed'
                            print(f"   ❌ FEN conversion failed")
                    else:
                        print(f"   ⚠️ Image not found: {image_path}")
                        processed_chunk['fen'] = ""
                        processed_chunk['fen_method'] = 'image_missing'
                        
                except Exception as e:
                    print(f"   ❌ FEN conversion error: {e}")
                    processed_chunk['fen'] = ""
                    processed_chunk['fen_method'] = 'error'
                    
            processed_chunks.append(processed_chunk)
            
        print(f"\n📊 PROCESSING SUMMARY:")
        print(f"   Total chunks: {len(processed_chunks)}")
        print(f"   Diagrams found: {diagram_count}")
        print(f"   FEN conversions successful: {fen_success_count}")
        print(f"   FEN success rate: {(fen_success_count/diagram_count*100):.1f}%" if diagram_count > 0 else "   No diagrams")
        
        # Load processed chunks into Weaviate
        print(f"\n💾 Loading chunks into Weaviate...")
        
        client = weaviate.connect_to_local(host="localhost", port=8080)
        collection = client.collections.get("ChessLessonChunk")
        
        loaded_count = 0
        for chunk in processed_chunks:
            try:
                # Prepare data for Weaviate
                data_object = {
                    "content": chunk.get("text", ""),
                    "book_title": "Шахматы - первый год",
                    "lesson_number": "2",
                    "lesson_title": "Шах и мат",
                    "type": "education",
                    "language": "ru",
                    "content_type": chunk.get("type", "text"),
                    "source_file": "УРОК 2.docx",
                    "processing_method": "simple_etl_with_fen",
                    "fen": chunk.get("fen", ""),
                    "image": chunk.get("image", ""),
                    "diagram_analysis": chunk.get("fen_method", "")
                }
                
                collection.data.insert(data_object)
                loaded_count += 1
                
            except Exception as e:
                print(f"❌ Error loading chunk: {e}")
                
        # client.close() removed - Weaviate client manages connections automatically
        
        print(f"✅ Loaded {loaded_count} chunks into Weaviate")
        
        # Save results
        results = {
            "success": True,
            "lessons_processed": len(lessons),
            "chunks_created": len(processed_chunks),
            "diagrams_found": diagram_count,
            "fen_conversions": fen_success_count,
            "chunks_loaded": loaded_count,
            "processed_chunks": processed_chunks
        }
        
        with open('simple_etl_fen_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"💾 Results saved to: simple_etl_fen_results.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in ETL process: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = extract_and_process_with_fen()
    if success:
        print('\n🎉 SIMPLE ETL WITH FEN CONVERSION COMPLETED!')
    else:
        print('\n💥 ETL FAILED - Check errors above') 