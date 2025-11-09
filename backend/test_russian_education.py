#!/usr/bin/env python3
"""
Test Russian Education Processing - Simple Version
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

def test_russian_education():
    """Test Russian education processing using ETL modules"""
    try:
        print("🚀 Starting Russian Education Processing Test")
        print("=" * 50)
        
        # Import ETL modules directly
        from etl.extract import extract_content
        from etl.chunker import create_chunks_from_lesson
        from etl import config
        
        print("✅ ETL modules imported")
        
        # Test document path - use absolute path to avoid double path issue
        test_doc = os.path.abspath("input/russian_education/УРОК 2.docx")
        
        if not os.path.exists(test_doc):
            print(f"❌ Test document not found: {test_doc}")
            return
        
        print(f"📄 Processing document: {test_doc}")
        
        # Step 1: Extract content
        print("\n🔍 Step 1: Extracting content...")
        extracted_data = extract_content(test_doc, "output_images/russian_test")
        
        if not extracted_data:
            print("❌ Extraction failed")
            return
        
        print(f"✅ Content extracted")
        print(f"   📚 Book: {extracted_data.get('book_title', 'Unknown')}")
        print(f"   📖 Lessons: {len(extracted_data.get('lessons', []))}")
        
        # Step 2: Process and chunk the data
        print("\n✂️  Step 2: Creating chunks...")
        all_chunks = []
        book_title = extracted_data.get("book_title", "Русская шахматная книга")
        
        # Russian chess terms detection
        russian_terms = []
        chess_keywords = ["король", "ферзь", "ладья", "слон", "конь", "пешка", "шах", "мат", "рокировка"]
        
        for lesson in extracted_data.get("lessons", []):
            lesson_chunks = create_chunks_from_lesson(lesson, book_title, language="ru")
            
            # Analyze for Russian chess content
            for chunk in lesson_chunks:
                chunk_text = chunk.get("text", "").lower()
                found_terms = [term for term in chess_keywords if term in chunk_text]
                russian_terms.extend(found_terms)
                
                # Add Russian-specific metadata
                chunk.update({
                    "language": "ru",
                    "content_type": "russian_education",
                    "source_file": "УРОК 2.docx",
                    "processing_method": "etl_test"
                })
            
            all_chunks.extend(lesson_chunks)
        
        print(f"✅ Created {len(all_chunks)} chunks")
        if russian_terms:
            unique_terms = list(set(russian_terms))
            print(f"🏷️  Russian chess terms found: {', '.join(unique_terms[:10])}")
            if len(unique_terms) > 10:
                print(f"    ... and {len(unique_terms) - 10} more")
        
        # Step 3: Show sample chunks
        print("\n📋 Step 3: Sample chunks...")
        for i, chunk in enumerate(all_chunks[:3]):
            print(f"  Chunk {i+1}:")
            print(f"    Type: {chunk.get('type', 'unknown')}")
            print(f"    Text: {chunk.get('text', '')[:100]}...")
            if chunk.get('fen'):
                print(f"    FEN: {chunk.get('fen')}")
            print()
        
        print("\n📊 PROCESSING SUMMARY:")
        print("=" * 30)
        print(f"✅ Document: {test_doc}")
        print(f"📚 Book: {book_title}")
        print(f"📖 Lessons processed: {len(extracted_data.get('lessons', []))}")
        print(f"🧩 Chunks created: {len(all_chunks)}")
        print(f"🇷🇺 Russian terms detected: {len(set(russian_terms))}")
        print(f"🎯 Language: Russian (ru)")
        
        # Save results to file
        import json
        output_file = "russian_education_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "extracted_data": extracted_data,
                "chunks": all_chunks,
                "russian_terms": list(set(russian_terms)),
                "summary": {
                    "book_title": book_title,
                    "lessons_count": len(extracted_data.get('lessons', [])),
                    "chunks_count": len(all_chunks),
                    "russian_terms_count": len(set(russian_terms))
                }
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Results saved to: {output_file}")
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_russian_education() 