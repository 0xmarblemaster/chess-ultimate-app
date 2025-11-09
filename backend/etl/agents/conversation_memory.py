from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import redis
import logging
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

class MessageRole(str, Enum):
    """Message roles in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class ConversationMessage:
    """Single message in a conversation"""
    role: MessageRole
    content: str
    timestamp: datetime
    message_id: str
    metadata: Optional[Dict[str, Any]] = None
    # Add search result context
    search_results: Optional[List[Dict[str, Any]]] = None
    search_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "metadata": self.metadata or {},
            "search_results": self.search_results,
            "search_context": self.search_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_id=data["message_id"],
            metadata=data.get("metadata", {}),
            search_results=data.get("search_results"),
            search_context=data.get("search_context")
        )

@dataclass
class ConversationSession:
    """Complete conversation session"""
    session_id: str
    user_id: Optional[str]
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata or {},
            "summary": self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """Create from dictionary"""
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            messages=[ConversationMessage.from_dict(msg) for msg in data.get("messages", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            summary=data.get("summary")
        )

# Database models for persistent storage
class ConversationSessionDB(Base):
    """Database model for conversation sessions"""
    __tablename__ = "conversation_sessions"
    
    session_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_metadata = Column(Text)  # JSON - renamed from metadata to avoid conflict
    summary = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)

class ConversationMessageDB(Base):
    """Database model for individual messages"""
    __tablename__ = "conversation_messages"
    
    message_id = Column(String(255), primary_key=True)
    session_id = Column(String(255), index=True)
    role = Column(String(50))
    content = Column(Text)
    timestamp = Column(DateTime)
    message_metadata = Column(Text)  # JSON - renamed from metadata to avoid conflict
    sequence_number = Column(Integer)  # Order within session

class ConversationMemoryManager:
    """Manages conversation memory with Redis cache and persistent storage"""
    
    def __init__(self, redis_client: redis.Redis, db_session: Session, 
                 max_messages_in_memory: int = 50,
                 summarization_threshold: int = 30):
        self.redis = redis_client
        self.db = db_session
        self.max_messages_in_memory = max_messages_in_memory
        self.summarization_threshold = summarization_threshold
        
    def _get_redis_key(self, session_id: str) -> str:
        """Get Redis key for session"""
        return f"conversation:session:{session_id}"
    
    def _get_messages_redis_key(self, session_id: str) -> str:
        """Get Redis key for session messages"""
        return f"conversation:messages:{session_id}"
    
    def get_conversation_history(self, session_id: str, 
                                limit: Optional[int] = None) -> List[ConversationMessage]:
        """Get conversation history from Redis cache or database"""
        try:
            # Try Redis first (recent messages)
            redis_key = self._get_messages_redis_key(session_id)
            cached_messages = self.redis.lrange(redis_key, 0, -1)
            
            if cached_messages:
                messages = []
                for msg_json in cached_messages:
                    try:
                        msg_data = json.loads(msg_json.decode('utf-8'))
                        messages.append(ConversationMessage.from_dict(msg_data))
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(f"Error parsing cached message: {e}")
                        continue
                
                # Apply limit if specified
                if limit:
                    messages = messages[-limit:]
                
                logger.debug(f"Retrieved {len(messages)} messages from Redis cache for session {session_id}")
                return messages
            
            # If not in Redis, load from database
            return self._load_from_database(session_id, limit)
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def _load_from_database(self, session_id: str, 
                           limit: Optional[int] = None) -> List[ConversationMessage]:
        """Load conversation history from database"""
        try:
            query = self.db.query(ConversationMessageDB).filter(
                ConversationMessageDB.session_id == session_id
            ).order_by(ConversationMessageDB.sequence_number.desc())
            
            if limit:
                query = query.limit(limit)
            
            db_messages = query.all()
            
            messages = []
            for db_msg in reversed(db_messages):  # Reverse to get chronological order
                try:
                    metadata = json.loads(db_msg.message_metadata) if db_msg.message_metadata else {}
                    message = ConversationMessage(
                        role=MessageRole(db_msg.role),
                        content=db_msg.content,
                        timestamp=db_msg.timestamp,
                        message_id=db_msg.message_id,
                        metadata=metadata
                    )
                    messages.append(message)
                except Exception as e:
                    logger.error(f"Error parsing database message {db_msg.message_id}: {e}")
                    continue
            
            # Cache in Redis for future access
            if messages:
                self._cache_messages_in_redis(session_id, messages)
            
            logger.debug(f"Loaded {len(messages)} messages from database for session {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            return []
    
    def _cache_messages_in_redis(self, session_id: str, messages: List[ConversationMessage]):
        """Cache messages in Redis for fast access"""
        try:
            redis_key = self._get_messages_redis_key(session_id)
            
            # Clear existing cache
            self.redis.delete(redis_key)
            
            # Add messages to list
            for message in messages:
                self.redis.rpush(redis_key, json.dumps(message.to_dict()))
            
            # Set expiration (24 hours)
            self.redis.expire(redis_key, 86400)
            
        except Exception as e:
            logger.error(f"Error caching messages in Redis: {e}")
    
    def add_message(self, session_id: str, role: MessageRole, content: str,
                   user_id: Optional[str] = None, 
                   metadata: Optional[Dict[str, Any]] = None,
                   search_results: Optional[List[Dict[str, Any]]] = None,
                   search_context: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        """Add a new message to the conversation"""
        try:
            # Generate message ID
            import uuid
            message_id = str(uuid.uuid4())
            
            # Create message
            message = ConversationMessage(
                role=role,
                content=content,
                timestamp=datetime.utcnow(),
                message_id=message_id,
                metadata=metadata,
                search_results=search_results,
                search_context=search_context
            )
            
            # Add to Redis cache
            redis_key = self._get_messages_redis_key(session_id)
            self.redis.rpush(redis_key, json.dumps(message.to_dict()))
            
            # Ensure Redis cache doesn't grow too large
            list_length = self.redis.llen(redis_key)
            if list_length > self.max_messages_in_memory:
                # Remove oldest messages from Redis (they're still in DB)
                excess_count = list_length - self.max_messages_in_memory
                for _ in range(excess_count):
                    self.redis.lpop(redis_key)
            
            # Get current sequence number
            sequence_number = self._get_next_sequence_number(session_id)
            
            # Store in database
            db_message = ConversationMessageDB(
                message_id=message_id,
                session_id=session_id,
                role=role.value,
                content=content,
                timestamp=message.timestamp,
                message_metadata=json.dumps({
                    **(metadata or {}),
                    "search_results": search_results,
                    "search_context": search_context
                }),
                sequence_number=sequence_number
            )
            
            self.db.add(db_message)
            
            # Update or create session record
            self._update_session_record(session_id, user_id)
            
            self.db.commit()
            
            # Check if summarization is needed
            if sequence_number >= self.summarization_threshold:
                self._schedule_summarization(session_id)
            
            logger.debug(f"Added message {message_id} to session {session_id}")
            return message
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding message: {e}")
            raise
    
    def _get_next_sequence_number(self, session_id: str) -> int:
        """Get the next sequence number for a message in the session"""
        last_message = self.db.query(ConversationMessageDB).filter(
            ConversationMessageDB.session_id == session_id
        ).order_by(ConversationMessageDB.sequence_number.desc()).first()
        
        return (last_message.sequence_number + 1) if last_message else 1
    
    def _update_session_record(self, session_id: str, user_id: Optional[str] = None):
        """Update or create session record in database"""
        session_record = self.db.query(ConversationSessionDB).filter(
            ConversationSessionDB.session_id == session_id
        ).first()
        
        if session_record:
            session_record.updated_at = datetime.utcnow()
            session_record.message_count = self._get_next_sequence_number(session_id)
        else:
            session_record = ConversationSessionDB(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                session_metadata=json.dumps({}),
                message_count=1
            )
            self.db.add(session_record)
    
    def _schedule_summarization(self, session_id: str):
        """Schedule conversation summarization (placeholder for async task)"""
        # This would ideally trigger a background task
        # For now, we'll just log it
        logger.info(f"Session {session_id} reached summarization threshold")
        # TODO: Implement actual summarization logic
    
    def clear_session(self, session_id: str):
        """Clear session from Redis cache"""
        try:
            redis_key = self._get_messages_redis_key(session_id)
            session_key = self._get_redis_key(session_id)
            
            self.redis.delete(redis_key)
            self.redis.delete(session_key)
            
            logger.debug(f"Cleared Redis cache for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing session cache: {e}")
    
    def get_recent_sessions(self, user_id: Optional[str] = None, 
                           limit: int = 10) -> List[ConversationSessionDB]:
        """Get recent conversation sessions"""
        try:
            query = self.db.query(ConversationSessionDB).order_by(
                ConversationSessionDB.updated_at.desc()
            )
            
            if user_id:
                query = query.filter(ConversationSessionDB.user_id == user_id)
            
            return query.limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting recent sessions: {e}")
            return []
    
    def get_last_search_results(self, session_id: str) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
        """Get the most recent search results from conversation history"""
        try:
            conversation_history = self.get_conversation_history(session_id, limit=10)
            
            # Look for the most recent message with search results
            for message in reversed(conversation_history):
                if message.search_results and message.search_context:
                    logger.debug(f"Found search results from message {message.message_id}: {len(message.search_results)} results")
                    return message.search_results, message.search_context
            
            logger.debug(f"No search results found in recent conversation history for session {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving last search results: {e}")
            return None
    
    def clear_search_context(self, session_id: str):
        """Clear search context from the most recent messages (useful when starting a new search)"""
        try:
            # This could be implemented to mark search results as "stale" 
            # For now, we'll rely on the natural flow where new search results replace old ones
            logger.debug(f"Search context cleared for session {session_id}")
        except Exception as e:
            logger.error(f"Error clearing search context: {e}")

# Global instance (to be initialized in app startup)
conversation_memory_manager: Optional[ConversationMemoryManager] = None

def initialize_conversation_memory(redis_client: redis.Redis = None, database_url: str = None):
    """Initialize the conversation memory manager"""
    global conversation_memory_manager
    
    try:
        # Use defaults if not provided
        if database_url is None:
            database_url = "sqlite:///conversation_memory.db"
        
        if redis_client is None:
            try:
                import redis
                redis_client = redis.Redis(host='localhost', port=6379, decode_responses=False)
                # Test Redis connection
                redis_client.ping()
                logger.info("Connected to Redis successfully")
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Redis connection failed: {e}. Using mock Redis for conversation memory.")
                # Create a mock Redis client for fallback
                redis_client = MockRedis()
        
        # Create database engine and session
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session = SessionLocal()
        
        # Initialize manager
        conversation_memory_manager = ConversationMemoryManager(
            redis_client=redis_client,
            db_session=db_session
        )
        
        logger.info("Conversation memory manager initialized successfully")
        return conversation_memory_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize conversation memory manager: {e}")
        raise

class MockRedis:
    """Mock Redis implementation for fallback when Redis is not available"""
    
    def __init__(self):
        self.data = {}
        self.lists = {}
        self.expiry = {}
    
    def ping(self):
        return True
    
    def set(self, key, value, ex=None):
        self.data[key] = value
        if ex:
            self.expiry[key] = ex
    
    def get(self, key):
        return self.data.get(key)
    
    def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)
            self.lists.pop(key, None)
            self.expiry.pop(key, None)
    
    def rpush(self, key, *values):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].extend(values)
        return len(self.lists[key])
    
    def lpop(self, key):
        if key in self.lists and self.lists[key]:
            return self.lists[key].pop(0)
        return None
    
    def lrange(self, key, start, end):
        if key not in self.lists:
            return []
        return self.lists[key][start:end+1 if end != -1 else None]
    
    def llen(self, key):
        return len(self.lists.get(key, []))
    
    def expire(self, key, seconds):
        self.expiry[key] = seconds

def get_conversation_memory_manager() -> Optional[ConversationMemoryManager]:
    """Get the global conversation memory manager instance"""
    return conversation_memory_manager 