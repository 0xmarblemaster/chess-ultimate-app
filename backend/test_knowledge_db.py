#!/usr/bin/env python3
"""
Test Knowledge Database and Search Functionality
Comprehensive diagnostics for the Russian education RAG issues
"""

import sys
import os
import json
import weaviate

# Add backend to path
sys.path.insert(0, '.')

def test_knowledge_database():
    """Test all aspects of the knowledge database"""
    try:
        print("🔍 COMPREHENSIVE KNOWLEDGE DATABASE DIAGNOSTICS")
        print("=" * 60)
        
        # 1. Test Weaviate connection
        print("\n1️⃣ TESTING WEAVIATE CONNECTION")
        client = weaviate.connect_to_local(host="localhost", port=8080)
        print("✅ Connected to Weaviate successfully")
        
        # 2. List all collections
        print("\n2️⃣ CHECKING AVAILABLE COLLECTIONS")
        collections = client.collections.list_all()
        collection_names = list(collections.keys())
        print(f"📋 Available collections: {collection_names}")
        
        # 3. Check ChessLessonChunk collection specifically
        print("\n3️⃣ EXAMINING ChessLessonChunk COLLECTION")
        if 'ChessLessonChunk' in collection_names:
            collection = client.collections.get("ChessLessonChunk")
            
            # Get total count
            total_objects = collection.aggregate.over_all(total_count=True)
            print(f"📊 Total objects in ChessLessonChunk: {total_objects.total_count}")
            
            if total_objects.total_count > 0:
                # Get sample objects
                sample_results = collection.query.fetch_objects(limit=3)
                
                print("\n📋 SAMPLE OBJECTS:")
                for i, obj in enumerate(sample_results.objects):
                    print(f"\n  Object {i+1}:")
                    print(f"    UUID: {obj.uuid}")
                    print("    Properties:")
                    for key, value in obj.properties.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"      {key}: {value[:100]}... (truncated)")
                        else:
                            print(f"      {key}: {value}")
            
            # 4. Test Russian text search
            print("\n4️⃣ TESTING RUSSIAN TEXT SEARCH")
            
            # Test different search methods
            search_queries = [
                ("УРОК 2", "lesson 2 reference"),
                ("шах", "check in Russian"),
                ("мат", "checkmate in Russian"),
                ("урок", "lesson in Russian"),
                ("диаграмма", "diagram in Russian")
            ]
            
            for query, description in search_queries:
                print(f"\n🔍 Testing keyword search for '{query}' ({description}):")
                try:
                    results = collection.query.bm25(
                        query=query,
                        limit=3
                    )
                    print(f"   Found {len(results.objects)} results")
                    
                    for j, result in enumerate(results.objects):
                        content = result.properties.get('content', '')[:150]
                        print(f"     {j+1}. {content}...")
                        
                except Exception as e:
                    print(f"   ❌ Search failed: {e}")
            
            # 5. Test lesson repository search
            print("\n5️⃣ TESTING LESSON REPOSITORY SEARCH")
            try:
                from database.lesson_repository import LessonRepository
                repo = LessonRepository()
                
                # Test search with repository
                repo_results = repo.search_lessons(
                    query="урок 2",
                    limit=5
                )
                print(f"📚 LessonRepository search results: {len(repo_results)}")
                
                for k, result in enumerate(repo_results[:2]):
                    print(f"   {k+1}. Source: {result.get('source', 'unknown')}")
                    content = str(result.get('content', ''))[:100]
                    print(f"      Content: {content}...")
                    
            except Exception as e:
                print(f"❌ LessonRepository test failed: {e}")
                import traceback
                traceback.print_exc()
            
            # 6. Test configuration matching
            print("\n6️⃣ CHECKING CONFIGURATION ALIGNMENT")
            try:
                from etl import config as etl_config
                print(f"📋 Config WEAVIATE_CLASS_NAME: {etl_config.WEAVIATE_CLASS_NAME}")
                print(f"📋 LessonRepository collection_name: {repo.collection_name if 'repo' in locals() else 'N/A'}")
                
                # Check if they match
                if 'repo' in locals() and repo.collection_name == etl_config.WEAVIATE_CLASS_NAME:
                    print("✅ Configuration alignment: CORRECT")
                else:
                    print("❌ Configuration alignment: MISMATCH!")
                    
            except Exception as e:
                print(f"❌ Configuration check failed: {e}")
            
        else:
            print("❌ ChessLessonChunk collection NOT FOUND!")
            
        # 7. Test backend API endpoint
        print("\n7️⃣ TESTING BACKEND API ENDPOINTS")
        try:
            import requests
            
            # Test lesson search endpoint
            response = requests.get(
                "http://localhost:5001/api/lessons/search?query=урок 2",
                timeout=5
            )
            print(f"📡 API /lessons/search status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Results count: {data.get('count', 0)}")
            else:
                print(f"   Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ API test failed: {e}")
            
        # 8. Test Russian education API
        print("\n8️⃣ TESTING RUSSIAN EDUCATION API")
        try:
            response = requests.get(
                "http://localhost:5001/api/russian-education/search-russian-content?query=урок 2",
                timeout=5
            )
            print(f"📡 API /russian-education/search status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Results count: {data.get('count', 0)}")
                print(f"   Filters used: {data.get('filters', {})}")
            else:
                print(f"   Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Russian education API test failed: {e}")
        
        # client.close() removed - Weaviate client manages connections automatically
        print("\n🎉 DIAGNOSTICS COMPLETE!")
        
    except Exception as e:
        print(f"❌ Fatal error in diagnostics: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_knowledge_database() 