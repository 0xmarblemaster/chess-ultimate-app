#!/usr/bin/env python3
"""
Test Learning API Integration with Weaviate

This script tests the integration between the Learning API and Weaviate database
to ensure lessons and exercises are properly fetched and structured.
"""

import requests
import json
import weaviate

def test_weaviate_connection():
    """Test connection to Weaviate and check for lesson data"""
    print("🔍 Testing Weaviate Connection...")
    
    try:
        client = weaviate.connect_to_local()
        print("✅ Connected to Weaviate")
        
        # Check ChessLessonChunk collection
        try:
            collection = client.collections.get("ChessLessonChunk")
            response = collection.query.fetch_objects(limit=5)
            
            if response.objects:
                print(f"✅ Found {len(response.objects)} lesson chunks")
                
                # Show sample content
                for i, obj in enumerate(response.objects[:2]):
                    print(f"\n📝 Sample Chunk {i+1}:")
                    props = obj.properties
                    print(f"   Book: {props.get('book_title', 'N/A')}")
                    print(f"   Lesson: {props.get('lesson_number', 'N/A')}")
                    print(f"   Type: {props.get('type', 'N/A')}")
                    print(f"   Content: {str(props.get('content', props.get('text', 'N/A')))[:100]}...")
                
                return True
            else:
                print("❌ No lesson chunks found in database")
                return False
                
        except Exception as e:
            print(f"❌ Error accessing ChessLessonChunk: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        return False
    finally:
        try:
            # client.close() removed - Weaviate client manages connections automatically
        except:
            pass

def test_learning_api():
    """Test the Learning API endpoints"""
    print("\n🚀 Testing Learning API Endpoints...")
    
    base_url = "http://localhost:5001/api/learning"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Learning API is healthy")
        else:
            print(f"❌ Learning API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach Learning API: {e}")
        print("   Make sure the backend is running on localhost:5001")
        return False
    
    # Test documents endpoint
    try:
        response = requests.get(f"{base_url}/documents")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Documents endpoint working - found {data.get('total', 0)} documents")
            
            if data.get('documents'):
                for doc in data['documents'][:2]:
                    print(f"   📚 {doc.get('title', 'Untitled')}: {doc.get('lessonCount', 0)} lessons")
        else:
            print(f"❌ Documents endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing documents endpoint: {e}")
    
    # Test specific lesson endpoint
    lesson_id = "uroki_shachmaty_dlya_detei_lesson_2"
    try:
        response = requests.get(f"{base_url}/lessons/{lesson_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                lesson = data['lesson']
                print(f"✅ Lesson endpoint working")
                print(f"   📖 Title: {lesson.get('title', 'N/A')}")
                print(f"   📝 Content length: {len(lesson.get('content', ''))}")
                print(f"   🎯 Exercises: {lesson.get('metadata', {}).get('exerciseCount', 0)}")
                print(f"   📊 Diagrams: {lesson.get('metadata', {}).get('diagramCount', 0)}")
                
                # Test exercises endpoint
                ex_response = requests.get(f"{base_url}/lessons/{lesson_id}/exercises")
                if ex_response.status_code == 200:
                    ex_data = ex_response.json()
                    if ex_data.get('success'):
                        exercises = ex_data.get('exercises', [])
                        print(f"   ✅ Exercises endpoint working - {len(exercises)} exercises available")
                        
                        for i, exercise in enumerate(exercises[:3], 1):
                            print(f"      {i}. {exercise.get('instruction', 'No instruction')}")
                            if exercise.get('fen'):
                                print(f"         FEN: {exercise['fen'][:50]}...")
            else:
                print(f"❌ Lesson endpoint returned error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Lesson endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing lesson endpoint: {e}")
    
    return True

def test_exercise_loading():
    """Test exercise loading functionality"""
    print("\n🎯 Testing Exercise Loading...")
    
    base_url = "http://localhost:5001/api/learning"
    lesson_id = "uroki_shachmaty_dlya_detei_lesson_2"
    exercise_id = f"{lesson_id}:1"
    
    try:
        response = requests.post(f"{base_url}/exercises/{exercise_id}/load-to-board")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                board_data = data.get('boardData', {})
                exercise = board_data.get('exercise', {})
                print("✅ Exercise loading works!")
                print(f"   🎯 Exercise: {exercise.get('instruction', 'N/A')}")
                print(f"   🏁 FEN: {board_data.get('fen', 'N/A')[:50]}...")
                print(f"   💡 Hint: {exercise.get('hint', 'N/A')}")
                return True
            else:
                print(f"❌ Exercise loading failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Exercise loading request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing exercise loading: {e}")
    
    return False

def main():
    """Run all tests"""
    print("🚀 TESTING LEARNING API INTEGRATION")
    print("=" * 50)
    
    # Test Weaviate connection
    weaviate_ok = test_weaviate_connection()
    
    # Test Learning API
    api_ok = test_learning_api()
    
    # Test exercise loading
    exercise_ok = test_exercise_loading()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print(f"   Weaviate Connection: {'✅ PASS' if weaviate_ok else '❌ FAIL'}")
    print(f"   Learning API: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"   Exercise Loading: {'✅ PASS' if exercise_ok else '❌ FAIL'}")
    
    if weaviate_ok and api_ok and exercise_ok:
        print("\n🎉 ALL TESTS PASSED! Learning integration is working!")
        print("\n📚 Next steps:")
        print("   1. Open the frontend Learning page")
        print("   2. Select 'Как ходят фигуры' lesson")
        print("   3. Try loading exercises to the board")
    else:
        print("\n⚠️ Some tests failed. Please check the issues above.")
        if not weaviate_ok:
            print("   - Make sure Weaviate is running and has lesson data loaded")
        if not api_ok:
            print("   - Make sure the backend server is running on localhost:5001")

if __name__ == "__main__":
    main() 