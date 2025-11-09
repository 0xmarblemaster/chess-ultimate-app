#!/usr/bin/env python3
"""
Full ETL Pipeline with FEN Conversion
Process УРОК 2.docx with complete diagram analysis and FEN generation
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, '.')

def run_full_etl_with_fen():
    """Run the complete ETL pipeline with FEN conversion enabled"""
    try:
        print('🚀 STARTING FULL ETL PIPELINE WITH FEN CONVERSION')
        print('=' * 60)
        
        # Import the Russian education pipeline
        from etl.russian_education_pipeline import RussianEducationPipeline
        
        # Initialize the pipeline with FEN conversion enabled
        print('📋 Initializing Russian Education Pipeline...')
        pipeline = RussianEducationPipeline()
        
        # Set the document path
        document_path = Path("input/russian_education/УРОК 2.docx")
        
        if not document_path.exists():
            print(f"❌ Document not found: {document_path}")
            return False
            
        print(f"📄 Processing document: {document_path}")
        
        # Run the pipeline with FEN conversion enabled
        print('\n🔄 Running ETL pipeline...')
        results = pipeline.process_single_document(file_path=document_path)
        
        if results and results.get('success'):
            print('✅ ETL Pipeline completed successfully!')
            
            # Print summary
            lessons = results.get('lessons', [])
            total_chunks = results.get('total_chunks', 0)
            total_images = results.get('total_images', 0)
            
            print(f'\n📊 PROCESSING SUMMARY:')
            print(f'   Lessons processed: {len(lessons)}')
            print(f'   Total chunks: {total_chunks}')
            print(f'   Chess diagrams: {total_images}')
            
            # Check FEN conversion success
            fen_count = 0
            fen_success = 0
            
            for lesson in lessons:
                for chunk in lesson.get('chunks', []):
                    if chunk.get('image'):  # Has diagram
                        fen_count += 1
                        if chunk.get('fen'):  # Has FEN
                            fen_success += 1
                            
            print(f'   FEN conversions attempted: {fen_count}')
            print(f'   FEN conversions successful: {fen_success}')
            print(f'   FEN success rate: {(fen_success/fen_count*100):.1f}%' if fen_count > 0 else '   No diagrams found')
            
            # Save detailed results
            results_file = 'full_etl_fen_results.json'
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f'💾 Detailed results saved to: {results_file}')
            
            return True
            
        else:
            print('❌ ETL Pipeline failed!')
            print(f'Error: {results.get("error", "Unknown error")}')
            return False
            
    except Exception as e:
        print(f'❌ Error running ETL pipeline: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_full_etl_with_fen()
    if success:
        print('\n🎉 FULL ETL PIPELINE WITH FEN CONVERSION COMPLETED!')
    else:
        print('\n💥 PIPELINE FAILED - Check errors above') 