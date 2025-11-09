from flask import Blueprint, request, jsonify, current_app
import logging
import chess
import time
import traceback

# Create blueprint with URL prefix
chat_api_blueprint = Blueprint('chat_api', __name__, url_prefix='/api/chat')
logger = logging.getLogger(__name__)

# System message for the chat
SYSTEM_MESSAGE_CHAT_INTERACTIVE = (
    f"You are an AI Chess Tutor. Your primary goal is to help users understand chess concepts, positions, and game play. "
    f"You have access to a function 'get_stockfish_analysis(fen_string)' to get Stockfish engine analysis for a given FEN position."
    f"You also have access to a function 'check_move_legality(fen_string, move_san)' which returns if a move is legal."
    f"When a user asks for the best move, or for analysis that would benefit from engine calculation, you MUST use 'get_stockfish_analysis' for the relevant FEN and incorporate its findings."
    f"If the user provides a FEN or describes a position, use that FEN for analysis. If the context implies a current board state, use that."
    f"When discussing specific moves:"
    f"1.  **Move Legality is Paramount:** Always verify move legality using 'check_move_legality' before suggesting moves. Never suggest illegal moves.\\n" +
    f"2.  **Clarity:** Explain your reasoning clearly and concisely, especially when it's based on Stockfish analysis (e.g., 'Stockfish suggests ... because ... and evaluates the position as ...').\\n" +
    f"3.  **Interactive Assistance:** If the user makes a move, acknowledge it. If they ask for hints or ideas, provide them based on sound chess principles and engine analysis if appropriate.\\n" +
    f"4.  **Board State:** If you refer to a specific position that should be shown on a visual board, end your response with [SET_FEN: <fen_string>]. Use the FEN relevant to your explanation.\\n" +
    f"5.  **Opening Recognition:** If the current FEN or sequence of moves corresponds to a known chess opening, identify it (e.g., 'This position is reached after the main line of the Ruy Lopez'). You may have access to opening data.\\n"
    f"User messages may include their current FEN state as `Current FEN: <fen_string>` or their last move as `User's last move: <move_san>`.\\n" + # Note: these backticks are for Markdown, not function calls
    f"If asked about an opening from a FEN, try to identify it. If provided with opening moves, identify the opening.\\n"
)

def detect_language(text):
    """Auto-detect language from text content.
    
    Args:
        text (str): The input text
        
    Returns:
        str: Language code ('ru' for Russian, 'en' for English, etc.)
    """
    if not text:
        return 'en'
    
    # Check for Cyrillic characters (Russian)
    cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
    total_letters = sum(1 for char in text if char.isalpha())
    
    # If more than 30% of alphabetic characters are Cyrillic, consider it Russian
    if total_letters > 0 and (cyrillic_count / total_letters) > 0.3:
        return 'ru'
    
    # Add more language detection logic here if needed
    # For now, default to English
    return 'en'

@chat_api_blueprint.route('', methods=['POST'])
def chat():
    """Handle chat requests from the user."""
    # Import llm_client and active_games from main app (local import)
    from app import llm_client, active_games
    
    if not llm_client:
        return jsonify({"error": "LLM client not configured. Please set API key."}), 503

    data = request.get_json()
    messages = data.get('messages')
    session_id = data.get('session_id')
    received_fen = data.get('fen') or data.get('current_fen') or data.get('current_board_fen')  # Check all parameter names
    language = data.get('language', 'en')  # Get language preference, default to English

    # Validate required parameters
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if not received_fen:
        return jsonify({"error": "fen is required"}), 400
    
    user_input = messages[-1]['content'] if messages else ""

    logger.info(f"Chat Request - Session ID: {session_id}, Received FEN: {received_fen}")
    logger.info(f"User Input: {user_input}")

    # Retrieve/Initialize/Synchronize Game State from Memory
    if session_id not in active_games:
        logger.info(f"Initializing new game state for session {session_id} with FEN: {received_fen}")
        try:
            # Initialize board with FEN from the first request of the session
            initial_board = chess.Board(received_fen)
            active_games[session_id] = {'board': initial_board}
        except ValueError:
            logger.error(f"Invalid initial FEN received from frontend: {received_fen}")
            return jsonify({"error": f"Invalid initial FEN provided: {received_fen}"}), 400
    
    session_state = active_games[session_id]
    board = session_state['board']

    # Synchronize backend board with frontend FEN if they differ
    if received_fen != board.fen():
        logger.info(f"FEN mismatch! Frontend FEN: {received_fen}, Backend FEN: {board.fen()}. Updating backend state.")
        try:
            board = chess.Board(received_fen)
            active_games[session_id]['board'] = board
        except ValueError:
            logger.error(f"Invalid FEN received from frontend during sync: {received_fen}")
            return jsonify({"error": f"Invalid FEN received: {received_fen}"}), 400

    try:
        # Import enhanced answer agent from etl.agents (local import)
        from etl.agents import answer_agent_instance as etl_answer_agent
        
        if not etl_answer_agent:
            logger.error("AnswerAgent not available from etl.agents")
            return jsonify({"error": "Chat AI not initialized. Please check server configuration."}), 503

        # Use the enhanced answer agent that includes conversation memory
        if language == 'ru':
            query_text = f"Please respond in Russian language. User query: {user_input}"
        elif language == 'kz':
            query_text = f"Please respond in Kazakh language. User query: {user_input}"
        else:
            query_text = user_input
            
        enhanced_response = etl_answer_agent.generate_answer(
            query=query_text,
            retrieved_documents=None,  # Let the agent handle retrieval if needed
            query_type="chat",
            current_fen=board.fen(),
            session_id=session_id
        )
        
        answer = enhanced_response.get("answer", "Sorry, I couldn't generate a response.")
        
        # Generate PGN for response
        try:
            game_pgn = chess.pgn.Game()
            temp_board_pgn = board.copy()
            moves_to_add = []
            while temp_board_pgn.move_stack:
                moves_to_add.append(temp_board_pgn.pop())
            moves_to_add.reverse()
            node = game_pgn
            for move in moves_to_add:
                node = node.add_variation(move)
            pgn_exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
            final_pgn = game_pgn.accept(pgn_exporter)
        except Exception as pgn_error:
            logger.error(f"Error generating PGN: {pgn_error}")
            final_pgn = "[PGN generation error]"

        # Get Stockfish analysis for response
        from stockfish_analyzer import analyze_fen_with_stockfish
        analysis_lines = analyze_fen_with_stockfish(fen_string=board.fen(), time_limit=None, depth_limit=24, multipv=3)
        if not analysis_lines:
            analysis_lines = []

        game_ended = board.is_game_over(claim_draw=board.can_claim_draw())
        outcome_obj = board.outcome(claim_draw=board.can_claim_draw()) if game_ended else None
        
        response_data = {
            "reply": answer,
            "fen": board.fen(),
            "pgn": final_pgn,
            "is_game_over": game_ended,
            "outcome": outcome_obj.result() if outcome_obj else None,
            "analysis_lines": analysis_lines,
            "conversation_memory_used": enhanced_response.get("conversation_history_used", False),
            "quality_metrics": enhanced_response.get("quality_metrics"),
            "query_id": enhanced_response.get("query_id"),
            "answer_id": enhanced_response.get("answer_id")
        }
        
        logger.info(f"Enhanced chat response generated with conversation memory for session {session_id}")
        logger.info(f"Conversation history used: {enhanced_response.get('conversation_history_used', False)}")
        
        return jsonify(response_data)
        
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Error in chat endpoint: {e}\n{stack_trace}")
        return jsonify({"error": f"An error occurred processing the chat: {str(e)}"}), 500

@chat_api_blueprint.route('/progress/<session_id>', methods=['GET'])
def get_progress(session_id):
    """Get progress information for a specific session"""
    from etl.agents.progress_tracker import progress_manager
    
    try:
        progress_info = progress_manager.get_progress(session_id)
        
        if progress_info is None:
            return jsonify({
                "session_id": session_id,
                "error": "No active progress tracking for this session"
            }), 404
        
        return jsonify(progress_info), 200
        
    except Exception as e:
        logger.error(f"Error getting progress for session {session_id}: {e}")
        return jsonify({
            "session_id": session_id,
            "error": f"Failed to get progress: {str(e)}"
        }), 500

@chat_api_blueprint.route('/rag', methods=['POST'])
def rag_query():
    """RAG query endpoint using the orchestrator."""
    # Import tracking and analytics modules (local imports)
    from etl.agents.query_analytics import query_analytics
    from etl.agents.progress_tracker import progress_manager
    
    # Import app-level components and agents (local imports)
    from app import active_games, user_sessions
    # Always import fresh to avoid getting stale fallback instances
    from etl.agents import answer_agent_instance as etl_answer_agent
    from etl.agents.orchestrator import run_pipeline
    from etl.agents import router_agent_instance, retriever_agent_instance
    from stockfish_analyzer import analyze_fen_with_stockfish, analyze_fen_with_stockfish_service
    
    # Start timing for analytics
    start_time = time.time()
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data or missing Content-Type header"}), 400
    
    query = data.get('query') or data.get('message')  # Support both 'query' and 'message' fields
    session_id = data.get('session_id')
    received_fen = data.get('fen') or data.get('current_fen') or data.get('current_board_fen')  # Check all parameter names
    query_type = data.get('query_type')  # Get query_type from request (None if not provided)
    language = data.get('language')  # Get language preference from request (don't default yet)

    # Validate required parameters first
    if not query:
        return jsonify({"error": "query or message is required"}), 400
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    # Auto-detect language if not provided (now that we know query is not None)
    if not language:
        language = detect_language(query)
        logger.info(f"Auto-detected language: {language} for query: {query[:50]}...")
    else:
        logger.info(f"Using provided language: {language}")

    # Create progress tracker for this session
    progress_tracker = progress_manager.create_tracker(session_id)
    
    if not etl_answer_agent:
        logger.error("Answer agent not initialized. RAG functionality unavailable.")
        progress_tracker.fail_step("query_validation", "RAG system not initialized")
        return jsonify({
            "error": "RAG system not initialized (no answer agent). Check API keys."
        }), 503

    # Start query validation step
    progress_tracker.start_step("query_validation", "Validating query parameters")

    # Determine current board FEN from active games or user sessions
    current_board_fen_for_rag = None
    current_pgn_for_rag = None

    # If frontend sent a FEN directly with this request, prioritize it
    if received_fen:
        current_board_fen_for_rag = received_fen
        logger.info(f"Using FEN directly from request: {current_board_fen_for_rag}")
        
        # Update user_sessions for this session_id
        user_sessions[session_id] = user_sessions.get(session_id, {})
        user_sessions[session_id]['current_fen'] = current_board_fen_for_rag
        
        # Also update active_games if needed
        if session_id in active_games and 'board' in active_games[session_id]:
            try:
                import chess
                active_games[session_id]['board'] = chess.Board(received_fen)
                logger.info(f"Updated active_games board with received FEN: {received_fen}")
            except Exception as e:
                logger.error(f"Error updating active_games with received FEN: {e}")
    # Otherwise try to get from active_games first (where chess.Board objects are stored)
    elif session_id in active_games and 'board' in active_games[session_id]:
        board = active_games[session_id]['board']
        current_board_fen_for_rag = board.fen()
        
        # Generate PGN from move stack if available
        if board.move_stack:
            current_pgn_for_rag = " ".join([board.san(m) for m in board.move_stack])
        else:
            current_pgn_for_rag = "[No moves yet]"
            
        logger.info(f"Using board FEN from active_games for RAG: {current_board_fen_for_rag}")
        
        # Ensure user_sessions is also updated with this FEN
        user_sessions[session_id] = user_sessions.get(session_id, {})
        user_sessions[session_id]['current_fen'] = current_board_fen_for_rag
    # Otherwise, try to get from user_sessions (RAG tracking)
    elif session_id in user_sessions and 'current_fen' in user_sessions[session_id]:
        current_board_fen_for_rag = user_sessions[session_id]['current_fen']
        logger.info(f"Using FEN from user_sessions for RAG: {current_board_fen_for_rag}")
    else:
        logger.warning(f"No FEN found for session {session_id} in RAG query. Context will be limited.")

    # Complete query validation
    progress_tracker.complete_step("query_validation", {"query_length": len(query)})

    # Add language instruction to query if Russian or Kazakh is selected
    if language == 'ru':
        query_with_language = f"Please respond in Russian language. User query: {query}"
        logger.info(f"Modified query for Russian language: {query_with_language}")
    elif language == 'kz':
        query_with_language = f"Please respond in Kazakh language. User query: {query}"
        logger.info(f"Modified query for Kazakh language: {query_with_language}")
    else:
        query_with_language = query

    try:
        # Call the orchestrator's run_pipeline function
        pipeline_state = run_pipeline(
            initial_query=query_with_language,  # Use language-modified query
            router_agent_instance=router_agent_instance,
            retriever_agent_instance=retriever_agent_instance,
            answer_agent_instance=etl_answer_agent,
            current_board_fen=current_board_fen_for_rag,
            session_pgn=current_pgn_for_rag,
            session_id=session_id  # Pass session_id for conversation memory
        )
        
        # Start Stockfish analysis step
        progress_tracker.start_step("stockfish_analysis", "Running chess engine analysis")
        
        # Determine the FEN for which to run analysis for the UI
        final_fen_for_ui_analysis = pipeline_state.get("fen_for_analysis", 
                                  pipeline_state.get("current_board_fen", 
                                                     current_board_fen_for_rag))

        # When running analysis for UI, use the new service with a timeout
        analysis_lines_for_ui = []
        if final_fen_for_ui_analysis:
            try:
                # Use short analysis (depth 10-12) for better UI responsiveness
                analysis_lines_for_ui = analyze_fen_with_stockfish_service(
                    fen_string=final_fen_for_ui_analysis,
                    multipv=3,  # Top 3 lines for UI display
                    depth_limit=12,  # Moderate depth for speed
                    time_limit=3.0  # Reasonable timeout for UI
                )
                logger.info(f"Generated UI analysis for FEN: {final_fen_for_ui_analysis}")
                progress_tracker.complete_step("stockfish_analysis", {
                    "lines_generated": len(analysis_lines_for_ui) if analysis_lines_for_ui else 0
                })
            except Exception as analysis_error:
                logger.error(f"Error generating UI Stockfish analysis: {analysis_error}")
                try:
                    # Fallback to primary analysis function with shorter timeout
                    analysis_lines_for_ui = analyze_fen_with_stockfish(
                        fen_string=final_fen_for_ui_analysis,
                        multipv=3,
                        depth_limit=10,
                        time_limit=2.0
                    )
                    logger.info(f"Used fallback analysis for UI with FEN: {final_fen_for_ui_analysis}")
                    progress_tracker.complete_step("stockfish_analysis", {
                        "lines_generated": len(analysis_lines_for_ui) if analysis_lines_for_ui else 0,
                        "used_fallback": True
                    })
                except Exception as e:
                    logger.error(f"All Stockfish analysis attempts for UI failed: {e}")
                    analysis_lines_for_ui = None
                    progress_tracker.fail_step("stockfish_analysis", str(e))
            
            # Ensure it's an empty list if analysis fails, not None
            if analysis_lines_for_ui is None:
                analysis_lines_for_ui = []
                logger.warning(f"All Stockfish analysis attempts for UI returned None for FEN: {final_fen_for_ui_analysis}")
        else:
            logger.warning("No FEN determined for UI Stockfish analysis in RAG query response.")
            progress_tracker.skip_step("stockfish_analysis", "No FEN available for analysis")

        # Start response formatting step
        progress_tracker.start_step("response_formatting", "Finalizing response")

        # Update the RAG session tracking
        user_sessions[session_id] = {
            'current_fen': final_fen_for_ui_analysis or current_board_fen_for_rag,
            'last_query': query,
            'last_response': pipeline_state.get("final_answer", ""),
            'last_query_time': time.time()
        }

        # Calculate response time for analytics
        response_time = time.time() - start_time
        
        # Track query analytics
        query_analytics.track_query(
            session_id=session_id,
            query=query,
            classification=pipeline_state.get("query_type", "unknown"),
            success=bool(pipeline_state.get("final_answer")),
            response_time=response_time,
            error_message=pipeline_state.get("error_message"),
            retrieved_count=len(pipeline_state.get("retrieved_chunks", [])),
            current_fen=current_board_fen_for_rag
        )

        # Complete response formatting and finish tracking
        progress_tracker.complete_step("response_formatting", {
            "response_length": len(pipeline_state.get("final_answer", "")),
            "sources_count": len(pipeline_state.get("retrieved_chunks", []))
        })
        progress_tracker.finish(success=True)

        return jsonify({
            "answer": pipeline_state.get("final_answer", ""),
            "sources": pipeline_state.get("retrieved_chunks", []),
            "metadata": pipeline_state.get("router_metadata", {}),
            "query_type": pipeline_state.get("query_type", "unknown"),
            "fen": final_fen_for_ui_analysis,  # Return FEN as 'fen' for consistency
            "analysis_lines": analysis_lines_for_ui,
            "opening_detection": pipeline_state.get("opening_details", {}),
            "response_time": response_time,  # Include response time in response
            "progress_session_id": session_id  # Include session ID for progress tracking
        }), 200

    except Exception as e:
        # Calculate response time even for errors
        response_time = time.time() - start_time
        
        # Track failed query
        query_analytics.track_query(
            session_id=session_id,
            query=query,
            classification="error",
            success=False,
            response_time=response_time,
            error_message=str(e),
            current_fen=current_board_fen_for_rag
        )
        
        # Mark progress as failed
        progress_tracker.finish(success=False)
        
        stack_trace = traceback.format_exc()
        logger.error(f"Error in RAG query: {e}\n{stack_trace}")
        return jsonify({"error": f"An error occurred during the RAG query: {str(e)}"}), 500 