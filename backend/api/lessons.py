"""
Lessons API - Phase 1
Endpoints for fetching courses, modules, and lessons
"""

from flask import Blueprint, jsonify, request
from services.supabase_client import supabase
from utils.auth import verify_clerk_token, get_current_user_id

lessons_bp = Blueprint('lessons', __name__)


@lessons_bp.route('/api/courses', methods=['GET'])
def get_courses():
    """
    Get all courses (public endpoint)

    Returns:
        [
            {
                "id": "uuid",
                "title": "Chess Fundamentals",
                "description": "Learn the basics...",
                "level": "beginner",
                "order_index": 1
            }
        ]
    """
    try:
        result = supabase.table('courses').select('*').order('order_index').execute()
        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch courses: {str(e)}"}), 500


@lessons_bp.route('/api/courses/<course_id>/modules', methods=['GET'])
def get_course_modules(course_id):
    """
    Get all modules for a specific course

    Args:
        course_id: UUID of the course

    Returns:
        [
            {
                "id": "uuid",
                "course_id": "uuid",
                "title": "Tactical Motifs",
                "description": "Learn basic patterns",
                "order_index": 1
            }
        ]
    """
    try:
        result = supabase.table('modules')\
            .select('*')\
            .eq('course_id', course_id)\
            .order('order_index')\
            .execute()

        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch modules: {str(e)}"}), 500


@lessons_bp.route('/api/modules/<module_id>/lessons', methods=['GET'])
def get_module_lessons(module_id):
    """
    Get all lessons for a specific module

    Args:
        module_id: UUID of the module

    Returns:
        [
            {
                "id": "uuid",
                "module_id": "uuid",
                "title": "Introduction to Forks",
                "lesson_type": "theory",
                "order_index": 1
            }
        ]
    """
    try:
        result = supabase.table('lessons')\
            .select('*')\
            .eq('module_id', module_id)\
            .order('order_index')\
            .execute()

        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch lessons: {str(e)}"}), 500


@lessons_bp.route('/api/lessons/<lesson_id>', methods=['GET'])
@verify_clerk_token
def get_lesson(lesson_id):
    """
    Get specific lesson content by ID (requires authentication)

    Args:
        lesson_id: UUID of the lesson

    Returns:
        {
            "id": "uuid",
            "title": "Introduction to Forks",
            "content": "# What is a Fork?...",
            "lesson_type": "theory",
            "exercise_fen": "...",
            "exercise_solution": [...]
        }
    """
    try:
        user_id = get_current_user_id()

        # Fetch lesson
        result = supabase.table('lessons')\
            .select('*')\
            .eq('id', lesson_id)\
            .execute()

        if not result.data:
            return jsonify({"error": "Lesson not found"}), 404

        lesson = result.data[0]

        # Check if lesson is locked (requires previous lesson completion)
        if lesson.get('requires_lesson_id'):
            # Check if user completed required lesson
            progress = supabase.table('user_progress')\
                .select('status')\
                .eq('user_id', user_id)\
                .eq('lesson_id', lesson['requires_lesson_id'])\
                .execute()

            if not progress.data or progress.data[0].get('status') != 'completed':
                return jsonify({
                    "error": "Lesson locked",
                    "requires_lesson_id": lesson['requires_lesson_id']
                }), 403

        return jsonify(lesson), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch lesson: {str(e)}"}), 500


@lessons_bp.route('/api/lessons/<lesson_id>/progress', methods=['GET'])
@verify_clerk_token
def get_lesson_progress(lesson_id):
    """
    Get user's progress for a specific lesson

    Returns:
        {
            "status": "in_progress",
            "started_at": "2025-01-09T...",
            "time_spent_seconds": 120,
            "score": null
        }
    """
    try:
        user_id = get_current_user_id()

        result = supabase.table('user_progress')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('lesson_id', lesson_id)\
            .execute()

        if not result.data:
            # No progress yet - return default
            return jsonify({
                "status": "not_started",
                "started_at": None,
                "completed_at": None,
                "time_spent_seconds": 0,
                "score": None
            }), 200

        return jsonify(result.data[0]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch progress: {str(e)}"}), 500


@lessons_bp.route('/api/lessons/<lesson_id>/progress', methods=['POST'])
@verify_clerk_token
def update_lesson_progress(lesson_id):
    """
    Update user's progress for a specific lesson

    Request body:
        {
            "status": "in_progress" | "completed",
            "time_spent_seconds": 120,
            "score": 85  # Optional, for quiz/exercise lessons
        }

    Returns:
        Updated progress object
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        # Build update object
        update_data = {
            'user_id': user_id,
            'lesson_id': lesson_id,
            'status': data.get('status', 'in_progress'),
            'updated_at': 'now()'
        }

        # Add optional fields
        if 'time_spent_seconds' in data:
            update_data['time_spent_seconds'] = data['time_spent_seconds']

        if 'score' in data:
            update_data['score'] = data['score']

        # Set started_at if not started yet
        if data.get('status') == 'in_progress':
            # Check if progress exists
            existing = supabase.table('user_progress')\
                .select('started_at')\
                .eq('user_id', user_id)\
                .eq('lesson_id', lesson_id)\
                .execute()

            if not existing.data or not existing.data[0].get('started_at'):
                update_data['started_at'] = 'now()'

        # Set completed_at if completing
        if data.get('status') == 'completed':
            update_data['completed_at'] = 'now()'

        # Upsert progress
        result = supabase.table('user_progress')\
            .upsert(update_data, on_conflict='user_id,lesson_id')\
            .execute()

        return jsonify(result.data[0]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to update progress: {str(e)}"}), 500


@lessons_bp.route('/api/lessons/<lesson_id>/chat', methods=['GET'])
@verify_clerk_token
def get_lesson_chat(lesson_id):
    """
    Get chat history for a specific lesson

    Returns:
        {
            "messages": [
                {"role": "user", "content": "What is a fork?"},
                {"role": "assistant", "content": "A fork is..."}
            ]
        }
    """
    try:
        user_id = get_current_user_id()

        result = supabase.table('lesson_chat_history')\
            .select('messages')\
            .eq('user_id', user_id)\
            .eq('lesson_id', lesson_id)\
            .execute()

        if not result.data:
            return jsonify({"messages": []}), 200

        return jsonify(result.data[0]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch chat history: {str(e)}"}), 500


@lessons_bp.route('/api/lessons/<lesson_id>/chat', methods=['POST'])
@verify_clerk_token
def send_lesson_chat(lesson_id):
    """
    Send a message to the AI tutor for this lesson

    Request body:
        {
            "message": "What is the best move in this position?"
        }

    Returns:
        {
            "response": "The best move is...",
            "messages": [...]  # Full chat history
        }
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        user_message = data.get('message')

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Get lesson context
        lesson_result = supabase.table('lessons')\
            .select('*')\
            .eq('id', lesson_id)\
            .execute()

        if not lesson_result.data:
            return jsonify({"error": "Lesson not found"}), 404

        lesson = lesson_result.data[0]
        lesson_content = lesson.get('content', '')
        lesson_title = lesson.get('title', '')

        # Get existing chat history
        history_result = supabase.table('lesson_chat_history')\
            .select('messages')\
            .eq('user_id', user_id)\
            .eq('lesson_id', lesson_id)\
            .execute()

        messages = history_result.data[0]['messages'] if history_result.data else []

        # Call LLM (using existing llm module)
        try:
            from llm.anthropic_llm import AnthropicLLM
            llm = AnthropicLLM()

            system_prompt = f"""You are a friendly and knowledgeable chess tutor helping a student with this lesson:

**Lesson: {lesson_title}**

{lesson_content}

Answer the student's questions about this lesson. Be encouraging, clear, and patient. Use examples when helpful."""

            # Prepare conversation history for LLM
            llm_messages = []
            for msg in messages:
                llm_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            llm_messages.append({'role': 'user', 'content': user_message})

            response = llm.generate(
                messages=llm_messages,
                system=system_prompt
            )

        except Exception as llm_error:
            # Fallback to simple response if LLM fails
            response = f"I'm here to help with the lesson '{lesson_title}'. However, I'm having trouble processing your question right now. Please try again or rephrase your question."

        # Update chat history
        messages.append({'role': 'user', 'content': user_message})
        messages.append({'role': 'assistant', 'content': response})

        # Save to database
        supabase.table('lesson_chat_history')\
            .upsert({
                'user_id': user_id,
                'lesson_id': lesson_id,
                'messages': messages,
                'updated_at': 'now()'
            }, on_conflict='user_id,lesson_id')\
            .execute()

        return jsonify({
            'response': response,
            'messages': messages
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to process chat message: {str(e)}"}), 500
