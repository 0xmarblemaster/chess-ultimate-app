from typing import Dict, Any, List, Optional
import os
import json
import openai
import re
import chess
import datetime
import logging
import uuid
import math

# Phase 2 imports for enhanced answer quality and accuracy
try:
    from .context_manager import extract_chess_context, ChessContext
except ImportError:
    from context_manager import extract_chess_context, ChessContext

try:
    from .answer_quality import assess_answer_quality, QualityMetrics
except ImportError:
    from answer_quality import assess_answer_quality, QualityMetrics

try:
    from .accuracy_tracker import measure_query_accuracy, AccuracyMeasurement
except ImportError:
    from accuracy_tracker import measure_query_accuracy, AccuracyMeasurement

try:
    from .performance_monitor import performance_monitor
except ImportError:
    from performance_monitor import performance_monitor

# Import conversation memory components
try:
    from .conversation_memory import (
        get_conversation_memory_manager, 
        ConversationMessage, 
        MessageRole
    )
except ImportError:
    # Fallback if not available
    get_conversation_memory_manager = lambda: None
    ConversationMessage = None
    MessageRole = None

def safe_json_dumps(obj):
    """Safely serialize objects to JSON, handling datetime objects, Infinity, and NaN"""
    def default_serializer(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, float):
            if math.isinf(o):
                return "Infinity" if o > 0 else "-Infinity"
            elif math.isnan(o):
                return "NaN"
        return str(o)
    
    def clean_object(obj):
        """Recursively clean an object, replacing inf/nan values"""
        if isinstance(obj, dict):
            return {k: clean_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_object(item) for item in obj]
        elif isinstance(obj, float):
            if math.isinf(obj):
                return "Infinity" if obj > 0 else "-Infinity"
            elif math.isnan(obj):
                return "NaN"
        return obj
    
    try:
        # First clean the object to replace inf/nan values
        cleaned_obj = clean_object(obj)
        return json.dumps(cleaned_obj, default=default_serializer, allow_nan=False)
    except Exception:
        return str(obj)

from .. import config
from .shared_types import RagState # Added import

logger = logging.getLogger(__name__)

def format_chunks_for_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks into a string for LLM context.
    Enhanced to highlight exact definitions and educational content.
    
    Args:
        chunks: List of chunks from the retriever or specialist agents
        
    Returns:
        Formatted context string
    """
    if not chunks:
        return "No relevant content found."
    
    # Handle if chunks itself is a single error/message dict (e.g. from a failed primary agent call)
    if isinstance(chunks, dict):
        if "error" in chunks:
            return f"Error: {chunks.get('error', 'Unknown error during retrieval')}"
        if "message" in chunks:
            return f"Note: {chunks.get('message', 'No specific message')}"
        # If it's a dict but not error/message, it might be a single valid chunk (e.g. opening_data)
        # This case should be handled by ensuring 'chunks' passed here is always a list if it contains data items.
        # For safety, let's wrap it in a list if it looks like a single data item.
        if chunks.get('type'): # Heuristic: if it has a type, it might be a single item
            chunks = [chunks]
        else:
            return "Retrieved content is in an unexpected dictionary format."
            
    if not isinstance(chunks, list):
        return "Retrieved content is not in the expected list format."

    formatted_chunk_strings = []
    
    for i, chunk_item in enumerate(chunks):
        if not isinstance(chunk_item, dict): # Skip if a chunk is not a dictionary
            formatted_chunk_strings.append(f"--- Context Item {i+1} (skipped - invalid format) ---")
            continue

        chunk_type = chunk_item.get('type', 'UnknownData')
        text_parts = [f"--- Context Item {i+1} (Type: {chunk_type}) ---"]

        if "error" in chunk_item:
            text_parts.append(f"Error: {chunk_item['error']}")
        elif "message" in chunk_item:
            text_parts.append(f"Note: {chunk_item['message']}")
        elif chunk_type == "chess_opening":
            text_parts.append(f"Source: Chess Openings Database")
            if chunk_item.get('opening'): text_parts.append(f"Opening: {chunk_item['opening']}")  # Fixed: ChessGame uses 'opening'
            if chunk_item.get('eco_code'): text_parts.append(f"ECO Code: {chunk_item['eco_code']}")
            if chunk_item.get('fen'): text_parts.append(f"FEN: {chunk_item['fen']}")
            if chunk_item.get('san_moves'): text_parts.append(f"Moves (SAN): {chunk_item['san_moves']}")
            if chunk_item.get('uci_moves'): text_parts.append(f"Moves (UCI): {chunk_item['uci_moves']}")
            # Add any other properties from the opening_data dict
            other_props = {k: v for k, v in chunk_item.items() if k not in ['type', 'opening', 'eco', 'final_fen', 'pgn_moves', 'moves_uci', 'error', 'message']}  # Fixed: use pgn_moves not moves_san
            if other_props:
                text_parts.append(f"Other details: {safe_json_dumps(other_props)}")
        elif chunk_type == "StockfishAnalysis": # Assuming StockfishAgent might use this type
            text_parts.append(f"Source: Stockfish Engine Analysis")
            if chunk_item.get('fen'): text_parts.append(f"Analyzed FEN: {chunk_item['fen']}")
            if chunk_item.get('depth'): text_parts.append(f"Depth: {chunk_item['depth']}")
            if chunk_item.get('score_for_white') is not None: text_parts.append(f"Score (White): {chunk_item['score_for_white']}")
            if chunk_item.get('pv_san'): text_parts.append(f"Principal Variation (SAN): {chunk_item['pv_san']}")
            if chunk_item.get('comment'): text_parts.append(f"Comment: {chunk_item['comment']}")
        elif chunk_type == "position_analysis": # Handle Stockfish position analysis
            text_parts.append(f"Source: {chunk_item.get('source', 'Stockfish Engine Analysis')}")
            if chunk_item.get('fen'): 
                text_parts.append(f"Analyzed Position (FEN): {chunk_item['fen']}")
            
            analysis_data = chunk_item.get('analysis', [])
            if analysis_data and isinstance(analysis_data, list):
                text_parts.append(f"Engine Analysis Results:")
                for i, line in enumerate(analysis_data[:3]):  # Show top 3 lines
                    if isinstance(line, dict):
                        move = line.get('move', 'unknown')
                        eval_str = line.get('evaluation_string', 'N/A')
                        eval_num = line.get('evaluation_numerical', 'N/A')
                        pv_san = line.get('pv_san', '')
                        
                        text_parts.append(f"  Line {i+1}: {move} ({eval_str}, {eval_num})")
                        if pv_san:
                            text_parts.append(f"    Variation: {pv_san}")
            elif analysis_data:
                text_parts.append(f"Raw Analysis Data: {str(analysis_data)[:200]}...")
        elif chunk_type == "ChessLessonChunk": # Existing lesson chunk formatting
            text_parts.append(f"Source Document: Chess Lesson")
            if chunk_item.get('book_title'): text_parts.append(f"Book: {chunk_item['book_title']}")
            if chunk_item.get('lesson_title'): text_parts.append(f"Lesson: {chunk_item['lesson_title']} (#{chunk_item.get('lesson_number', '?')})")
            if chunk_item.get('text'): text_parts.append(f"Content: {chunk_item['text']}")
            if chunk_item.get('fen'): text_parts.append(f"Associated FEN: {chunk_item['fen']}")
            if chunk_item.get('image'): text_parts.append(f"Image Ref: {chunk_item['image']}")
        elif chunk_type == "education": # Enhanced formatting for educational content
            text_parts.append(f"Source: Educational Material (ChessLessonChunk)")
            if chunk_item.get('book_title'): text_parts.append(f"Book: {chunk_item['book_title']}")
            if chunk_item.get('lesson_title'): text_parts.append(f"Lesson: {chunk_item['lesson_title']} (#{chunk_item.get('lesson_number', '?')})")
            
            # Get the content
            content = chunk_item.get('content', '')
            content_type = chunk_item.get('content_type', '')
            
            # Special handling for explanation_group content type (likely contains definitions)
            if content_type == 'explanation_group' and content:
                # Check if content contains definitions or explanations
                if any(keyword in content.lower() for keyword in ['мат', 'шах', 'это', '–', '-']):
                    text_parts.append(f"🎯 EXACT DEFINITION (Use Verbatim): {content}")
                else:
                    text_parts.append(f"Educational Content: {content}")
            elif content:
                text_parts.append(f"Content: {content}")
            
            if chunk_item.get('fen'): text_parts.append(f"Associated FEN: {chunk_item['fen']}")
            if chunk_item.get('source_file'): text_parts.append(f"Source File: {chunk_item['source_file']}")
        elif chunk_type == "pgn_data": # ADDED: Handle pgn_data
            text_parts.append(f"Source: {chunk_item.get('source', 'Session Game History')}")
            text_parts.append(f"Game PGN / Move History: {chunk_item.get('content', '[PGN data not found]')}")
        elif chunk_type == "chess_game_search_result": # ADDED: Handle game search results
            text_parts.append(f"Source: Chess Games Database Search Result")
            # These are properties from the ChessGame collection
            if chunk_item.get('white_player') and chunk_item.get('black_player'):
                text_parts.append(f"Game: {chunk_item['white_player']} vs {chunk_item['black_player']}")
            # Add ELO ratings to game information
            if chunk_item.get('white_elo') or chunk_item.get('black_elo'):
                white_elo = chunk_item.get('white_elo', 'N/A')
                black_elo = chunk_item.get('black_elo', 'N/A')
                text_parts.append(f"ELO Ratings: White: {white_elo}, Black: {black_elo}")
            if chunk_item.get('event'): text_parts.append(f"Event: {chunk_item['event']}")
            if chunk_item.get('date_utc'): 
                date_val = chunk_item['date_utc']
                # Handle different date formats
                try:
                    if isinstance(date_val, datetime.datetime):
                        # Already a datetime object
                        text_parts.append(f"Date: {date_val.strftime('%Y-%m-%d')}")
                    elif isinstance(date_val, str):
                        # String that needs parsing
                        dt_obj = datetime.datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        text_parts.append(f"Date: {dt_obj.strftime('%Y-%m-%d')}")
                    else:
                        # Fallback for other types
                        text_parts.append(f"Date: {str(date_val)}")
                except:
                    text_parts.append(f"Date: {str(date_val)}") # Fallback to string conversion
            if chunk_item.get('result'): text_parts.append(f"Result: {chunk_item['result']}")
            if chunk_item.get('eco'): text_parts.append(f"ECO: {chunk_item['eco']}")
            if chunk_item.get('opening') and chunk_item['opening']:
                text_parts.append(f"Opening: {chunk_item['opening']}")  # Fixed: ChessGame uses 'opening'
            if chunk_item.get('pgn_moves'):
                # Show a snippet of moves, not the whole thing unless very short
                moves_snippet = chunk_item['pgn_moves']
                if len(moves_snippet) > 150: # Arbitrary limit for snippet
                    moves_snippet = moves_snippet[:150] + "..."
                text_parts.append(f"Moves: {moves_snippet}")
            if chunk_item.get('final_fen'): text_parts.append(f"Final FEN: {chunk_item['final_fen']}")
            if chunk_item.get('uuid'): text_parts.append(f"Game ID: {chunk_item['uuid']}") # Ensure UUID is part of context if available
        elif chunk_type == "chess_game": # ADDED: Handle chess_game type (same format as chess_game_search_result)
            text_parts.append(f"Source: Chess Games Database")
            # These are properties from the ChessGame collection
            if chunk_item.get('white_player') and chunk_item.get('black_player'):
                text_parts.append(f"Game: {chunk_item['white_player']} vs {chunk_item['black_player']}")
            # Add ELO ratings to game information
            if chunk_item.get('white_elo') or chunk_item.get('black_elo'):
                white_elo = chunk_item.get('white_elo', 'N/A')
                black_elo = chunk_item.get('black_elo', 'N/A')
                text_parts.append(f"ELO Ratings: White: {white_elo}, Black: {black_elo}")
            if chunk_item.get('event'): text_parts.append(f"Event: {chunk_item['event']}")
            if chunk_item.get('date_utc'): 
                date_val = chunk_item['date_utc']
                # Handle different date formats
                try:
                    if isinstance(date_val, datetime.datetime):
                        # Already a datetime object
                        text_parts.append(f"Date: {date_val.strftime('%Y-%m-%d')}")
                    elif isinstance(date_val, str):
                        # String that needs parsing
                        dt_obj = datetime.datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        text_parts.append(f"Date: {dt_obj.strftime('%Y-%m-%d')}")
                    else:
                        # Fallback for other types
                        text_parts.append(f"Date: {str(date_val)}")
                except:
                    text_parts.append(f"Date: {str(date_val)}") # Fallback to string conversion
            if chunk_item.get('result'): text_parts.append(f"Result: {chunk_item['result']}")
            if chunk_item.get('eco'): text_parts.append(f"ECO: {chunk_item['eco']}")
            if chunk_item.get('opening') and chunk_item['opening']:
                text_parts.append(f"Opening: {chunk_item['opening']}")  # Fixed: ChessGame uses 'opening'
            if chunk_item.get('pgn_moves'):
                # Show a snippet of moves, not the whole thing unless very short
                moves_snippet = chunk_item['pgn_moves']
                if len(moves_snippet) > 150: # Arbitrary limit for snippet
                    moves_snippet = moves_snippet[:150] + "..."
                text_parts.append(f"Moves: {moves_snippet}")
            if chunk_item.get('final_fen'): text_parts.append(f"Final FEN: {chunk_item['final_fen']}")
            if chunk_item.get('uuid'): text_parts.append(f"Game ID: {chunk_item['uuid']}") # Ensure UUID is part of context if available
        elif chunk_type == "enhanced_game_result": # ADDED: Handle enhanced retrieval game results
            text_parts.append(f"Source: Chess Games Database (Enhanced Search)")
            # Enhanced retrieval results have formatted content
            if chunk_item.get('content'):
                text_parts.append(f"Game Details: {chunk_item['content']}")
            # Add metadata if available
            metadata = chunk_item.get('metadata', {})
            if metadata.get('enhanced_retrieval'):
                text_parts.append(f"Search Type: Enhanced retrieval with FEN matching")
            if chunk_item.get('data', {}).get('chess_concepts'):
                concepts = chunk_item['data']['chess_concepts']
                text_parts.append(f"Chess Concepts: {', '.join(concepts)}")
        else: # Generic fallback for other data or if 'content' property exists
            source = chunk_item.get('source', 'Unknown source')
            content = chunk_item.get('content', 'No specific content field found. Full data: ' + safe_json_dumps(chunk_item))
            text_parts.append(f"Source: {source}")
            text_parts.append(f"Content: {content}")
            if chunk_item.get('fen'): text_parts.append(f"FEN: {chunk_item['fen']}")

        formatted_chunk_strings.append("\n".join(text_parts))
    
    return "\n\n---\n\n".join(formatted_chunk_strings)

# Add a function to detect FEN strings in text
def extract_fen_from_text(text: str) -> Optional[str]:
    """
    Extracts a valid FEN string from text.
    
    Args:
        text: The text to search for FEN strings
        
    Returns:
        The first valid FEN string found, or None if no valid FEN found
    """
    # FEN pattern (common format)
    # Adjusted to be more robust: handles various whitespace, ensures full FEN structure
    fen_pattern = r"\s*([rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}\s+[wb]\s+(?:[KQkq]{1,4}|-)\s+(?:[a-h][1-8]|-)\s+\d+\s+\d+)\s*"
    
    # Find all potential FEN strings
    matches = re.findall(fen_pattern, text)
    
    # Validate each match with chess.Board
    for match in matches:
        try:
            # Attempt to create a board with this FEN to validate it
            chess.Board(match.strip()) # Strip whitespace before validation
            return match.strip()
        except ValueError:
            continue # Not a valid FEN, try next match
    
    return None

class AnswerAgent:
    """
    Enhanced Answer Agent with quality assessment and accuracy tracking
    """
    
    def __init__(self, llm_client=None, conversation_memory_manager=None):
        """
        Initialize the AnswerAgent
        
        Parameters:
        -----------
        llm_client : object
            OpenAI client instance for generating answers
        conversation_memory_manager : ConversationMemoryManager
            Conversation memory manager instance
        """
        self.llm_client = llm_client
        self.conversation_memory_manager = conversation_memory_manager
        
        # Quality and accuracy tracking
        self.enable_quality_assessment = True
        self.enable_accuracy_tracking = True
        
        logger.info("AnswerAgent initialized with Phase 2 enhancements")
    
    @performance_monitor.timer('answer_generation')
    def generate_answer(self, query: str, retrieved_documents: List[Dict] = None, 
                       query_type: str = "direct", current_fen: str = None,
                       session_id: str = None, context: ChessContext = None) -> Dict[str, Any]:
        """
        Generate an enhanced answer with quality assessment, accuracy tracking, and conversation memory
        
        Parameters:
        -----------
        query : str
            The user's query with optional context
        retrieved_documents : List[Dict]
            The list of documents retrieved from the database
        query_type : str
            The type of query
        current_fen : str
            The current FEN position
        session_id : str
            Session identifier for tracking and conversation memory
        context : ChessContext
            Pre-extracted chess context (optional)
            
        Returns:
        --------
        Dict[str, Any]
            Enhanced response with answer, quality metrics, and accuracy tracking
        """
        if self.llm_client is None:
            error_response = "I'm sorry, I'm not able to provide answers at the moment as the AI service is unavailable."
            return {
                "answer": error_response,
                "error": "llm_client_unavailable",
                "quality_metrics": None,
                "accuracy_measurement": None
            }
        
        # Get conversation memory manager
        memory_manager = self.conversation_memory_manager
        
        # Fallback to global conversation memory manager if instance one is not available
        if not memory_manager:
            try:
                from backend.etl.agents.conversation_memory import get_conversation_memory_manager
                memory_manager = get_conversation_memory_manager()
                logger.debug("Using global conversation memory manager as fallback")
            except Exception as e:
                logger.error(f"Failed to get global conversation memory manager: {e}")
                memory_manager = None
        
        logger.info(f"Conversation memory manager retrieved: {memory_manager is not None}")
        conversation_history = []
        
        # Retrieve conversation history if available
        if memory_manager and session_id:
            try:
                conversation_history = memory_manager.get_conversation_history(
                    session_id, 
                    limit=20  # Get last 20 messages for context
                )
                logger.debug(f"Retrieved {len(conversation_history)} conversation messages for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to retrieve conversation history: {e}")
                conversation_history = []
        
        # Store user message in conversation history
        if memory_manager and session_id:
            try:
                user_metadata = {
                    "query_type": query_type,
                    "current_fen": current_fen,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
                memory_manager.add_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=query,
                    metadata=user_metadata
                )
                logger.debug(f"Stored user message in conversation history for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to store user message in conversation history: {e}")
        
        # Check for contextual filtering request
        contextual_filter_result = self._handle_contextual_filtering(
            query, session_id, memory_manager, retrieved_documents, query_type
        )
        
        if contextual_filter_result:
            # This was a contextual filter request, return the filtered results
            logger.info(f"Handled contextual filtering request for session {session_id}")
            
            # Store assistant response in conversation history with new search results
            if memory_manager and session_id:
                try:
                    assistant_metadata = {
                        "query_type": "contextual_filter",
                        "current_fen": current_fen,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    memory_manager.add_message(
                        session_id=session_id,
                        role=MessageRole.ASSISTANT,
                        content=contextual_filter_result["answer"],
                        metadata=assistant_metadata,
                        search_results=contextual_filter_result.get("filtered_games", []),
                        search_context={
                            "filter_type": "contextual",
                            "original_count": contextual_filter_result.get("original_count", 0),
                            "filtered_count": contextual_filter_result.get("total_count", 0),
                            "filters_applied": contextual_filter_result.get("filters_applied", {})
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to store contextual filter response: {e}")
            
            return contextual_filter_result
        
        # Extract context if not provided
        if context is None:
            context = extract_chess_context(query, current_fen, session_id)
        
        # Generate unique IDs for tracking
        query_id = str(uuid.uuid4())
        answer_id = str(uuid.uuid4())
        
        logger.info(f"Generating enhanced answer for query: {query[:50]}... (Intent: {context.intent_type}, Complexity: {context.query_complexity})")
        
        try:
            # Generate the answer using the base method (now includes conversation history)
            answer = self._generate_base_answer(
                query, 
                retrieved_documents, 
                query_type, 
                current_fen, 
                context,
                conversation_history
            )
            
            # Store assistant response in conversation history
            if memory_manager and session_id:
                try:
                    assistant_metadata = {
                        "query_type": query_type,
                        "current_fen": current_fen,
                        "answer_id": answer_id,
                        "query_id": query_id,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    
                    # Extract search results if this was a game search
                    search_results = None
                    search_context = None
                    
                    if query_type == "game_search" and retrieved_documents:
                        # Extract game data from retrieved documents
                        search_results = []
                        for doc in retrieved_documents:
                            if isinstance(doc, dict) and 'metadata' in doc:
                                game_data = doc['metadata']
                                search_results.append(game_data)
                        
                        if search_results:
                            search_context = {
                                "search_type": "game_search",
                                "total_count": len(search_results),
                                "query_type": query_type,
                                "timestamp": datetime.datetime.utcnow().isoformat()
                            }
                            logger.info(f"Storing {len(search_results)} search results in conversation memory")
                    
                    memory_manager.add_message(
                        session_id=session_id,
                        role=MessageRole.ASSISTANT,
                        content=answer,
                        metadata=assistant_metadata,
                        search_results=search_results,
                        search_context=search_context
                    )
                    logger.debug(f"Stored assistant response in conversation history for session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to store assistant response in conversation history: {e}")
            
            # Prepare response structure
            response = {
                "answer": answer,
                "query_id": query_id,
                "answer_id": answer_id,
                "context": context.to_dict(),
                "query_type": query_type,
                "conversation_history_used": len(conversation_history) > 0
            }
            
            # Quality assessment
            quality_metrics = None
            if self.enable_quality_assessment and answer:
                try:
                    quality_metrics = assess_answer_quality(
                        answer=answer,
                        query=query,
                        context=context,
                        retrieved_documents=retrieved_documents,
                        answer_id=answer_id
                    )
                    response["quality_metrics"] = quality_metrics.to_dict()
                    
                    # Add quality flags to response
                    if quality_metrics.quality_flags:
                        response["quality_flags"] = quality_metrics.quality_flags
                    if quality_metrics.improvement_suggestions:
                        response["improvement_suggestions"] = quality_metrics.improvement_suggestions
                    
                    logger.info(f"Quality assessment completed - Overall score: {quality_metrics.overall_score:.2f}")
                    
                except Exception as e:
                    logger.error(f"Quality assessment failed: {e}")
                    response["quality_assessment_error"] = str(e)
            
            # Accuracy tracking
            accuracy_measurement = None
            if self.enable_accuracy_tracking and answer:
                try:
                    accuracy_measurement = measure_query_accuracy(
                        query=query,
                        answer=answer,
                        context=context,
                        quality_metrics=quality_metrics,
                        retrieved_documents=retrieved_documents,
                        session_id=session_id or "",
                        query_id=query_id,
                        answer_id=answer_id
                    )
                    response["accuracy_measurement"] = accuracy_measurement.to_dict()
                    
                    logger.info(f"Accuracy tracking completed - Score: {accuracy_measurement.final_accuracy_score:.2f}")
                    
                except Exception as e:
                    logger.error(f"Accuracy tracking failed: {e}")
                    response["accuracy_tracking_error"] = str(e)
            
            logger.info(f"Enhanced answer generated successfully with quality score: {quality_metrics.overall_score if quality_metrics else 'N/A'}")
            return response
            
        except Exception as e:
            error_msg = f"Error generating answer: {str(e)}"
            logger.error(error_msg)
            return {
                "answer": f"I encountered an error while trying to answer your question: {error_msg}",
                "error": str(e),
                "query_id": query_id,
                "answer_id": answer_id,
                "context": context.to_dict() if context else None,
                "quality_metrics": None,
                "accuracy_measurement": None,
                "conversation_history_used": False
            }
    
    def _generate_base_answer(self, query: str, retrieved_documents: List[Dict] = None, 
                             query_type: str = "direct", current_fen: str = None, 
                             context: ChessContext = None, conversation_history: List[Dict] = None) -> str:
        """
        Generate the base answer using the LLM (original functionality)
        
        Parameters:
        -----------
        query : str
            The user's query
        retrieved_documents : List[Dict]
            Retrieved documents for context
        query_type : str
            Type of query
        current_fen : str
            Current FEN position
        context : ChessContext
            Chess context information
        conversation_history : List[Dict]
            Conversation history for context
            
        Returns:
        --------
        str
            Generated answer text
        """
        # Create enhanced system prompt based on context
        system_prompt = self._create_system_prompt(query_type, context)
        
        # Format conversation history if available
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            conversation_context = self._format_conversation_history(conversation_history)
            logger.debug(f"Formatted conversation history: {len(conversation_context)} characters")
        
        # Format retrieved documents if available
        context_text = ""
        has_real_documents = False
        
        if retrieved_documents:
            context_text = format_chunks_for_context(retrieved_documents)
            # Check if we actually have real documents (not just error messages)
            has_real_documents = any(
                doc.get('type') in ['chess_game_search_result', 'chess_game', 'chess_opening', 'ChessLessonChunk', 'enhanced_game_result',
                                   'explanation_group', 'general_task', 'lesson_content', 'task', 'diagram', 'education', 'position_analysis'] 
                for doc in retrieved_documents
                if isinstance(doc, dict)
            )
            
            # Debug logging
            logger.info(f"Retrieved {len(retrieved_documents)} documents")
            for i, doc in enumerate(retrieved_documents):
                doc_type = doc.get('type', 'unknown') if isinstance(doc, dict) else 'not_dict'
                logger.info(f"Document {i}: type={doc_type}")
            logger.info(f"has_real_documents: {has_real_documents}")
            logger.info(f"Context text length: {len(context_text)}")
            if context_text and len(context_text) > 100:
                logger.info(f"Context text preview: {context_text[:200]}...")
            else:
                logger.info(f"Context text: {context_text}")
            
            # Also log the full context for debugging
            logger.info(f"FULL CONTEXT TEXT: {context_text}")
            
        # Special handling for game search queries when no games are found
        if query_type == "game_search" and not has_real_documents:
            logger.info(f"ENTERING no-games-found branch: query_type={query_type}, has_real_documents={has_real_documents}")
            if context and context.current_fen:
                return f"""I searched the database for games containing the position from the FEN:
{context.current_fen}

Unfortunately, I could not find any games in our database that contain this specific position. This could be because:

1. This position might be from a less common line or opening variation
2. The position might be from the middle or endgame phase that's not well-represented in our database
3. The database might not contain enough games covering this particular position

To help you analyze this position, I can:
- Provide engine analysis of the current position
- Suggest similar opening lines if this is from the opening phase
- Offer general strategic principles that apply to this type of position

Would you like me to analyze the position from a strategic or tactical perspective instead?"""
            else:
                return """I searched the games database but could not find any games matching your request. This could be because:

1. The specific criteria might be too narrow or specific
2. The database might not contain games with those exact characteristics
3. There might be a spelling error in player names or tournament names

You can try:
- Broadening your search criteria
- Checking spelling of names or events
- Searching for similar but not exact matches
- Asking about general strategies or openings instead

Is there another way I can help you with chess analysis or information?"""
        
        # Build the complete user prompt with all context
        user_prompt_parts = []
        
        # Add conversation history context if available
        if conversation_context:
            user_prompt_parts.append(f"=== CONVERSATION HISTORY ===\n{conversation_context}\n")
        
        # Add current query
        user_prompt_parts.append(f"=== CURRENT QUESTION ===\n{query}\n")
        
        # Add position context if available
        if current_fen:
            user_prompt_parts.append(f"=== CURRENT CHESS POSITION ===\nFEN: {current_fen}\n")
        
        # Add retrieved context if available
        if context_text:
            user_prompt_parts.append(f"=== RETRIEVED CONTEXT ===\n{context_text}")
        
        # Combine all prompt parts
        user_prompt = "\n".join(user_prompt_parts)
        
        # Create the messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call the LLM
        logger.info(f"Making LLM call with {len(conversation_history) if conversation_history else 0} history messages")
        logger.debug(f"System prompt length: {len(system_prompt)}")
        logger.debug(f"User prompt length: {len(user_prompt)}")
        
        try:
            # Check if we have an OpenAILLM wrapper or raw OpenAI client
            logger.info(f"DEBUG: LLM client type: {type(self.llm_client)}")
            logger.info(f"DEBUG: LLM client class: {self.llm_client.__class__.__name__}")
            logger.info(f"DEBUG: hasattr(llm_client, 'generate'): {hasattr(self.llm_client, 'generate')}")
            
            if hasattr(self.llm_client, 'generate'):
                logger.info("DEBUG: Taking .generate() branch (should be Anthropic)")
                # Using OpenAILLM wrapper - use generate method
                # Combine system and user messages for the generate method
                full_prompt = user_prompt
                answer = self.llm_client.generate(
                    prompt=full_prompt,
                    system_message=system_prompt
                )
            else:
                logger.info("DEBUG: Taking .chat.completions.create() branch (OpenAI)")
                # Using raw OpenAI client - use chat.completions.create
                response = self.llm_client.chat.completions.create(
                    model=config.get_model_name(),
                    messages=messages,
                    max_tokens=config.get_max_tokens(),
                    temperature=config.get_temperature()
                )
                answer = response.choices[0].message.content.strip()
            
            logger.info(f"LLM response generated successfully (length: {len(answer)})")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
    
    def _format_conversation_history(self, conversation_history: List[Dict]) -> str:
        """
        Format conversation history for inclusion in LLM prompt
        
        Parameters:
        -----------
        conversation_history : List[Dict]
            List of conversation messages
            
        Returns:
        --------
        str
            Formatted conversation history text
        """
        if not conversation_history:
            return ""
        
        formatted_messages = []
        
        for i, message in enumerate(conversation_history):
            # Handle both ConversationMessage objects and dictionaries
            if hasattr(message, 'role'):
                # ConversationMessage object
                role = message.role.value if hasattr(message.role, 'value') else str(message.role)
                content = message.content
                timestamp = message.timestamp.strftime("%H:%M") if hasattr(message.timestamp, 'strftime') else str(message.timestamp)
            else:
                # Dictionary format
                role = message.get('role', 'unknown')
                content = message.get('content', '')
                timestamp = message.get('timestamp', '')
                if timestamp and isinstance(timestamp, str):
                    try:
                        # Try to parse timestamp and format it
                        dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp = dt.strftime("%H:%M")
                    except:
                        timestamp = timestamp[:5]  # Just take first 5 chars if parsing fails
            
            # Format the message
            role_display = {
                'user': 'Human',
                'assistant': 'Assistant',
                'system': 'System'
            }.get(role.lower(), role.title())
            
            formatted_messages.append(f"[{timestamp}] {role_display}: {content}")
        
        # Limit the conversation history to prevent token overflow
        formatted_text = "\n".join(formatted_messages)
        
        # If the conversation history is too long, truncate it intelligently
        max_history_chars = 2000  # Adjust based on your token limits
        if len(formatted_text) > max_history_chars:
            # Keep the most recent messages
            recent_messages = formatted_messages[-5:]  # Keep last 5 messages
            formatted_text = "...[earlier conversation truncated]...\n" + "\n".join(recent_messages)
        
        return formatted_text
    
    def _create_system_prompt(self, query_type: str, context: ChessContext = None) -> str:
        """
        Create an enhanced system prompt based on query type and context
        
        Parameters:
        -----------
        query_type : str
            Type of query
        context : ChessContext
            Chess context information
            
        Returns:
        --------
        str
            System prompt text
        """
        base_prompt = "You are a helpful Chess AI assistant with conversation memory."
        
        # Conversation memory instructions
        memory_instructions = """
CONVERSATION MEMORY GUIDELINES:

1. **Context Awareness**: Use the conversation history to understand the full context of the current question
2. **Reference Resolution**: Resolve pronouns and references (like "he", "it", "that position") using previous conversation
3. **Continuity**: Maintain awareness of ongoing topics, previous questions, and established context
4. **Follow-up Understanding**: Recognize when the current question is a follow-up to previous topics
5. **Personalization**: Remember user preferences, skill level, and interests mentioned in the conversation

6. **Examples of Context Usage**:
   - If user previously asked about "Ian Nepomniachtchi" and now asks "did he play Carlsen?", understand "he" refers to Nepomniachtchi
   - If discussing a specific position and user asks "what's the best move?", refer to that position
   - If user mentioned being a beginner, adjust explanations accordingly
   - If analyzing a game and user asks "what happens next?", continue from the current position

7. **When No History Available**: If no conversation history is provided, treat as a fresh conversation
"""
        
        # Universal verbatim response instructions
        verbatim_instructions = """
CRITICAL INSTRUCTIONS FOR USING DATABASE CONTENT:

1. **VERBATIM RESPONSES FOR DIRECT ANSWERS:**
   - When the context contains text that DIRECTLY answers the user's question, use the EXACT wording from the database
   - Look for definitions, explanations, or statements that precisely match what the user is asking
   - Quote the relevant text verbatim, especially for educational content, rules, or definitions
   - Preserve the original language (Russian, English, etc.) when quoting directly

2. **WHEN TO USE EXACT QUOTES:**
   - Definitions of chess terms (e.g., "что такое мат" → use exact definition from document)
   - Educational explanations that directly address the question
   - Rules or principles stated in the source material
   - Any content that provides a direct, complete answer to the user's question

3. **WHEN TO PARAPHRASE:**
   - When combining information from multiple sources
   - When the context provides related but not exact information
   - When adding your own analysis beyond what's in the documents
   - When translating concepts between languages

4. **IMPLEMENTATION:**
   - Start with any exact quotes that directly answer the question
   - Then add your own explanation or context if needed
   - Always prioritize accuracy to the source material
   - Maintain the educational intent of the original content"""
        
        # Intent-specific prompts
        if context and context.intent_type == "tactics":
            return f"""{base_prompt} You specialize in chess tactics and combinations.

{memory_instructions}

{verbatim_instructions}
            
When analyzing tactical positions:
- Identify key tactical patterns (forks, pins, skewers, discoveries, etc.)
- Explain the tactical motifs clearly
- Provide concrete variations when possible
- Use proper chess notation (algebraic notation)
- Focus on forcing moves and combinations

Current query is about tactics with patterns: {', '.join(context.tactical_patterns) if context.tactical_patterns else 'general tactics'}
Complexity level: {context.query_complexity}"""

        elif context and context.intent_type == "opening":
            return f"""{base_prompt} You specialize in chess opening theory and principles.

{memory_instructions}

{verbatim_instructions}
            
When discussing openings:
- Explain opening principles and development
- Mention key ideas and typical plans
- Reference specific opening variations when relevant
- Use proper chess notation
- Focus on understanding rather than memorization

Current query is about openings in the {context.position_type} phase.
Complexity level: {context.query_complexity}"""

        elif context and context.intent_type == "strategy":
            return f"""{base_prompt} You specialize in chess strategy and positional play.

{memory_instructions}

{verbatim_instructions}
            
When analyzing strategic positions:
- Identify pawn structures and imbalances
- Explain long-term plans and objectives
- Discuss piece coordination and activity
- Mention key strategic concepts
- Focus on positional understanding

Current query is about strategy in the {context.position_type} phase.
Complexity level: {context.query_complexity}"""

        elif context and context.intent_type == "endgame":
            return f"""{base_prompt} You specialize in chess endgames and technique.

{memory_instructions}

{verbatim_instructions}
            
When analyzing endgame positions:
- Explain key endgame principles
- Identify critical squares and techniques
- Provide concrete winning/drawing methods
- Use precise calculation when needed
- Focus on practical technique

Current query is about endgames.
Complexity level: {context.query_complexity}"""

        elif query_type == "game_search":
            return f"""{base_prompt} You specialize in chess game analysis.

{memory_instructions}

{verbatim_instructions}

CRITICAL INSTRUCTIONS FOR GAME SEARCH:

1. LOOK FOR GAME DATA: Check the context for any of these indicators that games were found:
   - "Source: Chess Games Database"
   - "Game Details:" followed by game information
   - Player names like "**Player1 vs Player2**"
   - Game metadata (Event, Date, Result, ECO, Opening, Game ID)

2. IF GAMES ARE FOUND IN CONTEXT:
   - Present each game clearly with all available details
   - Use the exact player names, events, dates, and other data provided
   - Format as: **[White Player] vs [Black Player]** followed by game details
   - NEVER say "no games found" if game data is present in the context

3. IF NO GAMES ARE FOUND IN CONTEXT:
   - Only then state that no games were found in the database
   - Explain possible reasons and offer alternative assistance

4. NEVER INVENT OR HALLUCINATE:
   - Do NOT create fictional games, players, or game details
   - Only use the exact game data provided in the context
   - Be truthful about what is actually in the database context

The context will contain game data if any games match the search criteria. Look carefully for game information before concluding that no games were found."""

        elif query_type == "position_analysis":
            return f"""{base_prompt} You specialize in chess position analysis using Stockfish engine.

{memory_instructions}

CRITICAL INSTRUCTIONS FOR POSITION ANALYSIS:

1. **ALWAYS PRIORITIZE STOCKFISH ENGINE RESULTS:**
   - The context contains Stockfish analysis with the best moves and evaluations
   - ALWAYS use the engine's top recommendation as your primary answer
   - The "Line 1" result is the best move according to the engine
   - Look for patterns like "Line 1: [move] (M1, 999.99)" for mate or "+X.XX" for advantage

2. **HOW TO READ ENGINE ANALYSIS:**
   - "M1" = Mate in 1 move (this is the strongest possible move!)
   - "M2" = Mate in 2 moves
   - "+3.59" = White is winning by 3.59 points
   - "-2.45" = Black is winning by 2.45 points
   - "Variation:" shows the best continuation after the move

3. **RESPONSE FORMAT:**
   - Start with the best move from Line 1
   - If it's mate, clearly state "This is mate in X moves!"
   - Include the evaluation (e.g., "White is winning +3.5")
   - Mention the key continuation from the variation
   - Explain WHY this move is strong

4. **NEVER GUESS OR IMPROVISE:**
   - Do NOT suggest your own moves if engine analysis is available
   - Do NOT give generic opening advice when asking for best moves
   - Always defer to the engine's concrete analysis
   - The engine has calculated deeper than any human can

5. **EXAMPLE RESPONSE:**
   "The best move is Qh5# - this is mate in 1! The engine shows this delivers checkmate immediately, ending the game. This forcing move cannot be defended against."

Current query is about position analysis. Use the Stockfish engine results from the context as the authoritative answer.
Complexity level: {context.query_complexity if context else 'medium'}"""

        elif query_type == "direct":
            return f"""{base_prompt} You provide direct, simple answers to chess questions.

{memory_instructions}

CRITICAL INSTRUCTIONS FOR DIRECT QUERIES:

1. **SIMPLE FEN/BOARD REQUESTS:**
   - If asked for the current board FEN, simply provide the FEN from the context
   - Don't search for games or provide additional analysis unless requested
   - Be concise and direct - answer exactly what was asked

2. **CURRENT POSITION QUERIES:**
   - "what is the current board fen" → return the FEN
   - "current fen" → return the FEN
   - "show me the current position" → describe position and provide FEN
   - "current board" → describe the board state

3. **RESPONSE FORMAT:**
   - For FEN requests: "The current board FEN is: [FEN_STRING]"
   - Keep responses short and direct
   - Only provide what was specifically asked for
   - Don't add game searches or analysis unless requested

4. **WHAT NOT TO DO:**
   - Don't search for games unless specifically asked
   - Don't provide analysis unless requested
   - Don't add extra information not requested
   - Stay focused on the specific question asked

Provide direct, concise answers that match exactly what the user requested."""

        else:
            # Default system prompt with memory and verbatim instructions
            prompt = f"""{base_prompt} Answer chess-related queries concisely and accurately.

{memory_instructions}

{verbatim_instructions}

GENERAL GUIDELINES:
- If the query is about a chess position, refer to the FEN provided if available
- Use clear and simple language, and provide practical advice when appropriate
- When educational content in the database directly answers the question, quote it exactly
- Preserve the educational value and accuracy of the source material"""
            
            if context:
                prompt += f"\n\nQuery context: Intent={context.intent_type}, Complexity={context.query_complexity}"
                if context.current_fen:
                    prompt += f", Position={context.position_type}"
            
            return prompt
    
    def generate_answer_legacy(self, query: str, retrieved_documents: List[Dict] = None, 
                              query_type: str = "direct", current_fen: str = None) -> str:
        """
        Legacy method for backward compatibility - returns just the answer text
        
        Parameters:
        -----------
        query : str
            The user's query
        retrieved_documents : List[Dict]
            Retrieved documents
        query_type : str
            Type of query
        current_fen : str
            Current FEN position
            
        Returns:
        --------
        str
            Generated answer text only
        """
        result = self.generate_answer(query, retrieved_documents, query_type, current_fen)
        return result.get("answer", "Error generating answer")
    
    def set_quality_assessment(self, enabled: bool):
        """Enable or disable quality assessment"""
        self.enable_quality_assessment = enabled
        logger.info(f"Quality assessment {'enabled' if enabled else 'disabled'}")
    
    def set_accuracy_tracking(self, enabled: bool):
        """Enable or disable accuracy tracking"""
        self.enable_accuracy_tracking = enabled
        logger.info(f"Accuracy tracking {'enabled' if enabled else 'disabled'}")
    
    def get_enhanced_capabilities(self) -> Dict[str, bool]:
        """Get status of enhanced capabilities"""
        return {
            "quality_assessment": self.enable_quality_assessment,
            "accuracy_tracking": self.enable_accuracy_tracking,
            "context_awareness": True,
            "performance_monitoring": True
        }

    def _handle_contextual_filtering(self, query: str, session_id: str, memory_manager, retrieved_documents: List[Dict] = None, query_type: str = None) -> Dict[str, Any]:
        """
        Handle contextual filtering request
        
        Parameters:
        -----------
        query : str
            The user's query
        session_id : str
            Session identifier for tracking and conversation memory
        memory_manager : ConversationMemoryManager
            Conversation memory manager instance
        retrieved_documents : List[Dict]
            Retrieved documents
        query_type : str
            Query type from the router agent
            
        Returns:
        --------
        Dict[str, Any]
            Result of the contextual filtering or None if not a contextual request
        """
        if not memory_manager or not session_id:
            return None
        
        try:
            # Check if this is already classified as a contextual filter request
            is_contextual = (query_type == "contextual_filter")
            
            # If not already classified, check using the enhanced router agent
            if not is_contextual:
                from backend.etl.agents.enhanced_router_agent import EnhancedRouterAgent
                from backend.services.advanced_filtering_service import AdvancedFilteringService
                
                router_agent = EnhancedRouterAgent()
                is_contextual = router_agent.detect_contextual_filter_request(query)
            
            if not is_contextual:
                return None
            
            logger.info(f"Detected contextual filter request: '{query}' (query_type: {query_type})")
            
            # Get the last search results from conversation memory
            last_search_data = memory_manager.get_last_search_results(session_id)
            
            if not last_search_data:
                logger.warning(f"No previous search results found for contextual filtering in session {session_id}")
                return {
                    "answer": "I don't see any previous search results to filter. Please search for games first, then I can help you filter them.",
                    "query_type": "contextual_filter_error",
                    "error": "No previous search results found"
                }
            
            previous_results, search_context = last_search_data
            logger.info(f"Found {len(previous_results)} previous results to filter")
            
            # Parse the filter request from the query
            from backend.etl.agents.enhanced_router_agent import EnhancedRouterAgent
            router_agent = EnhancedRouterAgent()
            filter_request = router_agent.parse_filter_query(query)
            
            # Apply contextual filtering
            from backend.services.advanced_filtering_service import AdvancedFilteringService
            filtering_service = AdvancedFilteringService()
            filter_result = filtering_service.filter_games_contextual(filter_request, previous_results)
            
            # Generate a response
            filtered_games = filter_result.get('games', [])
            original_count = filter_result.get('original_count', 0)
            filtered_count = filter_result.get('total_count', 0)
            filters_applied = filter_result.get('filters_applied', {})
            
            if filter_result.get('error'):
                answer = f"I encountered an error while filtering the results: {filter_result['error']}"
            elif filtered_count == 0:
                answer = f"No games match your filter criteria from the {original_count} previous results."
                if filters_applied:
                    answer += f" Filters applied: {', '.join(f'{k}: {v}' for k, v in filters_applied.items())}"
            else:
                answer = f"Filtered {original_count} games down to {filtered_count} games"
                if filters_applied:
                    answer += f" using filters: {', '.join(f'{k}: {v}' for k, v in filters_applied.items())}"
                answer += ".\n\n"
                
                # Add game details
                for i, game in enumerate(filtered_games[:10], 1):  # Show first 10 games
                    white = game.get('white_player') or game.get('White', 'Unknown')
                    black = game.get('black_player') or game.get('Black', 'Unknown')
                    result = game.get('result') or game.get('Result', '*')
                    event = game.get('event') or game.get('Event', 'Unknown Event')
                    date = game.get('date') or game.get('Date', 'Unknown Date')
                    white_elo = game.get('white_elo') or game.get('WhiteElo', 'N/A')
                    black_elo = game.get('black_elo') or game.get('BlackElo', 'N/A')
                    
                    answer += f"{i}. **{white}** ({white_elo}) vs **{black}** ({black_elo})\n"
                    answer += f"   Result: {result} | Event: {event} | Date: {date}\n\n"
                
                if filtered_count > 10:
                    answer += f"... and {filtered_count - 10} more games."
            
            return {
                "answer": answer,
                "query_type": "contextual_filter",
                "filtered_games": filtered_games,
                "original_count": original_count,
                "total_count": filtered_count,
                "filters_applied": filters_applied,
                "processing_time": filter_result.get('processing_time', 0),
                "context": {
                    "filter_type": "contextual",
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error in contextual filtering: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "answer": f"I encountered an error while trying to filter the previous results: {str(e)}",
                "query_type": "contextual_filter_error",
                "error": str(e)
            } 