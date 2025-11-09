# Agents package for the ETL pipeline
# This module contains the LangGraph agents for the RAG system

from typing import Dict, Any, List, Optional
import logging
import os
from .. import config as etl_config_module
from ..weaviate_loader import get_weaviate_client

# Add the backend directory to the path
import sys
import os
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)

# Import LLM clients with error handling
try:
    from backend.llm.openai_llm import OpenAILLM
    from backend.llm.anthropic_llm import AnthropicLLM
    logger.info("Successfully imported LLM clients with backend.llm path")
except ImportError as e:
    logger.error(f"Failed to import LLM clients with backend.llm path: {e}")
    logger.info(f"Backend dir: {backend_dir}")
    logger.info(f"Current sys.path: {sys.path[:3]}...")
    # Try alternative import path
    try:
        import sys
        import os
        # Add the backend directory to sys.path if not already there
        backend_parent_dir = os.path.dirname(backend_dir)
        if backend_parent_dir not in sys.path:
            sys.path.insert(0, backend_parent_dir)
        
        from backend.llm.openai_llm import OpenAILLM
        from backend.llm.anthropic_llm import AnthropicLLM
        logger.info("Successfully imported LLM clients with alternative path")
    except ImportError as e2:
        logger.error(f"Alternative import also failed: {e2}")
        raise ImportError(f"Could not import LLM clients: {e}") from e

# Initialize conversation memory manager for agents module
# REMOVED: This was causing issues with duplicate initialization
# The conversation memory is now initialized properly in app.py
# try:
#     from .conversation_memory import initialize_conversation_memory
#     initialize_conversation_memory()
#     logger.info("Conversation memory manager initialized in agents module")
# except Exception as e:
#     logger.error(f"Failed to initialize conversation memory in agents module: {e}")

# Global variables to hold agent instances (initialized lazily)
_weaviate_client = None
_router_agent_instance = None
_retriever_agent_instance = None
_answer_agent_instance = None

# Lazy imports for agents to avoid circular dependencies
_RouterAgent = None
_RetrieverAgent = None
_AnswerAgent = None

def _get_router_agent_class():
    """Lazy import RouterAgent class"""
    global _RouterAgent
    if _RouterAgent is None:
        from .enhanced_router_agent import EnhancedRouterAgent as RouterAgent
        _RouterAgent = RouterAgent
    return _RouterAgent

def _get_retriever_agent_class():
    """Lazy import RetrieverAgent class"""
    global _RetrieverAgent
    if _RetrieverAgent is None:
        from .retriever_agent import RetrieverAgent
        _RetrieverAgent = RetrieverAgent
    return _RetrieverAgent

def _get_answer_agent_class():
    """Lazy import AnswerAgent class"""
    global _AnswerAgent
    if _AnswerAgent is None:
        from .answer_agent import AnswerAgent
        _AnswerAgent = AnswerAgent
    return _AnswerAgent

def get_weaviate_client_cached():
    """Get Weaviate client with caching"""
    global _weaviate_client
    if _weaviate_client is None:
        try:
            _weaviate_client = get_weaviate_client()
            if _weaviate_client:
                logger.info("Weaviate client initialized successfully via get_weaviate_client().")
            else:
                logger.error("get_weaviate_client() returned None. Weaviate client not available.")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client using get_weaviate_client(): {e}", exc_info=True)
            _weaviate_client = None
    return _weaviate_client

def _get_llm_client(use_case: str = "general"):
    """Get appropriate LLM client based on available API keys, prioritizing Anthropic"""
    api_key = None
    llm_client = None
    
    logger.info(f"DEBUG: _get_llm_client called for use_case: {use_case}")
    
    # Try Anthropic first
    api_key = os.getenv("ANTHROPIC_API_KEY")
    logger.info(f"DEBUG: ANTHROPIC_API_KEY found: {bool(api_key)}")
    
    if api_key:
        try:
            if use_case == "router":
                model_name = "claude-3-haiku-20240307"  # Faster model for routing
                max_tokens = etl_config_module.ROUTER_AGENT_MAX_TOKENS
            else:  # answer agent or general use
                model_name = "claude-3-5-sonnet-20241022"  # More capable model for answers
                max_tokens = etl_config_module.ANSWER_AGENT_MAX_TOKENS
                
            logger.info(f"DEBUG: Trying to create AnthropicLLM with model: {model_name}")
            
            llm_client = AnthropicLLM(
                api_key=api_key,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=0.7
            )
            logger.info(f"DEBUG: AnthropicLLM created successfully for {use_case} with model: {model_name}")
            logger.info(f"Anthropic LLM client initialized for {use_case} with model: {model_name}")
            return llm_client
        except Exception as e:
            logger.error(f"DEBUG: Failed to initialize Anthropic client: {e}")
            logger.error(f"Failed to initialize Anthropic client: {e}")
    
    # Fallback to OpenAI
    logger.info(f"DEBUG: Falling back to OpenAI for use_case: {use_case}")
    api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"DEBUG: OPENAI_API_KEY found: {bool(api_key)}")
    
    if api_key:
        try:
            if use_case == "router":
                model_name = etl_config_module.ROUTER_AGENT_MODEL_NAME
                max_tokens = etl_config_module.ROUTER_AGENT_MAX_TOKENS
            else:  # answer agent or general use
                model_name = etl_config_module.ANSWER_AGENT_MODEL_NAME
                max_tokens = etl_config_module.ANSWER_AGENT_MAX_TOKENS
                
            llm_client = OpenAILLM(
                api_key=api_key,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=0.7
            )
            logger.info(f"OpenAI LLM client initialized for {use_case} with model: {model_name}")
            return llm_client
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    logger.warning(f"No LLM client available for {use_case} - neither Anthropic nor OpenAI API keys found")
    return None

def get_router_agent_instance():
    """Get router agent instance with lazy initialization"""
    global _router_agent_instance
    if _router_agent_instance is None:
        try:
            # Use lazy import to avoid circular dependency
            def get_filtering_service():
                try:
                    from backend.services.advanced_filtering_service import AdvancedFilteringService
                    return AdvancedFilteringService()
                except ImportError as e:
                    logger.warning(f"Could not import AdvancedFilteringService: {e}")
                    return None
            
            filtering_service = get_filtering_service()
            
            # Initialize EnhancedRouterAgent with filtering service
            if filtering_service:
                _router_agent_instance = _get_router_agent_class()(filtering_service=filtering_service)
                logger.info("EnhancedRouterAgent instance initialized with filtering service.")
            else:
                _router_agent_instance = _get_router_agent_class()()
                logger.warning("EnhancedRouterAgent initialized without filtering service.")
        except Exception as e:
            logger.error(f"Failed to initialize EnhancedRouterAgent: {e}", exc_info=True)
            # Create router without filtering service as fallback
            _router_agent_instance = _get_router_agent_class()()
            logger.warning("EnhancedRouterAgent initialized without filtering service as fallback.")
    return _router_agent_instance

def get_retriever_agent_instance():
    """Get retriever agent instance with lazy initialization"""
    global _retriever_agent_instance
    if _retriever_agent_instance is None:
        try:
            weaviate_client = get_weaviate_client_cached()
            if weaviate_client:
                _retriever_agent_instance = _get_retriever_agent_class()(
                    client=weaviate_client,
                    opening_book_path=etl_config_module.OPENING_BOOK_PATH
                )
                logger.info("RetrieverAgent instance initialized.")
            else:
                logger.error("RetrieverAgent could not be initialized because Weaviate client is unavailable.")
                _retriever_agent_instance = None
        except Exception as e:
            logger.error(f"Failed to initialize RetrieverAgent: {e}", exc_info=True)
            _retriever_agent_instance = None
    return _retriever_agent_instance

def get_answer_agent_instance():
    """Get answer agent instance with lazy initialization"""
    global _answer_agent_instance
    if _answer_agent_instance is None:
        try:
            # Import conversation memory manager
            from .conversation_memory import get_conversation_memory_manager
            
            # Create LLM client for answer agent
            llm_client_for_answer_agent = _get_llm_client("answer")
            if llm_client_for_answer_agent:
                logger.info(f"LLM client for AnswerAgent initialized with model: {llm_client_for_answer_agent.model_name}")
            
            # Get conversation memory manager
            conversation_memory_manager = get_conversation_memory_manager()
            
            # Initialize AnswerAgent with conversation memory manager
            _answer_agent_instance = _get_answer_agent_class()(
                llm_client=llm_client_for_answer_agent,
                conversation_memory_manager=conversation_memory_manager
            )
            logger.info(f"AnswerAgent instance initialized with conversation memory: {conversation_memory_manager is not None}")
        except Exception as e:
            logger.error(f"Failed to initialize AnswerAgent: {e}", exc_info=True)
            # Create answer agent without LLM client as fallback
            _answer_agent_instance = _get_answer_agent_class()(llm_client=None)
            logger.warning("AnswerAgent initialized without LLM client as fallback.")
    return _answer_agent_instance

# Create a module wrapper to support attribute access
class LazyAgentModule:
    @property
    def router_agent_instance(self):
        return get_router_agent_instance()
    
    @property
    def retriever_agent_instance(self):
        return get_retriever_agent_instance()
    
    @property
    def answer_agent_instance(self):
        return get_answer_agent_instance()
    
    @property
    def RouterAgent(self):
        return _get_router_agent_class()
    
    @property
    def RetrieverAgent(self):
        return _get_retriever_agent_class()
    
    @property
    def AnswerAgent(self):
        return _get_answer_agent_class()

# Create a module-level instance to provide the lazy properties
_lazy_agents = LazyAgentModule()

# Expose the lazy properties at module level
router_agent_instance = _lazy_agents.router_agent_instance
retriever_agent_instance = _lazy_agents.retriever_agent_instance  
answer_agent_instance = _lazy_agents.answer_agent_instance

# Make classes available at module level
RouterAgent = _lazy_agents.RouterAgent
RetrieverAgent = _lazy_agents.RetrieverAgent
AnswerAgent = _lazy_agents.AnswerAgent

# Import the orchestrator module
from . import orchestrator

__all__ = [
    "router_agent_instance",
    "retriever_agent_instance", 
    "answer_agent_instance",
    "RouterAgent",
    "RetrieverAgent",
    "AnswerAgent",
    "OpenAILLM",
    "get_weaviate_client"
] 