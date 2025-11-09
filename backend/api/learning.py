"""
Learning Mode API

Provides endpoints for the Learning Mode functionality:
- Document management and discovery
- Lesson content retrieval
- Exercise generation and validation
- Progress tracking
"""

import logging
from flask import Blueprint, jsonify, request
from typing import Dict, Any, List, Optional
import json

# Local imports from backend directory
from database.lesson_repository import LessonRepository
from services.vector_store_service import VectorStoreService
from etl import config as etl_config

logger = logging.getLogger(__name__)

# Create blueprint for learning mode API
learning_api = Blueprint('learning_api', __name__, url_prefix='/api/learning')

# Initialize lesson repository with error handling
try:
    lesson_repo = LessonRepository()
    logger.info("Lesson repository initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize lesson repository: {e}")
    lesson_repo = None

@learning_api.route('/documents', methods=['GET'])
def get_documents():
    """
    Get list of available documents/books for learning mode.
    
    Returns:
        JSON response with documents list and metadata
    """
    try:
        # Check if lesson repository is available and healthy
        logger.info(f"Checking lesson repository: lesson_repo={lesson_repo is not None}")
        
        repo_healthy = False
        if lesson_repo:
            try:
                repo_healthy = lesson_repo.healthcheck()
                logger.info(f"Lesson repository healthcheck result: {repo_healthy}")
            except Exception as e:
                logger.warning(f"Healthcheck failed with error: {e}")
                repo_healthy = False
        else:
            logger.info("Lesson repository is None")
        
        if not lesson_repo or not repo_healthy:
            # Fallback to mock data for development/testing
            logger.warning("Lesson repository unavailable or unhealthy, using mock data")
            mock_documents = [
                {
                    'id': 'uroki_shachmaty_dlya_detei',
                    'title': 'Уроки шахмат для детей',
                    'author': 'Chess Education',
                    'language': 'ru',
                    'lessonCount': 12,
                    'chunkCount': 48,
                    'difficulty': 'beginner',
                    'topics': ['tactics', 'checkmate', 'opening'],
                    'progress': {
                        'completedLessons': 0,
                        'totalLessons': 12
                    }
                },
                {
                    'id': 'basic_chess_tactics',
                    'title': 'Basic Chess Tactics',
                    'author': 'Chess Academy',
                    'language': 'en',
                    'lessonCount': 8,
                    'chunkCount': 32,
                    'difficulty': 'intermediate',
                    'topics': ['tactics', 'combinations', 'pins'],
                    'progress': {
                        'completedLessons': 2,
                        'totalLessons': 8
                    }
                },
                {
                    'id': 'endgame_fundamentals',
                    'title': 'Endgame Fundamentals',
                    'author': 'IM Smith',
                    'language': 'en',
                    'lessonCount': 15,
                    'chunkCount': 60,
                    'difficulty': 'advanced',
                    'topics': ['endgame', 'king_pawn', 'rook_endgame'],
                    'progress': {
                        'completedLessons': 0,
                        'totalLessons': 15
                    }
                }
            ]
            
            return jsonify({
                'success': True,
                'documents': mock_documents,
                'total': len(mock_documents),
                'note': 'Using mock data - vector store unavailable'
            })
        
        # If we reach here, repo is healthy - try to use it
        try:
            # Additional check: ensure vector store client is available
            if not hasattr(lesson_repo, 'vector_store') or not lesson_repo.vector_store or not lesson_repo.vector_store.client:
                raise Exception("Vector store client is not available")
                
            # Query the lesson repository to get unique books/documents
            query = """
            {
              Aggregate {
                ChessLessonChunk {
                  meta {
                    count
                  }
                  groupedBy: ["book"] {
                    value
                    groupedBy: ["difficulty"] {
                      value
                    }
                    groupedBy: ["topics"] {
                      value
                    }
                  }
                }
              }
            }
            """
            
            # Get unique books using Weaviate aggregation
            result = lesson_repo.vector_store.client.query.raw(query)
            
            # Process the aggregation result to create document list
            documents = []
            if result.get('data', {}).get('Aggregate', {}).get('ChessLessonChunk'):
                aggregation = result['data']['Aggregate']['ChessLessonChunk']
                
                # Extract grouped data
                book_groups = aggregation.get('groupedBy', [])
                for book_group in book_groups:
                    book_title = book_group.get('value')
                    if book_title:
                        # Get additional metadata for this book
                        book_chunks = lesson_repo.get_lessons_by_book(book_title)
                        
                        # Extract topics and difficulty levels
                        topics = set()
                        difficulties = set()
                        lesson_numbers = set()
                        
                        for chunk in book_chunks:
                            if chunk.get('topics'):
                                topics.update(chunk['topics'])
                            if chunk.get('difficulty'):
                                difficulties.add(chunk['difficulty'])
                            if chunk.get('lessonNumber'):
                                lesson_numbers.add(chunk['lessonNumber'])
                        
                        # Determine primary language (Russian or English)
                        language = 'ru' if any('УРОК' in chunk.get('content', '') for chunk in book_chunks[:5]) else 'en'
                        
                        document = {
                            'id': book_title.replace(' ', '_').lower(),
                            'title': book_title,
                            'author': 'Chess Education',  # Could be extracted from metadata
                            'language': language,
                            'lessonCount': len(lesson_numbers),
                            'chunkCount': len(book_chunks),
                            'difficulty': list(difficulties)[0] if difficulties else 'intermediate',
                            'topics': list(topics)[:5],  # Limit to first 5 topics
                            'progress': {
                                'completedLessons': 0,  # TODO: Track user progress
                                'totalLessons': len(lesson_numbers)
                            }
                        }
                        documents.append(document)
            
            # Sort documents by title
            documents.sort(key=lambda x: x['title'])
            
            return jsonify({
                'success': True,
                'documents': documents,
                'total': len(documents)
            })
        except Exception as e:
            logger.warning(f"Failed to query vector store, falling back to mock data: {e}")
            # Fall back to mock data if vector store query fails
            mock_documents = [
                {
                    'id': 'uroki_shachmaty_dlya_detei',
                    'title': 'Уроки шахмат для детей',
                    'author': 'Chess Education',
                    'language': 'ru',
                    'lessonCount': 12,
                    'chunkCount': 48,
                    'difficulty': 'beginner',
                    'topics': ['tactics', 'checkmate', 'opening'],
                    'progress': {
                        'completedLessons': 0,
                        'totalLessons': 12
                    }
                },
                {
                    'id': 'basic_chess_tactics',
                    'title': 'Basic Chess Tactics',
                    'author': 'Chess Academy',
                    'language': 'en',
                    'lessonCount': 8,
                    'chunkCount': 32,
                    'difficulty': 'intermediate',
                    'topics': ['tactics', 'combinations', 'pins'],
                    'progress': {
                        'completedLessons': 2,
                        'totalLessons': 8
                    }
                },
                {
                    'id': 'endgame_fundamentals',
                    'title': 'Endgame Fundamentals',
                    'author': 'IM Smith',
                    'language': 'en',
                    'lessonCount': 15,
                    'chunkCount': 60,
                    'difficulty': 'advanced',
                    'topics': ['endgame', 'king_pawn', 'rook_endgame'],
                    'progress': {
                        'completedLessons': 0,
                        'totalLessons': 15
                    }
                }
            ]
            
            return jsonify({
                'success': True,
                'documents': mock_documents,
                'total': len(mock_documents),
                'note': 'Using mock data - vector store query failed'
            })
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch documents: {str(e)}'
        }), 500

@learning_api.route('/documents/<document_id>/lessons', methods=['GET'])
def get_document_lessons(document_id: str):
    """
    Get lessons for a specific document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        JSON response with lessons list
    """
    try:
        # Check if lesson repository is available and healthy
        repo_healthy = False
        if lesson_repo:
            try:
                repo_healthy = lesson_repo.healthcheck()
                logger.info(f"Lesson repository healthcheck result for lessons: {repo_healthy}")
            except Exception as e:
                logger.warning(f"Healthcheck failed for lessons with error: {e}")
                repo_healthy = False
        
        if not lesson_repo or not repo_healthy:
            # Fallback to mock data for development/testing
            logger.warning("Lesson repository unavailable or unhealthy, using mock lessons data")
            
            if document_id == 'uroki_shachmaty_dlya_detei':
                mock_lessons = [
                    {
                        'id': f"{document_id}_lesson_1",
                        'documentId': document_id,
                        'title': 'УРОК 1 - Знакомство с доской',
                        'content': 'В этом уроке мы изучим шахматную доску и расположение фигур.',
                        'exercises': [],
                        'order': 1,
                        'isCompleted': False,
                        'chunks': []
                    },
                    {
                        'id': f"{document_id}_lesson_2",
                        'documentId': document_id,
                        'title': 'УРОК 2 - Как ходят фигуры',
                        'content': 'Изучаем правила движения каждой шахматной фигуры.',
                        'exercises': [],
                        'order': 2,
                        'isCompleted': False,
                        'chunks': []
                    }
                ]
            elif document_id == 'basic_chess_tactics':
                mock_lessons = [
                    {
                        'id': f"{document_id}_lesson_1",
                        'documentId': document_id,
                        'title': 'Introduction to Tactics',
                        'content': 'Learn the fundamental tactical patterns in chess.',
                        'exercises': [],
                        'order': 1,
                        'isCompleted': False,
                        'chunks': []
                    },
                    {
                        'id': f"{document_id}_lesson_2",
                        'documentId': document_id,
                        'title': 'Pins and Skewers',
                        'content': 'Master the art of pins and skewers to win material.',
                        'exercises': [],
                        'order': 2,
                        'isCompleted': False,
                        'chunks': []
                    }
                ]
            else:
                mock_lessons = [
                    {
                        'id': f"{document_id}_lesson_1",
                        'documentId': document_id,
                        'title': 'Sample Lesson',
                        'content': 'This is a sample lesson for the selected document.',
                        'exercises': [],
                        'order': 1,
                        'isCompleted': False,
                        'chunks': []
                    }
                ]
            
            return jsonify({
                'success': True,
                'lessons': mock_lessons,
                'documentId': document_id,
                'total': len(mock_lessons),
                'note': 'Using mock data - vector store unavailable'
            })
        
        # If we reach here, repo is healthy - try to use it
        try:
            # Additional check: ensure repository methods are available
            if not hasattr(lesson_repo, 'get_lessons_by_book'):
                raise Exception("Repository methods not available")
                
            # Convert document ID back to book title
            book_title = document_id.replace('_', ' ').title()
            
            # Alternative approach: search for chunks that contain the document_id
            if not book_title:
                return jsonify({
                    'success': False,
                    'error': 'Invalid document ID'
                }), 400
            
            # Get all chunks for this book
            book_chunks = lesson_repo.get_lessons_by_book(book_title)
            
            # Group chunks by lesson number
            lessons_map = {}
            for chunk in book_chunks:
                lesson_num = chunk.get('lessonNumber', 1)
                if lesson_num not in lessons_map:
                    lessons_map[lesson_num] = {
                        'id': f"{document_id}_lesson_{lesson_num}",
                        'documentId': document_id,
                        'title': chunk.get('lessonTitle', f'Lesson {lesson_num}'),
                        'content': '',
                        'exercises': [],
                        'order': lesson_num,
                        'isCompleted': False,  # TODO: Track completion
                        'chunks': []
                    }
                
                # Add chunk to lesson
                lessons_map[lesson_num]['chunks'].append(chunk)
                
                # Build content from chunks
                if chunk.get('content'):
                    lessons_map[lesson_num]['content'] += chunk['content'] + '\n\n'
            
            # Convert to list and sort by order
            lessons = list(lessons_map.values())
            lessons.sort(key=lambda x: x['order'])
            
            return jsonify({
                'success': True,
                'lessons': lessons,
                'documentId': document_id,
                'total': len(lessons)
            })
        except Exception as e:
            logger.warning(f"Failed to query lessons from vector store, falling back to mock data: {e}")
            # Fall back to mock data if vector store query fails
            if document_id == 'uroki_shachmaty_dlya_detei':
                mock_lessons = [
                    {
                        'id': f"{document_id}_lesson_1",
                        'documentId': document_id,
                        'title': 'УРОК 1 - Знакомство с доской',
                        'content': 'В этом уроке мы изучим шахматную доску и расположение фигур.',
                        'exercises': [],
                        'order': 1,
                        'isCompleted': False,
                        'chunks': []
                    },
                    {
                        'id': f"{document_id}_lesson_2",
                        'documentId': document_id,
                        'title': 'УРОК 2 - Как ходят фигуры',
                        'content': 'Изучаем правила движения каждой шахматной фигуры.',
                        'exercises': [],
                        'order': 2,
                        'isCompleted': False,
                        'chunks': []
                    }
                ]
            elif document_id == 'basic_chess_tactics':
                mock_lessons = [
                    {
                        'id': f"{document_id}_lesson_1",
                        'documentId': document_id,
                        'title': 'Introduction to Tactics',
                        'content': 'Learn the fundamental tactical patterns in chess.',
                        'exercises': [],
                        'order': 1,
                        'isCompleted': False,
                        'chunks': []
                    },
                    {
                        'id': f"{document_id}_lesson_2",
                        'documentId': document_id,
                        'title': 'Pins and Skewers',
                        'content': 'Master the art of pins and skewers to win material.',
                        'exercises': [],
                        'order': 2,
                        'isCompleted': False,
                        'chunks': []
                    }
                ]
            else:
                mock_lessons = [
                    {
                        'id': f"{document_id}_lesson_1",
                        'documentId': document_id,
                        'title': 'Sample Lesson',
                        'content': 'This is a sample lesson for the selected document.',
                        'exercises': [],
                        'order': 1,
                        'isCompleted': False,
                        'chunks': []
                    }
                ]
            
            return jsonify({
                'success': True,
                'lessons': mock_lessons,
                'documentId': document_id,
                'total': len(mock_lessons),
                'note': 'Using mock data - vector store query failed'
            })
        
    except Exception as e:
        logger.error(f"Error fetching lessons for document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch lessons: {str(e)}'
        }), 500

@learning_api.route('/lessons/<lesson_id>', methods=['GET'])
def get_lesson_detail(lesson_id: str):
    """
    Get detailed lesson content with exercises from Weaviate.
    
    Args:
        lesson_id: Lesson identifier (e.g., 'uroki_shachmaty_dlya_detei_lesson_2')
        
    Returns:
        JSON response with lesson content, diagrams, and numbered exercises
    """
    try:
        logger.info(f"Fetching lesson details for: {lesson_id}")
        
        # Check if lesson repository is available and healthy
        repo_healthy = False
        if lesson_repo:
            try:
                repo_healthy = lesson_repo.healthcheck()
                logger.info(f"Lesson repository healthcheck result for lesson detail: {repo_healthy}")
            except Exception as e:
                logger.warning(f"Healthcheck failed for lesson detail with error: {e}")
                repo_healthy = False
        
        if not lesson_repo or not repo_healthy:
            logger.warning("Lesson repository unavailable, using mock data")
            mock_data = _get_mock_lesson_detail(lesson_id)
            return jsonify(mock_data)
        
        # Parse the lesson_id to extract document_id and lesson_number
        # Expected format: document_id_lesson_N
        parts = lesson_id.split('_lesson_')
        if len(parts) != 2:
            return jsonify({
                'success': False,
                'error': 'Invalid lesson ID format'
            }), 400
            
        document_id = parts[0]
        try:
            lesson_number = int(parts[1])
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid lesson number'
            }), 400
        
        # Query Weaviate for lesson chunks
        try:
            collection = lesson_repo.vector_store.client.collections.get("ChessLessonChunk")
            
            # Get all chunks for this lesson
            where_filter = {
                "operator": "And",
                "operands": [
                    {
                        "path": ["lesson_number"],
                        "operator": "Equal",
                        "valueText": str(lesson_number)
                    }
                ]
            }
            
            response = collection.query.fetch_objects(
                where=where_filter,
                limit=100
            )
            
            if not response.objects:
                logger.warning(f"No chunks found for lesson {lesson_id}")
                return jsonify({
                    'success': False,
                    'error': 'Lesson not found'
                }), 404
            
            # Process the chunks into lesson structure
            lesson_data = _process_lesson_chunks(response.objects, lesson_id, lesson_number)
            
            return jsonify({
                'success': True,
                'lesson': lesson_data
            })
            
        except Exception as e:
            logger.warning(f"Error querying Weaviate, falling back to mock data: {e}")
            mock_data = _get_mock_lesson_detail(lesson_id)
            return jsonify(mock_data)
        
    except Exception as e:
        logger.error(f"Error fetching lesson {lesson_id}: {e}")
        # Fall back to mock data on any error
        try:
            mock_data = _get_mock_lesson_detail(lesson_id)
            return jsonify(mock_data)
        except Exception as fallback_e:
            logger.error(f"Mock data fallback also failed: {fallback_e}")
            return jsonify({
                'success': False,
                'error': f'Failed to fetch lesson: {str(e)}'
            }), 500

def _process_lesson_chunks(chunks, lesson_id: str, lesson_number: int) -> Dict[str, Any]:
    """
    Process Weaviate chunks into structured lesson data with numbered exercises.
    
    Args:
        chunks: List of Weaviate objects
        lesson_id: Lesson identifier
        lesson_number: Lesson number
        
    Returns:
        Structured lesson data dictionary
    """
    # Extract basic lesson info from first chunk
    first_chunk = chunks[0]
    props = first_chunk.properties
    
    lesson_title = props.get('book_title', f'Lesson {lesson_number}')
    lesson_content = ""
    diagrams = []
    exercises = []
    exercise_counter = 1
    
    # Process chunks by type
    explanation_texts = []
    task_chunks = []
    
    for chunk in chunks:
        chunk_props = chunk.properties
        chunk_type = chunk_props.get('type', '')
        content = chunk_props.get('content', chunk_props.get('text', ''))
        
        if 'explanation' in chunk_type:
            explanation_texts.append(content)
        elif 'task' in chunk_type or 'general_task' in chunk_type:
            task_chunks.append(chunk_props)
    
    # Combine explanation text
    lesson_content = '\n\n'.join(explanation_texts)
    
    # Process tasks into numbered exercises
    for task_chunk in task_chunks:
        image_file = task_chunk.get('image', '')
        fen_string = task_chunk.get('fen', '')
        task_text = task_chunk.get('content', task_chunk.get('text', ''))
        
        # Create exercise object
        exercise = {
            'id': exercise_counter,
            'instruction': f"Exercise {exercise_counter}: {task_text if task_text and len(task_text) > 5 else 'Solve the position'}",
            'hint': 'Look for checkmate patterns or tactical motifs',
            'fen': fen_string,
            'image': image_file,
            'solution': [],  # Will be populated by AI analysis if needed
            'type': 'tactical_puzzle'
        }
        
        exercises.append(exercise)
        
        # Also add to diagrams if it has a position
        if fen_string or image_file:
            diagram = {
                'id': f'diagram_{exercise_counter}',
                'title': f'Position {exercise_counter}',
                'fen': fen_string,
                'image': image_file,
                'description': task_text
            }
            diagrams.append(diagram)
        
        exercise_counter += 1
    
    # If no exercises were found, create some based on the content
    if not exercises and lesson_content:
        exercises = _generate_exercises_from_content(lesson_content, lesson_number)
    
    return {
        'id': lesson_id,
        'title': lesson_title,
        'content': lesson_content,
        'diagrams': diagrams,
        'exercises': exercises,
        'metadata': {
            'exerciseCount': len(exercises),
            'diagramCount': len(diagrams),
            'topics': _extract_topics_from_content(lesson_content),
            'language': 'ru',
            'difficulty': 'beginner'
        }
    }

def _generate_exercises_from_content(content: str, lesson_number: int) -> List[Dict[str, Any]]:
    """Generate exercises based on lesson content when none exist."""
    exercises = []
    
    # Basic exercises based on lesson content themes
    if 'мат' in content.lower():
        exercises.append({
            'id': 1,
            'instruction': 'Exercise 1: Find checkmate in one move',
            'hint': 'Look for ways to attack the enemy king',
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'solution': [],
            'type': 'checkmate_puzzle'
        })
    
    if 'шах' in content.lower():
        exercises.append({
            'id': len(exercises) + 1,
            'instruction': f'Exercise {len(exercises) + 1}: Practice giving check',
            'hint': 'Attack the enemy king directly',
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'solution': [],
            'type': 'check_puzzle'
        })
    
    return exercises

def _extract_topics_from_content(content: str) -> List[str]:
    """Extract chess topics from lesson content."""
    topics = []
    content_lower = content.lower()
    
    topic_keywords = {
        'checkmate': ['мат', 'checkmate'],
        'check': ['шах', 'check'],
        'tactics': ['тактика', 'tactics'],
        'opening': ['дебют', 'opening'],
        'endgame': ['эндшпиль', 'endgame'],
        'pieces': ['фигур', 'pieces'],
        'rules': ['правил', 'rules']
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            topics.append(topic)
    
    return topics[:5]  # Limit to 5 topics

def _get_mock_lesson_detail(lesson_id: str) -> Dict[str, Any]:
    """Return mock lesson data when repository is unavailable."""
    
    # Extract lesson info from ID
    if 'uroki_shachmaty_dlya_detei' in lesson_id:
        if 'lesson_1' in lesson_id:
            return {
                'success': True,
                'lesson': {
                    'id': lesson_id,
                    'title': 'УРОК 1 - Знакомство с доской',
                    'content': '''Знакомство с шахматной доской

Шахматная доска состоит из 64 клеток - 32 светлых и 32 темных.
Доска всегда ставится так, чтобы справа от игрока была светлая угловая клетка.

Горизонтальные ряды называются горизонталями (1, 2, 3, 4, 5, 6, 7, 8).
Вертикальные ряды называются вертикалями (a, b, c, d, e, f, g, h).''',
                    'diagrams': [
                        {
                            'id': 'diagram_1',
                            'title': 'Starting Position',
                            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                            'description': 'Initial chess position'
                        }
                    ],
                    'exercises': [
                        {
                            'id': 1,
                            'instruction': 'Exercise 1: Identify the squares',
                            'hint': 'Each square has a unique name like e4, d5',
                            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                            'solution': [],
                            'type': 'square_identification'
                        }
                    ],
                    'metadata': {
                        'exerciseCount': 1,
                        'diagramCount': 1,
                        'topics': ['board', 'squares', 'notation'],
                        'language': 'ru',
                        'difficulty': 'beginner'
                    }
                }
            }
        elif 'lesson_2' in lesson_id:
            return {
                'success': True,
                'lesson': {
                    'id': lesson_id,
                    'title': 'УРОК 2 - Шах и мат',
                    'content': '''Шах и мат

Шах – это нападение(атака) на короля

Есть 3 защиты от шаха:
• Съесть(срубить) фигуру, которая угрожает
• Убежать королем  
• Закрыться своей фигурой

Мат – это шах от которого нет защиты.
Самая главная цель в партии – это поставить мат.''',
                    'diagrams': [
                        {
                            'id': 'diagram_1',
                            'title': 'Check Position',
                            'fen': 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
                            'description': 'Basic check position - King being attacked'
                        },
                        {
                            'id': 'diagram_2',
                            'title': 'Checkmate Example',
                            'fen': 'rnb1kbnr/pppp1ppp/8/4p2q/4P3/8/PPPP1PPP/RNBQKB1R w KQkq - 1 3',
                            'description': 'Example of checkmate - King cannot escape'
                        },
                        {
                            'id': 'diagram_3',
                            'title': 'Escaping Check',
                            'fen': 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 2 3',
                            'description': 'Position where King can escape from check'
                        }
                    ],
                    'exercises': [
                        {
                            'id': 1,
                            'instruction': 'Exercise 1: Find checkmate in one move',
                            'hint': 'Look for a way to attack the king with no escape',
                            'fen': 'rnb1kbnr/pppp1ppp/8/4p2q/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 3',
                            'solution': [{'from': 'd1', 'to': 'h5'}],
                            'type': 'checkmate_puzzle'
                        },
                        {
                            'id': 2,
                            'instruction': 'Exercise 2: Defend against check',
                            'hint': 'Block, capture, or move the king',
                            'fen': 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 2 3',
                            'solution': [],
                            'type': 'defense_puzzle'
                        }
                    ],
                    'metadata': {
                        'exerciseCount': 2,
                        'diagramCount': 3,
                        'topics': ['checkmate', 'check', 'tactics'],
                        'language': 'ru',
                        'difficulty': 'beginner'
                    }
                }
            }
    elif 'basic_chess_tactics' in lesson_id:
        if 'lesson_1' in lesson_id:
            return {
                'success': True,
                'lesson': {
                    'id': lesson_id,
                    'title': 'Introduction to Tactics',
                    'content': '''Introduction to Chess Tactics

Tactical patterns are short-term combinations that win material or achieve checkmate.
The most common tactical motifs include:
- Pins: Attacking a piece that cannot move without exposing a more valuable piece
- Forks: Attacking two or more pieces simultaneously
- Skewers: Forcing a valuable piece to move and capturing a less valuable piece behind it
- Discovered attacks: Moving one piece to reveal an attack from another piece''',
                    'diagrams': [
                        {
                            'id': 'diagram_1',
                            'title': 'Fork Example',
                            'fen': 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/3P1N2/PPP2PPP/RNBQKB1R b KQkq - 0 4',
                            'description': 'Knight fork attacking king and rook'
                        }
                    ],
                    'exercises': [
                        {
                            'id': 1,
                            'instruction': 'Exercise 1: Find the fork',
                            'hint': 'Look for a knight move that attacks two pieces',
                            'fen': 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/3P4/PPP2PPP/RNBQKBNR w KQkq - 1 4',
                            'solution': [{'from': 'g1', 'to': 'f3'}],
                            'type': 'tactical_puzzle'
                        }
                    ],
                    'metadata': {
                        'exerciseCount': 1,
                        'diagramCount': 1,
                        'topics': ['tactics', 'fork', 'pins'],
                        'language': 'en',
                        'difficulty': 'intermediate'
                    }
                }
            }
        elif 'lesson_2' in lesson_id:
            return {
                'success': True,
                'lesson': {
                    'id': lesson_id,
                    'title': 'Pins and Skewers',
                    'content': '''Pins and Skewers

A pin is a tactic where a piece cannot or should not move because it would expose a more valuable piece to attack.

A skewer is a tactic where a valuable piece is attacked and must move, exposing a less valuable piece behind it to capture.

Both tactics exploit the alignment of pieces on ranks, files, or diagonals.''',
                    'diagrams': [
                        {
                            'id': 'diagram_1',
                            'title': 'Pin Example',
                            'fen': 'rnbqk2r/pppp1ppp/5n2/2b1p3/4P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 2 5',
                            'description': 'Bishop pins knight to king'
                        }
                    ],
                    'exercises': [
                        {
                            'id': 1,
                            'instruction': 'Exercise 1: Find the pin',
                            'hint': 'Look for a way to attack a piece that cannot move',
                            'fen': 'rnbqk2r/pppp1ppp/5n2/4p3/1b2P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 1 5',
                            'solution': [{'from': 'c1', 'to': 'g5'}],
                            'type': 'tactical_puzzle'
                        }
                    ],
                    'metadata': {
                        'exerciseCount': 1,
                        'diagramCount': 1,
                        'topics': ['tactics', 'pins', 'skewer'],
                        'language': 'en',
                        'difficulty': 'intermediate'
                    }
                }
            }
    
    # Default fallback for any lesson
    return {
        'success': True,
        'lesson': {
            'id': lesson_id,
            'title': 'Sample Lesson',
            'content': '''This is a sample lesson with basic chess content.

When the vector store is unavailable, you see this mock content.
The lesson would normally contain rich chess education material with diagrams and exercises.''',
            'diagrams': [
                {
                    'id': 'diagram_1',
                    'title': 'Starting Position',
                    'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                    'description': 'Standard chess starting position'
                }
            ],
            'exercises': [
                {
                    'id': 1,
                    'instruction': 'Exercise 1: Make the best move',
                    'hint': 'Control the center with a pawn',
                    'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                    'solution': [{'from': 'e2', 'to': 'e4'}],
                    'type': 'opening_puzzle'
                }
            ],
            'metadata': {
                'exerciseCount': 1,
                'diagramCount': 1,
                'topics': ['general'],
                'language': 'en',
                'difficulty': 'beginner'
            }
        }
    }

@learning_api.route('/exercises/validate', methods=['POST'])
def validate_exercise():
    """
    Validate a user's exercise solution.
    
    Expected JSON body:
    {
        "exerciseId": "string",
        "userMoves": [{"from": "e2", "to": "e4", "promotion": "q"}],
        "position": "fen_string"
    }
    
    Returns:
        JSON response with validation result
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        exercise_id = data.get('exerciseId')
        user_moves = data.get('userMoves', [])
        position = data.get('position')
        
        if not exercise_id:
            return jsonify({
                'success': False,
                'error': 'Exercise ID is required'
            }), 400
        
        # TODO: Implement actual move validation using Stockfish or chess.js
        # For now, return a mock validation response
        
        # Simple validation: check if moves are provided
        is_correct = len(user_moves) > 0
        
        validation_result = {
            'exerciseId': exercise_id,
            'isCorrect': is_correct,
            'feedback': 'Good move!' if is_correct else 'Try a different approach.',
            'correctMoves': [],  # TODO: Get from solution or calculate
            'explanation': 'Move validation explanation would go here.',
            'score': 100 if is_correct else 0,
            'hintsUsed': 0
        }
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        logger.error(f"Error validating exercise: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to validate exercise: {str(e)}'
        }), 500

@learning_api.route('/progress/<user_id>', methods=['GET'])
def get_user_progress(user_id: str):
    """
    Get learning progress for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        JSON response with user progress data
    """
    try:
        # TODO: Implement actual progress tracking
        # For now, return mock progress data
        
        progress = {
            'userId': user_id,
            'documentsStarted': 2,
            'lessonsCompleted': 5,
            'exercisesSolved': 23,
            'totalStudyTime': 180,  # minutes
            'streak': 3,  # days
            'achievements': [
                {'id': 'first_lesson', 'title': 'First Lesson', 'unlockedAt': '2023-12-01'},
                {'id': 'tactical_master', 'title': 'Tactical Master', 'unlockedAt': '2023-12-05'}
            ],
            'recentActivity': [
                {'type': 'lesson_completed', 'lessonId': 'uroka_2_lesson_1', 'timestamp': '2023-12-10T10:30:00Z'},
                {'type': 'exercise_solved', 'exerciseId': 'ex_123', 'timestamp': '2023-12-10T10:25:00Z'}
            ]
        }
        
        return jsonify({
            'success': True,
            'progress': progress
        })
        
    except Exception as e:
        logger.error(f"Error fetching progress for user {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch progress: {str(e)}'
        }), 500

@learning_api.route('/progress/<user_id>/lesson/<lesson_id>', methods=['POST'])
def update_lesson_progress(user_id: str, lesson_id: str):
    """
    Update progress for a specific lesson.
    
    Expected JSON body:
    {
        "status": "completed|started|in_progress",
        "timeSpent": 300,
        "score": 85
    }
    
    Args:
        user_id: User identifier
        lesson_id: Lesson identifier
        
    Returns:
        JSON response confirming update
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        status = data.get('status', 'in_progress')
        time_spent = data.get('timeSpent', 0)
        score = data.get('score', 0)
        
        # TODO: Store progress in database
        # For now, just return success
        
        return jsonify({
            'success': True,
            'message': f'Progress updated for lesson {lesson_id}',
            'data': {
                'userId': user_id,
                'lessonId': lesson_id,
                'status': status,
                'timeSpent': time_spent,
                'score': score
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating progress for user {user_id}, lesson {lesson_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to update progress: {str(e)}'
        }), 500

@learning_api.route('/search', methods=['POST'])
def search_content():
    """
    Search through lesson content.
    
    Expected JSON body:
    {
        "query": "search_text",
        "filters": {
            "difficulty": "beginner",
            "topics": ["tactics"],
            "chunkType": "task"
        },
        "limit": 10
    }
    
    Returns:
        JSON response with search results
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        query = data.get('query', '')
        filters = data.get('filters', {})
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        # Use lesson repository to search
        search_results = lesson_repo.search_lessons(query, limit=limit, filters=filters)
        
        # Format results for frontend
        formatted_results = []
        for result in search_results:
            formatted_result = {
                'id': result.get('chunkId'),
                'title': result.get('lessonTitle', 'Untitled'),
                'content': result.get('content', '')[:200] + '...',
                'book': result.get('book'),
                'lessonNumber': result.get('lessonNumber'),
                'chunkType': result.get('chunkType'),
                'difficulty': result.get('difficulty'),
                'topics': result.get('topics', []),
                'fen': result.get('fen'),
                'score': result.get('_additional', {}).get('score', 0)
            }
            formatted_results.append(formatted_result)
        
        return jsonify({
            'success': True,
            'results': formatted_results,
            'query': query,
            'total': len(formatted_results)
        })
        
    except Exception as e:
        logger.error(f"Error searching content: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to search content: {str(e)}'
        }), 500

@learning_api.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for learning mode API.
    
    Returns:
        JSON response with health status
    """
    try:
        # Check lesson repository health
        repo_healthy = lesson_repo and lesson_repo.healthcheck()
        
        return jsonify({
            'success': True,
            'status': 'healthy' if repo_healthy else 'degraded',
            'components': {
                'lesson_repository': 'healthy' if repo_healthy else 'unhealthy',
                'vector_store': 'healthy' if repo_healthy else 'unhealthy'
            }
        })
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@learning_api.route('/exercises/<lesson_id>/<int:exercise_number>/load-to-board', methods=['POST'])
def load_exercise_to_board(lesson_id: str, exercise_number: int):
    """
    Load an exercise position to the chess board for solving.
    
    Args:
        lesson_id: Lesson identifier  
        exercise_number: Exercise number (1-based)
        
    Returns:
        JSON response with board position and exercise details
    """
    try:
        # Check if lesson repository is available and healthy
        repo_healthy = False
        if lesson_repo:
            try:
                repo_healthy = lesson_repo.healthcheck()
                logger.info(f"Lesson repository healthcheck result for lessons: {repo_healthy}")
            except Exception as e:
                logger.warning(f"Healthcheck failed for lessons with error: {e}")
                repo_healthy = False
        
        if not lesson_repo or not repo_healthy:
            # Use mock data when repository is not available
            mock_response = _get_mock_lesson_detail(lesson_id)
            if not mock_response or not mock_response.get('success'):
                return jsonify({
                    'success': False,
                    'error': 'Lesson not found'
                }), 404
            # Extract lesson data from the mock response
            lesson = mock_response['lesson']
        else:
            try:
                lesson = lesson_repo.get_lesson_by_id(lesson_id)
                if not lesson:
                    mock_response = _get_mock_lesson_detail(lesson_id)
                    if not mock_response or not mock_response.get('success'):
                        return jsonify({
                            'success': False,
                            'error': 'Lesson not found'
                        }), 404
                    # Extract lesson data from the mock response
                    lesson = mock_response['lesson']
            except Exception as e:
                logger.warning(f"Repository error, falling back to mock data: {e}")
                mock_response = _get_mock_lesson_detail(lesson_id)
                if not mock_response or not mock_response.get('success'):
                    return jsonify({
                        'success': False,
                        'error': 'Lesson not found'
                    }), 404
                # Extract lesson data from the mock response
                lesson = mock_response['lesson']
        
        exercises = lesson.get('exercises', [])
        
        # Find the specific exercise by number (1-based)
        target_exercise = None
        for exercise in exercises:
            if exercise.get('id') == exercise_number:
                target_exercise = exercise
                break
        
        if not target_exercise:
            return jsonify({
                'success': False,
                'error': f'Exercise {exercise_number} not found in lesson'
            }), 404
        
        # Prepare the board data
        board_data = {
            'fen': target_exercise.get('fen', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'),
            'exercise': {
                'id': target_exercise['id'],
                'instruction': target_exercise['instruction'],
                'hint': target_exercise.get('hint', ''),
                'type': target_exercise.get('type', 'tactical_puzzle'),
                'solution': target_exercise.get('solution', []),
                'lessonTitle': lesson.get('title', 'Unknown Lesson')
            },
            'metadata': {
                'lessonId': lesson_id,
                'exerciseNumber': exercise_number,
                'totalExercises': len(exercises)
            }
        }
        
        return jsonify({
            'success': True,
            'boardData': board_data,
            'message': f'Exercise {exercise_number} loaded to board'
        })
        
    except Exception as e:
        logger.error(f"Error loading exercise {lesson_id}:{exercise_number} to board: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to load exercise: {str(e)}'
        }), 500

@learning_api.route('/lessons/<lesson_id>/exercises', methods=['GET'])
def get_lesson_exercises(lesson_id: str):
    """
    Get all exercises for a specific lesson with their positions.
    
    Args:
        lesson_id: Lesson identifier
        
    Returns:
        JSON response with numbered exercises
    """
    try:
        # Get the lesson details
        lesson_response = get_lesson_detail(lesson_id)
        if lesson_response[1] != 200:
            return jsonify({
                'success': False,
                'error': 'Lesson not found'
            }), 404
        
        lesson_data = lesson_response[0].get_json()
        if not lesson_data.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to fetch lesson data'
            }), 500
        
        lesson = lesson_data['lesson']
        exercises = lesson.get('exercises', [])
        
        # Format exercises with additional metadata
        formatted_exercises = []
        for i, exercise in enumerate(exercises, 1):
            formatted_exercise = {
                'id': exercise.get('id', i),
                'number': i,
                'instruction': exercise.get('instruction', f'Exercise {i}'),
                'hint': exercise.get('hint', ''),
                'type': exercise.get('type', 'tactical_puzzle'),
                'fen': exercise.get('fen', ''),
                'image': exercise.get('image', ''),
                'hasPosition': bool(exercise.get('fen') or exercise.get('image')),
                'loadUrl': f'/api/learning/exercises/{lesson_id}/{i}/load-to-board'
            }
            formatted_exercises.append(formatted_exercise)
        
        return jsonify({
            'success': True,
            'exercises': formatted_exercises,
            'lessonTitle': lesson['title'],
            'totalExercises': len(formatted_exercises)
        })
        
    except Exception as e:
        logger.error(f"Error fetching lesson exercises {lesson_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch exercises: {str(e)}'
        }), 500

# Error handlers for the blueprint
@learning_api.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@learning_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500 