"""
Chat API - Server-managed LLM chat endpoints for analysis tools

Provides endpoints for:
- Position analysis chat
- Game analysis chat
- Puzzle chat
- Conversation management

All endpoints require Clerk authentication and enforce rate limits.
"""

import asyncio
import logging
from flask import Blueprint, request, jsonify, g
from functools import wraps

from utils.auth import verify_clerk_token, get_current_user_id
from services.llm_session_manager import get_session_manager, LLMRequest
from services.conversation_manager import get_conversation_manager
from services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# Create Blueprint
chat_bp = Blueprint('chat', __name__)

# Get service instances
session_manager = get_session_manager()
conversation_manager = get_conversation_manager()
rate_limiter = get_rate_limiter()


def async_route(f):
    """Decorator to run async route handlers"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@chat_bp.route('/api/chat/analysis', methods=['POST'])
@verify_clerk_token
@async_route
async def chat_analysis():
    """
    Chat endpoint for position/game analysis.

    Request body:
    {
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "query": "What is the best move here?",
        "conversation_id": "optional-uuid",  // Reuse existing conversation
        "context_type": "position" | "game" | "general"  // Default: "analysis"
    }

    Response:
    {
        "success": true,
        "response": "The best move is...",
        "conversation_id": "uuid",
        "tokens_used": 150,
        "usage": {
            "hourly_remaining": 45,
            "daily_remaining": 195
        }
    }
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        # Validate required fields
        if not data or 'fen' not in data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: fen, query'
            }), 400

        fen = data['fen']
        query = data['query'].strip()
        conversation_id = data.get('conversation_id')
        context_type = data.get('context_type', 'analysis')

        # Validate inputs
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query cannot be empty'
            }), 400

        if len(query) > 2000:
            return jsonify({
                'success': False,
                'error': 'Query too long (max 2000 characters)'
            }), 400

        # Check rate limits
        allowed, reason = rate_limiter.check_rate_limit(user_id)
        if not allowed:
            logger.warning(f"Rate limit exceeded for user {user_id[:8]}...: {reason}")
            return jsonify({
                'success': False,
                'error': reason,
                'rate_limited': True
            }), 429

        # Get or create conversation
        if conversation_id:
            # Verify user owns this conversation
            conversations = conversation_manager.get_user_conversations(
                user_id,
                limit=100
            )
            if not any(c['id'] == conversation_id for c in conversations):
                return jsonify({
                    'success': False,
                    'error': 'Conversation not found or access denied'
                }), 404

            context = conversation_manager.get_context(conversation_id)
        else:
            # Create new conversation
            conversation_id = conversation_manager.create_conversation(
                user_id=user_id,
                conversation_type=context_type,
                context={'fen': fen}
            )
            context = []

        # Save user message
        conversation_manager.save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role='user',
            content=query,
            fen=fen
        )

        # Create LLM request
        llm_request = LLMRequest(
            user_id=user_id,
            fen=fen,
            query=query,
            conversation_id=conversation_id,
            context=context
        )

        # Execute LLM request
        logger.info(f"Executing chat request: user={user_id[:8]}..., conv={conversation_id[:8]}...")
        response = await session_manager.execute_request(llm_request)

        # Set g variables for performance monitoring middleware
        g.tokens_used = response.tokens_used
        g.model_used = response.model
        g.conversation_id = conversation_id

        if not response.success:
            # Set error message for monitoring
            g.error_message = response.error
            logger.error(f"LLM request failed: {response.error}")
            return jsonify({
                'success': False,
                'error': 'Failed to generate AI response. Please try again.',
                'details': response.error
            }), 500

        # Save assistant message
        conversation_manager.save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role='assistant',
            content=response.content,
            fen=fen,
            tokens_used=response.tokens_used,
            model=response.model
        )

        # Track usage for rate limiting
        rate_limiter.track_request(user_id, response.tokens_used)

        # Get updated usage stats
        usage_stats = rate_limiter.get_user_usage(user_id)

        logger.info(
            f"Chat request completed: user={user_id[:8]}..., "
            f"tokens={response.tokens_used}, time={response.response_time_ms:.0f}ms"
        )

        return jsonify({
            'success': True,
            'response': response.content,
            'conversation_id': conversation_id,
            'tokens_used': response.tokens_used,
            'response_time_ms': response.response_time_ms,
            'usage': {
                'hourly_remaining': usage_stats.get('hourly', {}).get('requests_remaining', 0),
                'daily_remaining': usage_stats.get('daily', {}).get('requests_remaining', 0),
                'tier': usage_stats.get('tier', 'free')
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in chat_analysis: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@chat_bp.route('/api/chat/history/<conversation_id>', methods=['GET'])
@verify_clerk_token
def get_chat_history(conversation_id):
    """
    Get conversation history.

    Response:
    {
        "success": true,
        "conversation": {
            "id": "uuid",
            "type": "position",
            "created_at": "2025-01-10T...",
            "updated_at": "2025-01-10T..."
        },
        "messages": [
            {
                "role": "user",
                "content": "What is the best move?",
                "timestamp": "2025-01-10T..."
            },
            ...
        ]
    }
    """
    try:
        user_id = get_current_user_id()

        # Verify user owns this conversation
        conversations = conversation_manager.get_user_conversations(user_id, limit=100)
        conversation = next((c for c in conversations if c['id'] == conversation_id), None)

        if not conversation:
            return jsonify({
                'success': False,
                'error': 'Conversation not found or access denied'
            }), 404

        # Get messages
        messages = conversation_manager.get_conversation_history(conversation_id)

        return jsonify({
            'success': True,
            'conversation': conversation,
            'messages': messages
        }), 200

    except Exception as e:
        logger.error(f"Error getting chat history: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve conversation history'
        }), 500


@chat_bp.route('/api/chat/conversations', methods=['GET'])
@verify_clerk_token
def get_user_conversations():
    """
    Get all conversations for current user.

    Query params:
    - type: Filter by conversation type (optional)
    - limit: Max conversations to return (default: 10)

    Response:
    {
        "success": true,
        "conversations": [
            {
                "id": "uuid",
                "type": "position",
                "created_at": "...",
                "updated_at": "...",
                "message_count": 5
            },
            ...
        ]
    }
    """
    try:
        user_id = get_current_user_id()
        conversation_type = request.args.get('type')
        limit = int(request.args.get('limit', 10))

        conversations = conversation_manager.get_user_conversations(
            user_id=user_id,
            conversation_type=conversation_type,
            limit=limit
        )

        return jsonify({
            'success': True,
            'conversations': conversations
        }), 200

    except Exception as e:
        logger.error(f"Error getting user conversations: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve conversations'
        }), 500


@chat_bp.route('/api/chat/conversation/<conversation_id>', methods=['DELETE'])
@verify_clerk_token
def delete_conversation(conversation_id):
    """
    Delete a conversation and all its messages.

    Response:
    {
        "success": true,
        "message": "Conversation deleted"
    }
    """
    try:
        user_id = get_current_user_id()

        # Verify user owns this conversation
        conversations = conversation_manager.get_user_conversations(user_id, limit=100)
        if not any(c['id'] == conversation_id for c in conversations):
            return jsonify({
                'success': False,
                'error': 'Conversation not found or access denied'
            }), 404

        # Delete conversation
        success = conversation_manager.delete_conversation(conversation_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'Conversation deleted'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete conversation'
            }), 500

    except Exception as e:
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to delete conversation'
        }), 500


@chat_bp.route('/api/chat/usage', methods=['GET'])
@verify_clerk_token
def get_usage_stats():
    """
    Get current user's usage statistics.

    Response:
    {
        "success": true,
        "usage": {
            "tier": "free",
            "hourly": {
                "requests": 5,
                "requests_limit": 50,
                "requests_remaining": 45,
                "tokens": 1250,
                "tokens_limit": 25000,
                "tokens_remaining": 23750
            },
            "daily": {
                "requests": 12,
                "requests_limit": 200,
                "requests_remaining": 188,
                "tokens": 3000,
                "tokens_limit": 100000,
                "tokens_remaining": 97000
            }
        }
    }
    """
    try:
        user_id = get_current_user_id()
        usage = rate_limiter.get_user_usage(user_id)

        return jsonify({
            'success': True,
            'usage': usage
        }), 200

    except Exception as e:
        logger.error(f"Error getting usage stats: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve usage statistics'
        }), 500


@chat_bp.route('/api/chat/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring.

    Response:
    {
        "status": "healthy",
        "stats": {
            "active_requests": 2,
            "total_processed": 1523,
            "total_errors": 5,
            "active_users": 15
        }
    }
    """
    try:
        stats = session_manager.get_stats()
        rate_stats = rate_limiter.get_stats()

        return jsonify({
            'status': 'healthy',
            'llm_stats': stats,
            'rate_limiter_stats': rate_stats
        }), 200

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@chat_bp.route('/api/chat/metrics', methods=['GET'])
def get_metrics():
    """
    Get performance metrics for API endpoints.

    Query params:
    - time_range: '1h', '24h', '7d', or '30d' (default: '1h')
    - source: 'memory' or 'database' (default: 'database')

    Response:
    {
        "success": true,
        "time_range": "1h",
        "metrics": {
            "total_requests": 150,
            "total_errors": 3,
            "avg_response_time": 245.5,
            "error_rate": 0.02,
            "endpoints": {
                "/api/chat/analysis": {
                    "count": 120,
                    "errors": 2,
                    "avg_time": 250.3,
                    "min_time": 100.5,
                    "max_time": 500.2,
                    "error_rate": 0.016
                }
            }
        }
    }
    """
    try:
        from middleware.performance_monitor import get_monitor

        monitor = get_monitor()
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Performance monitoring not enabled'
            }), 503

        time_range = request.args.get('time_range', '1h')
        source = request.args.get('source', 'database')

        if source == 'memory':
            metrics = monitor.get_stats()
        else:
            # Get from database
            metrics = monitor.get_database_stats(time_range)

        return jsonify({
            'success': True,
            'source': source,
            'metrics': metrics
        }), 200

    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve metrics'
        }), 500
