from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from .conversation_memory import ConversationMessage, MessageRole, get_conversation_memory_manager

logger = logging.getLogger(__name__)

class ConversationSummarizer:
    """Service for summarizing long conversations to maintain context while reducing token usage"""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.3):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model,
            temperature=temperature
        )
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def create_conversation_summary(self, messages: List[ConversationMessage], 
                                   existing_summary: Optional[str] = None,
                                   focus_areas: Optional[List[str]] = None) -> str:
        """
        Create a comprehensive summary of a conversation
        
        Args:
            messages: List of conversation messages to summarize
            existing_summary: Previous summary to build upon
            focus_areas: Specific areas to focus on (e.g., ['chess positions', 'user preferences'])
        
        Returns:
            Comprehensive conversation summary
        """
        try:
            if not messages:
                return existing_summary or "No conversation history available."
            
            # Prepare conversation text
            conversation_text = self._format_messages_for_summarization(messages)
            
            # Create focus areas text
            focus_text = ""
            if focus_areas:
                focus_text = f"\nPay special attention to: {', '.join(focus_areas)}"
            
            # Create system prompt for summarization
            system_prompt = f"""
            You are an expert conversation summarizer for a chess AI assistant. Your task is to create a comprehensive but concise summary of the conversation that preserves:

            1. **Chess Context**: Any chess positions, moves, analysis, or game states discussed
            2. **User Preferences**: User's playing style, preferences, skill level, interests
            3. **Key Topics**: Main subjects discussed and questions asked
            4. **Important Facts**: Specific information about chess openings, tactics, players, etc.
            5. **Context Flow**: How topics evolved and connected throughout the conversation
            6. **Unresolved Items**: Any questions or topics that need follow-up

            Guidelines:
            - Be concise but comprehensive
            - Maintain chess-specific terminology and notation
            - Preserve important FEN positions or move sequences
            - Keep user-specific information and preferences
            - Organize information logically
            - Focus on information that would be useful for continuing the conversation{focus_text}

            Format your summary in clear sections when appropriate.
            """
            
            # Create human prompt
            summary_context = ""
            if existing_summary:
                summary_context = f"\n\nPrevious conversation summary:\n{existing_summary}\n\n"
            
            human_prompt = f"""
            {summary_context}Recent conversation to summarize:

            {conversation_text}

            Please create a comprehensive summary that preserves all important context for future interactions.
            """
            
            # Generate summary
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = self.llm.invoke(messages)
            summary = response.content
            
            logger.info(f"Generated conversation summary ({len(summary)} characters)")
            return summary
            
        except Exception as e:
            logger.error(f"Error creating conversation summary: {e}")
            # Return existing summary or fallback
            return existing_summary or f"Error creating summary: {str(e)}"
    
    def create_incremental_summary(self, messages: List[ConversationMessage],
                                  existing_summary: str,
                                  recent_message_limit: int = 10) -> str:
        """
        Create an incremental summary by updating existing summary with recent messages
        
        Args:
            messages: All conversation messages
            existing_summary: Current summary to update
            recent_message_limit: Number of recent messages to focus on for update
        
        Returns:
            Updated summary
        """
        try:
            if not messages:
                return existing_summary
            
            # Get recent messages for incremental update
            recent_messages = messages[-recent_message_limit:] if len(messages) > recent_message_limit else messages
            recent_text = self._format_messages_for_summarization(recent_messages)
            
            system_prompt = """
            You are updating a conversation summary with new information. Your task is to:

            1. **Integrate New Information**: Add important new topics, preferences, or chess content
            2. **Update Existing Items**: Modify existing summary sections if new info contradicts or expands them
            3. **Maintain Structure**: Keep the summary well-organized and concise
            4. **Preserve Context**: Don't lose important historical information
            5. **Chess Focus**: Maintain chess-specific details like positions, moves, analysis

            Provide the complete updated summary, not just additions.
            """
            
            human_prompt = f"""
            Current conversation summary:
            {existing_summary}

            Recent conversation to integrate:
            {recent_text}

            Please provide the updated complete summary that incorporates the new information.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = self.llm.invoke(messages)
            updated_summary = response.content
            
            logger.info(f"Updated conversation summary incrementally")
            return updated_summary
            
        except Exception as e:
            logger.error(f"Error updating conversation summary: {e}")
            return existing_summary
    
    def _format_messages_for_summarization(self, messages: List[ConversationMessage]) -> str:
        """Format messages for summarization input"""
        formatted_lines = []
        
        for i, msg in enumerate(messages):
            # Format timestamp
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # Format role
            role_map = {
                MessageRole.USER: "User",
                MessageRole.ASSISTANT: "Assistant", 
                MessageRole.SYSTEM: "System"
            }
            role = role_map.get(msg.role, msg.role.value)
            
            # Add message with metadata if relevant
            metadata_info = ""
            if msg.metadata:
                # Extract useful metadata for context
                if 'chess_position' in msg.metadata:
                    metadata_info = f" [Position: {msg.metadata['chess_position']}]"
                elif 'query_type' in msg.metadata:
                    metadata_info = f" [Query: {msg.metadata['query_type']}]"
            
            formatted_lines.append(f"[{timestamp}] {role}{metadata_info}: {msg.content}")
        
        return "\n".join(formatted_lines)
    
    async def async_summarize_session(self, session_id: str) -> Optional[str]:
        """
        Asynchronously summarize a conversation session
        This can be called from background tasks
        """
        try:
            memory_manager = get_conversation_memory_manager()
            if not memory_manager:
                logger.error("Conversation memory manager not initialized")
                return None
            
            # Get conversation history
            messages = memory_manager.get_conversation_history(session_id)
            if not messages:
                logger.debug(f"No messages found for session {session_id}")
                return None
            
            # Run summarization in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(
                self.executor,
                self.create_conversation_summary,
                messages,
                None,  # No existing summary for full regeneration
                ['chess positions', 'user preferences', 'game analysis']  # Focus areas
            )
            
            logger.info(f"Async summarization completed for session {session_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in async summarization for session {session_id}: {e}")
            return None
    
    def should_summarize_conversation(self, messages: List[ConversationMessage],
                                    token_threshold: int = 3000,
                                    message_threshold: int = 20) -> bool:
        """
        Determine if a conversation should be summarized based on length criteria
        
        Args:
            messages: List of conversation messages
            token_threshold: Approximate token count threshold
            message_threshold: Number of messages threshold
        
        Returns:
            True if conversation should be summarized
        """
        if len(messages) < message_threshold:
            return False
        
        # Estimate token count (rough approximation: 4 chars per token)
        total_chars = sum(len(msg.content) for msg in messages)
        estimated_tokens = total_chars / 4
        
        return estimated_tokens > token_threshold
    
    def extract_conversation_insights(self, messages: List[ConversationMessage]) -> Dict[str, Any]:
        """
        Extract structured insights from conversation for analytics
        
        Returns:
            Dictionary with insights like topics, sentiment, user expertise level, etc.
        """
        try:
            if not messages:
                return {}
            
            conversation_text = self._format_messages_for_summarization(messages)
            
            system_prompt = """
            Analyze this chess assistant conversation and extract structured insights. Return a JSON object with:

            {
                "main_topics": ["topic1", "topic2", ...],
                "chess_openings_discussed": ["opening1", "opening2", ...],
                "user_skill_level": "beginner|intermediate|advanced|expert",
                "user_interests": ["interest1", "interest2", ...],
                "questions_asked": ["question1", "question2", ...],
                "positions_analyzed": ["fen1", "fen2", ...],
                "sentiment": "positive|neutral|negative",
                "engagement_level": "high|medium|low",
                "session_summary": "one_sentence_summary"
            }

            Be accurate and conservative in your assessments.
            """
            
            human_prompt = f"Analyze this conversation:\n\n{conversation_text}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Try to parse JSON response
            try:
                insights = json.loads(response.content)
                return insights
            except json.JSONDecodeError:
                logger.warning("Could not parse insights as JSON, returning text summary")
                return {"summary": response.content}
                
        except Exception as e:
            logger.error(f"Error extracting conversation insights: {e}")
            return {}

# Global instance
conversation_summarizer: Optional[ConversationSummarizer] = None

def initialize_conversation_summarizer(openai_api_key: str) -> ConversationSummarizer:
    """Initialize the global conversation summarizer"""
    global conversation_summarizer
    
    conversation_summarizer = ConversationSummarizer(openai_api_key)
    logger.info("Conversation summarizer initialized")
    return conversation_summarizer

def get_conversation_summarizer() -> Optional[ConversationSummarizer]:
    """Get the global conversation summarizer instance"""
    return conversation_summarizer 