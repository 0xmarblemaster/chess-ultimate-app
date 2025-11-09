#!/usr/bin/env python3
"""
Test RAG System with Russian Education Data
"""

import sys
import requests
import time

def test_rag_russian():
    """Test if the RAG system can now access Russian education data"""
    try:
        print("🧪 TESTING RAG SYSTEM WITH RUSSIAN EDUCATION DATA")
        print("=" * 55)
        
        base_url = "http://localhost:5001"
        
        # Test questions in Russian about the document
        test_queries = [
            ("О чем говорится в документе УРОК 2?", "What is document LESSON 2 about?"),
            ("Что такое шах?", "What is check?"),
            ("Что такое мат?", "What is checkmate?"),
            ("Какие есть защиты от шаха?", "What defenses are there against check?"),
            ("Расскажи про урок 2", "Tell me about lesson 2")
        ]
        
        for russian_query, english_desc in test_queries:
            print(f"\n🔍 Testing: '{russian_query}' ({english_desc})")
            
            # Test the main RAG endpoint
            try:
                payload = {
                    "query": russian_query,
                    "session_id": "test_session_123"
                }
                
                response = requests.post(
                    f"{base_url}/api/chat/rag",
                    json=payload,
                    timeout=10
                )
                
                print(f"   📡 Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    answer = data.get('answer', '')
                    sources = data.get('sources', [])
                    query_type = data.get('query_type', 'unknown')
                    
                    print(f"   🤖 Query Type: {query_type}")
                    print(f"   📚 Sources Found: {len(sources)}")
                    print(f"   💬 Answer: {answer[:200]}...")
                    
                    # Check if the answer contains Russian text (indicating it found our data)
                    russian_keywords = ['шах', 'мат', 'урок', 'король', 'ладья', 'фигур']
                    found_russian = any(keyword in answer.lower() for keyword in russian_keywords)
                    
                    if found_russian:
                        print("   ✅ SUCCESS: Answer contains Russian chess terms!")
                    else:
                        print("   ⚠️  WARNING: Answer doesn't seem to reference Russian content")
                        
                    if sources:
                        print(f"   📋 Sample source: {str(sources[0])[:100]}...")
                
                elif response.status_code == 503:
                    print("   ⚠️  RAG system not initialized (503)")
                else:
                    print(f"   ❌ Error: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Request failed: {e}")
            
            time.sleep(1)  # Brief pause between requests
        
        print(f"\n🏁 RAG TESTING COMPLETE!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rag_russian() 