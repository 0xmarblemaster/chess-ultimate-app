#!/usr/bin/env python3
"""
Check Chess Diagram FEN Processing Status
"""

import weaviate

def check_diagram_fens():
    """Check FEN processing status for chess diagrams"""
    try:
        print('🔍 CHECKING CHESS DIAGRAM FEN PROCESSING')
        print('=' * 50)

        # Connect to Weaviate
        client = weaviate.connect_to_local(host='localhost', port=8080)
        collection = client.collections.get('ChessLessonChunk')

        # Get all objects to check FEN status
        results = collection.query.fetch_objects(limit=20)

        diagram_count = 0
        fen_success_count = 0
        fen_empty_count = 0
        images_with_content = []

        for i, obj in enumerate(results.objects):
            props = obj.properties
            image = props.get('image', '')
            fen = props.get('fen', '')
            content = props.get('content', '')
            content_preview = content[:100] if content else 'No content'
            
            if image:  # Has an image/diagram
                diagram_count += 1
                print(f'\n📊 Diagram {diagram_count}:')
                print(f'   Image: {image}')
                print(f'   FEN: "{fen}"')
                print(f'   Content: {content_preview}...')
                
                images_with_content.append({
                    'image': image,
                    'fen': fen,
                    'content': content,
                    'has_fen': bool(fen and fen.strip())
                })
                
                if fen and fen.strip():
                    fen_success_count += 1
                    print('   ✅ FEN conversion: SUCCESS')
                    # Validate FEN format
                    if '/' in fen and ' ' in fen:
                        print(f'   ✅ FEN appears valid: {fen}')
                    else:
                        print(f'   ⚠️  FEN format questionable: {fen}')
                else:
                    fen_empty_count += 1
                    print('   ❌ FEN conversion: FAILED/EMPTY')

        print(f'\n📈 SUMMARY:')
        print(f'   Total diagrams found: {diagram_count}')
        print(f'   Successful FEN conversions: {fen_success_count}')
        print(f'   Failed/Empty FEN conversions: {fen_empty_count}')
        print(f'   Success rate: {(fen_success_count/diagram_count*100):.1f}%' if diagram_count > 0 else '   No diagrams found')

        # Check if image files exist
        print(f'\n📁 CHECKING IMAGE FILE EXISTENCE:')
        import os
        image_dir = '/home/marblemaster/Desktop/Cursor/mvp1/backend/output/images'
        alt_image_dir = '/home/marblemaster/Desktop/Cursor/mvp1/backend/input/russian_education'
        
        for img_data in images_with_content:
            img_file = img_data['image']
            img_path1 = os.path.join(image_dir, img_file)
            img_path2 = os.path.join(alt_image_dir, img_file)
            
            exists1 = os.path.exists(img_path1)
            exists2 = os.path.exists(img_path2)
            
            print(f'   {img_file}: {"✅" if exists1 or exists2 else "❌"} {"(output)" if exists1 else ""} {"(input)" if exists2 else ""} {"(missing)" if not exists1 and not exists2 else ""}')

        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f'❌ Error checking diagram FENs: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_diagram_fens() 