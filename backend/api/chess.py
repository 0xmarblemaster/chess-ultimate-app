from flask import Blueprint, request, jsonify, current_app
import chess
import json
import logging
from backend.stockfish_analyzer import (
    analyze_fen_with_stockfish, 
    analyze_fen_with_stockfish_service
)

# Create blueprint with URL prefix
chess_api_blueprint = Blueprint('chess_api', __name__, url_prefix='/api/chess')
logger = logging.getLogger(__name__)

# Global game state will still be managed by the main app
# and accessed via app context or imported directly

@chess_api_blueprint.route('/analyze_position', methods=['POST'])
def analyze_position():
    """Analyze a chess position with Stockfish and return the results."""
    data = request.get_json()
    fen = data.get('fen')

    if not fen:
        return jsonify({"error": "FEN string is required"}), 400

    logger.info(f"Analyzing position with FEN: {fen}")
    
    # Use the new modular Stockfish service with a manual timeout
    logger.info("Attempting analysis with Stockfish service...")
    analysis_lines = analyze_fen_with_stockfish_service(
        fen_string=fen,
        time_limit=5.0,  # 5 second manual timeout
        depth_limit=8,   # Fast analysis for UI (1-2 seconds)
        multipv=3        # Changed from 1 to 3 to show 3 best lines
    )
    
    # Log results
    if analysis_lines:
        logger.info(f"Stockfish service returned {len(analysis_lines)} analysis lines")
        for i, line in enumerate(analysis_lines):
            logger.info(f"Analysis line {i+1}: {line.get('pv_san')} (Eval: {line.get('evaluation_string')})")
    else:
        logger.warning("Stockfish service returned no analysis lines")
    
    # Fallback to the old function if the new service fails
    if analysis_lines is None:
        logger.warning("Stockfish service analysis failed. Falling back to legacy method.")
        analysis_lines = analyze_fen_with_stockfish(
            fen_string=fen,
            time_limit=5.0,  # Same timeout for consistency
            depth_limit=8,   # Fast analysis for UI (1-2 seconds)
            multipv=3        # Changed from 1 to 3 to match the primary method
        )
        
        # Log results from fallback
        if analysis_lines:
            logger.info(f"Legacy method returned {len(analysis_lines)} analysis lines")
            for i, line in enumerate(analysis_lines):
                logger.info(f"Legacy analysis line {i+1}: {line.get('pv_san')} (Eval: {line.get('evaluation_string')})")
        else:
            logger.warning("Legacy method also returned no analysis lines")

    if analysis_lines is None:
        logger.error("Both Stockfish analysis methods failed")
        return jsonify({
            "error": "Stockfish engine not available or analysis failed after retry."
        }), 503
        
    best_line_info = analysis_lines[0] if analysis_lines else {}
    commentary = f"Stockfish analysis: Best line eval={best_line_info.get('evaluation_string', 'N/A')}, Line={best_line_info.get('pv_san', 'N/A')}"

    # Log the final response
    logger.info(f"Returning {len(analysis_lines)} analysis lines for FEN: {fen}")
    logger.info(f"Best line: {best_line_info.get('pv_san', 'N/A')}")
    
    return jsonify({
        "fen": fen,
        "lines": analysis_lines,
        "commentary": commentary, 
        "is_critical": False # Placeholder
    })

@chess_api_blueprint.route('/set_fen', methods=['POST'])
def set_fen():
    """Set the current FEN for a session's board state."""
    data = request.get_json()
    fen = data.get('fen')
    session_id = data.get('session_id')

    if not fen:
        return jsonify({"error": "FEN string is required"}), 400
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    # Access active_games from the main app context
    from app import active_games

    try:
        # Validate FEN format
        board = chess.Board(fen)
        
        # Update or create session
        if session_id in active_games:
            active_games[session_id]['board'] = board
            logger.info(f"Updated board FEN for session {session_id}: {fen}")
        else:
            active_games[session_id] = {'board': board}
            logger.info(f"Created new game for session {session_id} with FEN: {fen}")
            
        return jsonify({
            "fen": fen,
            "session_id": session_id,
            "isCheck": board.is_check(),
            "isCheckmate": board.is_checkmate(),
            "isStalemate": board.is_stalemate()
        }), 200
    except ValueError as e:
        logger.error(f"Invalid FEN format: {fen}. Error: {e}")
        return jsonify({"error": f"Invalid FEN format: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error setting FEN: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500 