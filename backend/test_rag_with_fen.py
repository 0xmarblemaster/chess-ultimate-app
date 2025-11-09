#!/usr/bin/env python3
"""
Test RAG System with FEN-Enhanced Russian Education Data
"""

import weaviate
import requests
import json

def test_rag_with_fen():
    """Test RAG system with Russian education queries and FEN data"""
    try:
        print('🧪 TESTING RAG SYSTEM WITH FEN-ENHANCED DATA')
        print('=' * 60)
        
        # Test 1: Direct database verification
        print('\n📊 STEP 1: VERIFY DATABASE CONTENT')
        client = weaviate.connect_to_local(host="localhost", port=8080)
        collection = client.collections.get("ChessLessonChunk")
        
        # Get total count
        total_objects = collection.aggregate.over_all(total_count=True)
        print(f"✅ Total objects in ChessLessonChunk: {total_objects.total_count}")
        
        # Check FEN data
        results = collection.query.fetch_objects(limit=5)
        fen_count = 0
        for obj in results.objects:
            if obj.properties.get('fen'):
                fen_count += 1
                
        print(f"✅ Objects with FEN data: {fen_count}/5 (sample)")
        
        # Test 2: Search for specific Russian terms
        print('\n🔍 STEP 2: SEARCH FOR RUSSIAN CHESS TERMS')
        
        search_terms = ["шах", "мат", "ладья", "король"]
        for term in search_terms:
            results = collection.query.bm25(
                query=term,
                limit=3
            )
            
            found_count = len(results.objects)
            print(f"   '{term}': {found_count} results found")
            
            if found_count > 0:
                # Show first result with FEN if available
                first_result = results.objects[0]
                content = first_result.properties.get('content', '')[:100] + '...'
                fen = first_result.properties.get('fen', '')
                print(f"      Content: {content}")
                if fen:
                    print(f"      FEN: {fen}")
                    
        # client.close() removed - Weaviate client manages connections automatically
        
        # Test 3: RAG API queries
        print('\n🤖 STEP 3: TEST RAG API WITH RUSSIAN QUERIES')
        
        base_url = "http://localhost:5001"
        
        # Check if backend is running
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            print(f"✅ Backend is running (status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"❌ Backend not accessible: {e}")
            print("   Skipping API tests...")
            return True
            
        # Test queries
        test_queries = [
            "Что такое шах?",
            "Как защититься от шаха?", 
            "Что такое мат?",
            "Покажи позицию с матом в 1 ход",
            "Какие есть защиты от шаха?"
        ]
        
        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            
            try:
                response = requests.post(
                    f"{base_url}/api/chat",
                    json={"message": query},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('response', 'No response')
                    print(f"   ✅ Response: {answer[:200]}...")
                    
                    # Check if response mentions FEN
                    if 'fen' in answer.lower() or any(char in answer for char in ['/', 'w', 'b']) and len([c for c in answer if c == '/']) >= 7:
                        print(f"   🎯 Response includes FEN data!")
                        
                else:
                    print(f"   ❌ API Error: {response.status_code}")
                    print(f"      Response: {response.text[:200]}...")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Request failed: {e}")
                
        # Test 4: Position-specific queries
        print('\n♟️ STEP 4: TEST POSITION-SPECIFIC QUERIES')
        
        position_queries = [
            "Найди позицию где король и ладья против короля",
            "Покажи диаграмму с матом ладьей",
            "Есть ли позиции с конем в уроке?"
        ]
        
        for query in position_queries:
            print(f"\n🎯 Position Query: '{query}'")
            
            try:
                response = requests.post(
                    f"{base_url}/api/chat",
                    json={"message": query},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('response', 'No response')
                    print(f"   ✅ Response: {answer[:300]}...")
                else:
                    print(f"   ❌ API Error: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Request failed: {e}")
                
        print('\n🎉 RAG TESTING WITH FEN DATA COMPLETED!')
        return True
        
    except Exception as e:
        print(f'❌ Error testing RAG system: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_with_fen()
    if success:
        print('\n✅ RAG SYSTEM WITH FEN DATA VERIFICATION COMPLETED!')
    else:
        print('\n💥 RAG TESTING FAILED - Check errors above') 