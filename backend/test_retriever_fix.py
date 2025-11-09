#!/usr/bin/env python3
"""
Test the Retriever Agent Fix Directly
Test if our collection selection logic works without starting the full backend
"""

import sys
import os

# Add backend to path
sys.path.insert(0, '.')

def test_retriever_collection_selection():
    """Test if the retriever agent now selects the correct collection"""
    try:
        print("🧪 TESTING RETRIEVER AGENT COLLECTION SELECTION")
        print("=" * 55)
        
        # Import the updated retriever agent
        from etl.agents.retriever_agent import RetrieverAgent
        import weaviate
        
        # Connect to Weaviate
        client = weaviate.connect_to_local(host="localhost", port=8080)
        print("✅ Connected to Weaviate")
        
        # Create retriever agent instance
        retriever = RetrieverAgent(client=client, opening_book_path="")
        print("✅ Created RetrieverAgent instance")
        
        # Test Russian education queries
        test_queries = [
            ("О чем говорится в документе УРОК 2?", "Should use ChessLessonChunk"),
            ("Что такое шах?", "Should use ChessLessonChunk"),  
            ("Расскажи про урок 2", "Should use ChessLessonChunk"),
            ("Find games with Carlsen", "Should use ChessGame"),
            ("Show me Ruy Lopez opening", "Should use ChessGame"),
        ]
        
        print("\n🔍 TESTING COLLECTION SELECTION LOGIC:")
        for query, expected in test_queries:
            print(f"\n📝 Query: '{query}'")
            print(f"   Expected: {expected}")
            
            # Test the collection determination logic
            if hasattr(retriever, '_determine_collection_for_query'):
                determined_collection = retriever._determine_collection_for_query(query)
                print(f"   Determined: {determined_collection}")
                
                # Check if it matches expectation
                if ("ChessLessonChunk" in expected and determined_collection == "ChessLessonChunk") or \
                   ("ChessGame" in expected and determined_collection == "ChessGame"):
                    print("   ✅ CORRECT collection selected!")
                else:
                    print("   ❌ WRONG collection selected!")
            else:
                print("   ❌ Helper method not found - fix may not have applied correctly")
        
        # Test actual search on ChessLessonChunk for Russian queries
        print("\n📚 TESTING ACTUAL SEARCH ON ChessLessonChunk:")
        
        russian_query = "Что такое шах?"
        print(f"🔍 Testing search for: '{russian_query}'")
        
        try:
            # Test metadata that should trigger ChessLessonChunk search
            metadata = {
                "query_type": "semantic", 
                "k_results": 5,
                "target_class_name": "ChessLessonChunk"  # Explicitly set to test
            }
            
            result = retriever.retrieve(russian_query, metadata)
            
            retrieved_chunks = result.get("retrieved_chunks", [])
            print(f"📊 Retrieved {len(retrieved_chunks)} chunks")
            
            # Check if we got Russian content
            russian_content_found = False
            for i, chunk in enumerate(retrieved_chunks[:3]):
                if isinstance(chunk, dict):
                    content = str(chunk.get("content", ""))
                    print(f"   {i+1}. Content preview: '{content[:100]}...'")
                    
                    # Check for Russian text
                    if any(russian_word in content.lower() for russian_word in ['шах', 'мат', 'урок', 'король']):
                        russian_content_found = True
                        print(f"      ✅ Found Russian chess content!")
                    else:
                        print(f"      ⚠️  No Russian content detected")
            
            if russian_content_found:
                print("\n🎉 SUCCESS: Retriever found Russian education content!")
            else:
                print("\n⚠️  WARNING: No Russian content found - may need further investigation")
                
        except Exception as e:
            print(f"❌ Search test failed: {e}")
            import traceback
            traceback.print_exc()
        
        # client.close() removed - Weaviate client manages connections automatically
        print("\n✅ RETRIEVER AGENT TEST COMPLETE!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_retriever_collection_selection() 