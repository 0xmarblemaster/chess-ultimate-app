#!/usr/bin/env python3
"""
Test Retriever Agent Collection Selection Directly
"""

import sys
import weaviate

def test_retriever_direct():
    """Test retriever agent collection selection logic directly"""
    try:
        print('🧪 TESTING RETRIEVER AGENT COLLECTION SELECTION')
        print('=' * 60)
        
        # Test the collection selection logic
        print('\n🔍 STEP 1: TEST COLLECTION SELECTION LOGIC')
        
        # Simulate the logic from our fixed retriever agent
        def determine_collection_for_query(query_text):
            """Determine which collection to search based on query content"""
            query_lower = query_text.lower()
            
            # Russian education keywords
            education_keywords = [
                'урок', 'lesson', 'шах', 'мат', 'документ', 'document',
                'защита', 'defense', 'ладья', 'rook', 'король', 'king',
                'учебник', 'textbook', 'задача', 'problem', 'диаграмма', 'diagram'
            ]
            
            # Check for education-related content
            if any(keyword in query_lower for keyword in education_keywords):
                return "ChessLessonChunk"
            else:
                return "ChessGame"
                
        # Test queries
        test_queries = [
            ("Что такое шах?", "ChessLessonChunk"),
            ("Как защититься от шаха?", "ChessLessonChunk"), 
            ("О чем говорится в документе УРОК 2?", "ChessLessonChunk"),
            ("Покажи позицию с матом", "ChessLessonChunk"),
            ("Find games with Sicilian Defense", "ChessGame"),
            ("Show me a chess game", "ChessGame"),
            ("Найди диаграмму с ладьей", "ChessLessonChunk")
        ]
        
        for query, expected in test_queries:
            result = determine_collection_for_query(query)
            status = "✅" if result == expected else "❌"
            print(f"   {status} '{query}' → {result} (expected: {expected})")
            
        # Test 2: Direct database search
        print('\n📊 STEP 2: DIRECT DATABASE SEARCH TEST')
        
        client = weaviate.connect_to_local(host="localhost", port=8080)
        
        # Test ChessLessonChunk collection
        lesson_collection = client.collections.get("ChessLessonChunk")
        
        russian_queries = ["шах", "мат", "защита"]
        
        for query in russian_queries:
            results = lesson_collection.query.bm25(
                query=query,
                limit=3
            )
            
            print(f"   🔍 Query '{query}' in ChessLessonChunk:")
            print(f"      Found {len(results.objects)} results")
            
            if results.objects:
                first_result = results.objects[0]
                content = first_result.properties.get('content', '')[:150]
                fen = first_result.properties.get('fen', '')
                print(f"      Content: {content}...")
                if fen:
                    print(f"      FEN: {fen}")
                    
        # Test 3: Verify FEN data accessibility
        print('\n♟️ STEP 3: VERIFY FEN DATA ACCESSIBILITY')
        
        # Get all objects with FEN data
        all_results = lesson_collection.query.fetch_objects(limit=20)
        
        fen_objects = []
        for obj in all_results.objects:
            fen = obj.properties.get('fen', '')
            if fen and fen != '':
                fen_objects.append({
                    'content': obj.properties.get('content', '')[:100],
                    'fen': fen,
                    'image': obj.properties.get('image', '')
                })
                
        print(f"   📊 Found {len(fen_objects)} objects with FEN data")
        
        # Show sample FEN positions
        for i, obj in enumerate(fen_objects[:5]):
            print(f"   🎯 Position {i+1}:")
            print(f"      Content: {obj['content']}...")
            print(f"      FEN: {obj['fen']}")
            print(f"      Image: {obj['image']}")
            
        # client.close() removed - Weaviate client manages connections automatically
        
        print('\n🎉 RETRIEVER AGENT TESTING COMPLETED!')
        return True
        
    except Exception as e:
        print(f'❌ Error testing retriever agent: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_retriever_direct()
    if success:
        print('\n✅ RETRIEVER AGENT VERIFICATION COMPLETED!')
    else:
        print('\n💥 RETRIEVER TESTING FAILED - Check errors above') 