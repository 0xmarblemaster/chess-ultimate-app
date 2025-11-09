import logging
from typing import Optional, Dict, Any, List, Tuple, Union
from .shared_types import RagState
from .enhanced_router_agent import EnhancedRouterAgent as RouterAgent # Import the enhanced class for type hinting
from .unified_retriever import unified_retriever, RetrievalResult # Import unified retriever
from .answer_agent import AnswerAgent # For type hinting the instance
from .opening_agent import find_opening_by_fen # Import the new opening agent function
from .game_search_agent import find_games_by_criteria # ADDED: Import game search agent function
from .. import config as etl_config_module  # Import config for RETRIEVER_TOP_K

# Placeholder for other specialist agents to be imported later
# from .stockfish_agent import analyze_with_stockfish
# from .lesson_agent import find_lessons_by_diagram, find_lessons_by_topic

logger = logging.getLogger(__name__)

def _convert_game_filter_request_to_dict(game_filter_request) -> Optional[Dict[str, Any]]:
    """
    Convert a GameFilterRequest object to a dictionary format that the game search agent can understand.
    
    Args:
        game_filter_request: GameFilterRequest object or None
        
    Returns:
        Dictionary with keys the game search agent expects, or None if no filters
    """
    if not game_filter_request:
        return None
    
    # Convert GameFilterRequest object to dictionary
    filters_dict = {}
    
    # Player filters
    if hasattr(game_filter_request, 'white_player') and game_filter_request.white_player:
        filters_dict['white_player'] = game_filter_request.white_player
    
    if hasattr(game_filter_request, 'black_player') and game_filter_request.black_player:
        filters_dict['black_player'] = game_filter_request.black_player
        
    if hasattr(game_filter_request, 'any_player') and game_filter_request.any_player:
        filters_dict['any_player'] = game_filter_request.any_player
    
    # Opening filters
    if hasattr(game_filter_request, 'eco_code') and game_filter_request.eco_code:
        filters_dict['eco'] = game_filter_request.eco_code
    
    # Event filters
    if hasattr(game_filter_request, 'event') and game_filter_request.event:
        filters_dict['event'] = game_filter_request.event
    
    # Return None if no meaningful filters were found
    return filters_dict if filters_dict else None

def run_pipeline(initial_query: str, 
                 router_agent_instance: RouterAgent,
                 retriever_agent_instance: Any,  # Legacy parameter, not used with unified system
                 answer_agent_instance: AnswerAgent, 
                 current_board_fen: Optional[str] = None,
                 session_pgn: Optional[str] = None,
                 session_id: Optional[str] = None) -> RagState:
    """
    Main orchestrator for the RAG pipeline using the unified retriever system.
    Manages the flow of information through various agents using a shared state.
    """
    logger.info(f"DEBUG: [Orchestrator] Pipeline started. Query: '{initial_query[:50]}...', FEN: {current_board_fen}, PGN: {session_pgn[:50] if session_pgn else 'None'}...")

    # Initialize RagState
    state: RagState = {
        "user_query": initial_query,
        "current_board_fen": current_board_fen,
        "session_pgn": session_pgn,
        "answer_agent_instance": answer_agent_instance,
        "retrieved_chunks": [], 
        "lesson_data": [],      
        "router_metadata": {},   
        "opening_data": None
    }

    # 1. Router Agent: Classify query and update state
    try:
        state = router_agent_instance.classify_query(state)
        logger.info(f"DEBUG: [Orchestrator] Router updated state: Type '{state.get('query_type')}', Meta: {state.get('router_metadata')}")
    except Exception as e:
        logger.error(f"ERROR: [Orchestrator] RouterAgent failed: {e}")
        state["query_type"] = "error"
        state["error_message"] = f"Error in query classification: {str(e)}"
        state["final_answer"] = "Sorry, I had trouble understanding your request."
        return state

    # 2. Unified Retrieval System
    if state.get("query_type") != "error":
        query_type = state["query_type"]
        
        try:
            # Use unified retriever for all query types
            logger.info(f"DEBUG: [Orchestrator] Using unified retriever for query type: {query_type}")
            
            retrieval_result: RetrievalResult = unified_retriever.retrieve(
                query=initial_query,
                current_fen=current_board_fen,
                session_id=session_id,
                metadata=state.get("router_metadata", {})
            )
            
            # Update state with retrieval results
            state["retrieved_chunks"] = retrieval_result.documents
            state["retrieval_metadata"] = {
                "total_found": retrieval_result.total_found,
                "query_type": retrieval_result.query_type,
                "filters_applied": retrieval_result.filters_applied,
                "execution_time": retrieval_result.execution_time,
                "source": retrieval_result.source
            }
            
            logger.info(f"DEBUG: [Orchestrator] Unified retriever found {retrieval_result.total_found} documents using {retrieval_result.query_type} strategy")
            logger.info(f"DEBUG: [Orchestrator] Filters applied: {retrieval_result.filters_applied}")
            
            # Handle special cases that need additional processing
            if query_type == "opening_lookup" and current_board_fen:
                # Add opening-specific data if available
                try:
                    opening_result = find_opening_by_fen(current_board_fen)
                    if opening_result and not opening_result.get("error"):
                        state["opening_data"] = opening_result
                        # Add to retrieved chunks if not already present
                        opening_chunk = {
                            "type": "opening_data",
                            "content": opening_result,
                            "source": "opening_agent"
                        }
                        state["retrieved_chunks"].append(opening_chunk)
                        logger.info(f"DEBUG: [Orchestrator] Added opening data for FEN: {current_board_fen}")
                except Exception as opening_error:
                    logger.warning(f"WARN: [Orchestrator] Opening lookup failed: {opening_error}")
            
            elif query_type == "move_history_lookup":
                # Add PGN data if available
                if session_pgn and session_pgn not in ["[No moves played yet]", "[Error generating PGN]"]:
                    pgn_chunk = {
                        "type": "pgn_data",
                        "content": session_pgn,
                        "source": "session_history"
                    }
                    state["retrieved_chunks"].append(pgn_chunk)
                    logger.info(f"DEBUG: [Orchestrator] Added PGN data: {session_pgn[:100]}...")
                else:
                    no_pgn_chunk = {
                        "type": "system_message",
                        "message": "No move history available for the current session."
                    }
                    state["retrieved_chunks"].append(no_pgn_chunk)
            
            elif query_type == "position_analysis" and current_board_fen:
                # Add Stockfish analysis
                try:
                    from backend.services.stockfish_engine import stockfish_engine_instance
                    
                    logger.info(f"DEBUG: [Orchestrator] Adding Stockfish analysis for FEN: {current_board_fen}")
                    
                    analysis_result = stockfish_engine_instance.analyze_fen(
                        fen=current_board_fen,
                        depth_limit=18,
                        multipv=3
                    )
                    
                    if analysis_result and len(analysis_result) > 0:
                        analysis_chunk = {
                            "type": "position_analysis",
                            "fen": current_board_fen,
                            "analysis": analysis_result,
                            "source": "stockfish_engine"
                        }
                        state["retrieved_chunks"].append(analysis_chunk)
                        logger.info(f"DEBUG: [Orchestrator] Added Stockfish analysis. Top move: {analysis_result[0].get('move', 'unknown')}")
                    else:
                        error_chunk = {
                            "type": "error",
                            "message": "Stockfish analysis returned no results"
                        }
                        state["retrieved_chunks"].append(error_chunk)
                        
                except Exception as analysis_error:
                    logger.error(f"ERROR: [Orchestrator] Stockfish analysis failed: {analysis_error}")
                    error_chunk = {
                        "type": "error",
                        "message": f"Error during Stockfish analysis: {str(analysis_error)}"
                    }
                    state["retrieved_chunks"].append(error_chunk)
            
            # Check if retrieval was successful
            if retrieval_result.total_found == 0 and retrieval_result.documents:
                # Check if we have error or message documents
                first_doc = retrieval_result.documents[0]
                if first_doc.get("type") == "error":
                    state["error_message"] = first_doc.get("message", "Unknown retrieval error")
                elif first_doc.get("type") == "message":
                    # This is just an informational message, not an error
                    logger.info(f"DEBUG: [Orchestrator] Retrieval message: {first_doc.get('message')}")
            
        except Exception as e:
            logger.error(f"ERROR: [Orchestrator] Unified retriever failed: {e}")
            state["error_message"] = f"Error during data retrieval: {str(e)}"
            state["retrieved_chunks"] = [{
                "type": "error",
                "message": f"Retrieval system error: {str(e)}"
            }]

    # 3. Answer Agent: Generate final response
    if state.get("query_type") != "error" or state.get("error_message"):
        try:
            # Call AnswerAgent's generate_answer with individual parameters
            answer_result = state["answer_agent_instance"].generate_answer(
                query=state["user_query"],
                retrieved_documents=state.get("retrieved_chunks", []),
                query_type=state.get("query_type", "direct"),
                current_fen=state.get("current_board_fen"),
                session_id=session_id
            )
            
            # Extract the answer from the result and update state
            if isinstance(answer_result, dict) and "answer" in answer_result:
                state["final_answer"] = answer_result["answer"]
                # Store additional answer metadata
                if "quality_metrics" in answer_result:
                    state["quality_metrics"] = answer_result["quality_metrics"]
                if "accuracy_measurement" in answer_result:
                    state["accuracy_measurement"] = answer_result["accuracy_measurement"]
            else:
                # Fallback if answer_result is just a string (legacy mode)
                state["final_answer"] = str(answer_result)
                
            logger.info(f"DEBUG: [Orchestrator] AnswerAgent updated state. Final Answer: {state.get('final_answer', '')[:100]}...")
            
        except Exception as e:
            logger.error(f"ERROR: [Orchestrator] AnswerAgent failed catastrophically: {e}")
            state["error_message"] = (state.get("error_message", "") + f" Critical error in answer generation: {str(e)}").strip()
            state["final_answer"] = "Sorry, I encountered a critical error while trying to generate an answer."
    
    # Fallback if final_answer is still not set but an error_message exists
    if state.get("error_message") and not state.get("final_answer"):
        state["final_answer"] = state.get("error_message")
    
    # Clean up answer_agent_instance from the state before returning
    if 'answer_agent_instance' in state:
        del state['answer_agent_instance']

    return state 