"""
Conversation Manager - Handles chat conversation history and context

This service manages conversation storage and retrieval with:
- Conversation creation and tracking
- Message history storage
- Context retrieval with token limits
- Conversation cleanup
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import uuid

from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation history and context for multi-user chat sessions.

    Features:
    - Store conversations in Supabase
    - Retrieve context with token limits
    - Support multiple concurrent conversations per user
    - Context window management (last N messages)
    """

    MAX_CONTEXT_MESSAGES = 10  # Maximum messages to include in context
    MAX_CONTEXT_TOKENS = 2000  # Rough token limit for context

    def __init__(self):
        """Initialize conversation manager"""
        self.supabase = get_supabase_client()
        logger.info("Conversation Manager initialized")

    def create_conversation(
        self,
        user_id: str,
        conversation_type: str,
        context: dict = None
    ) -> str:
        """
        Create a new conversation session.

        Args:
            user_id: User's Clerk ID
            conversation_type: Type of conversation ('position', 'game', 'puzzle')
            context: Optional context data (FEN, PGN, etc.)

        Returns:
            conversation_id: UUID of created conversation
        """
        try:
            conversation_id = str(uuid.uuid4())

            result = self.supabase.table('analysis_conversations').insert({
                'id': conversation_id,
                'user_id': user_id,
                'conversation_type': conversation_type,
                'context': context or {},
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

            logger.info(
                f"Created conversation: id={conversation_id}, "
                f"user={user_id[:8]}..., type={conversation_type}"
            )

            return conversation_id

        except Exception as e:
            logger.error(f"Failed to create conversation: {e}", exc_info=True)
            raise

    def save_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        fen: str = None,
        tokens_used: int = 0,
        model: str = None
    ) -> str:
        """
        Save a chat message to the database.

        Args:
            conversation_id: Conversation UUID
            user_id: User's Clerk ID
            role: 'user' or 'assistant'
            content: Message content
            fen: Optional FEN position
            tokens_used: Number of tokens used (for cost tracking)
            model: Model name used

        Returns:
            message_id: UUID of created message
        """
        try:
            message_id = str(uuid.uuid4())

            result = self.supabase.table('analysis_chat_messages').insert({
                'id': message_id,
                'conversation_id': conversation_id,
                'user_id': user_id,
                'role': role,
                'content': content,
                'fen': fen,
                'tokens_used': tokens_used,
                'model': model,
                'timestamp': datetime.utcnow().isoformat()
            }).execute()

            # Update conversation updated_at timestamp
            self.supabase.table('analysis_conversations').update({
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', conversation_id).execute()

            logger.debug(
                f"Saved message: conversation={conversation_id[:8]}..., "
                f"role={role}, tokens={tokens_used}"
            )

            return message_id

        except Exception as e:
            logger.error(f"Failed to save message: {e}", exc_info=True)
            raise

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = None
    ) -> List[Dict]:
        """
        Retrieve conversation message history.

        Args:
            conversation_id: Conversation UUID
            limit: Maximum number of messages to retrieve (default: all)

        Returns:
            List of message dictionaries ordered chronologically
        """
        try:
            query = self.supabase.table('analysis_chat_messages')\
                .select('*')\
                .eq('conversation_id', conversation_id)\
                .order('timestamp', desc=False)

            if limit:
                query = query.limit(limit)

            result = query.execute()

            logger.debug(
                f"Retrieved {len(result.data)} messages for conversation {conversation_id[:8]}..."
            )

            return result.data

        except Exception as e:
            logger.error(f"Failed to retrieve conversation history: {e}", exc_info=True)
            return []

    def get_context(
        self,
        conversation_id: str,
        max_messages: int = None
    ) -> List[Dict]:
        """
        Retrieve conversation context for LLM prompt.

        This retrieves the last N messages with token budget management.
        Always includes the most recent messages verbatim.

        Args:
            conversation_id: Conversation UUID
            max_messages: Maximum messages to include (default: MAX_CONTEXT_MESSAGES)

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        if max_messages is None:
            max_messages = self.MAX_CONTEXT_MESSAGES

        try:
            # Get recent messages
            messages = self.get_conversation_history(
                conversation_id,
                limit=max_messages
            )

            # Format for LLM
            context = []
            total_tokens = 0

            # Reverse to get most recent first, then reverse back
            for msg in reversed(messages):
                # Estimate tokens (rough: 1 token ≈ 4 characters)
                msg_tokens = len(msg['content']) // 4

                # Check token budget
                if total_tokens + msg_tokens > self.MAX_CONTEXT_TOKENS:
                    # Skip older messages if we hit token limit
                    logger.debug(
                        f"Context token limit reached: {total_tokens}/{self.MAX_CONTEXT_TOKENS}"
                    )
                    break

                context.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
                total_tokens += msg_tokens

            # Reverse back to chronological order
            context.reverse()

            logger.debug(
                f"Retrieved context: {len(context)} messages, ~{total_tokens} tokens"
            )

            return context

        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}", exc_info=True)
            return []

    def get_user_conversations(
        self,
        user_id: str,
        conversation_type: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get all conversations for a user.

        Args:
            user_id: User's Clerk ID
            conversation_type: Optional filter by type
            limit: Maximum conversations to return

        Returns:
            List of conversation dictionaries
        """
        try:
            query = self.supabase.table('analysis_conversations')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('updated_at', desc=True)\
                .limit(limit)

            if conversation_type:
                query = query.eq('conversation_type', conversation_type)

            result = query.execute()

            logger.debug(
                f"Retrieved {len(result.data)} conversations for user {user_id[:8]}..."
            )

            return result.data

        except Exception as e:
            logger.error(f"Failed to get user conversations: {e}", exc_info=True)
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.

        Args:
            conversation_id: Conversation UUID

        Returns:
            True if successful
        """
        try:
            # Messages will be cascade deleted due to foreign key
            self.supabase.table('analysis_conversations')\
                .delete()\
                .eq('id', conversation_id)\
                .execute()

            logger.info(f"Deleted conversation: {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}", exc_info=True)
            return False

    def update_conversation_context(
        self,
        conversation_id: str,
        context: dict
    ) -> bool:
        """
        Update conversation context (e.g., update FEN as user makes moves).

        Args:
            conversation_id: Conversation UUID
            context: New context data

        Returns:
            True if successful
        """
        try:
            self.supabase.table('analysis_conversations').update({
                'context': context,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', conversation_id).execute()

            logger.debug(f"Updated context for conversation {conversation_id[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to update conversation context: {e}", exc_info=True)
            return False


# Global singleton instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """Get or create the global conversation manager instance"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
