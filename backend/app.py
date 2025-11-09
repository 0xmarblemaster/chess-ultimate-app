import sys
import os
import json
import logging
import time
import uuid
import socket
import threading
import queue
import traceback
from datetime import datetime
import argparse
import re  # Import re module for regular expressions
import atexit
import signal
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Tuple

# --- Start sys.path modification ---
# When running from backend directory: python app.py
# backend_dir is /home/marblemaster/Desktop/Cursor/mvp1/backend (dynamic)
backend_dir = os.path.dirname(os.path.abspath(__file__))
# mvp1_dir is /home/marblemaster/Desktop/Cursor/mvp1 (parent directory)
mvp1_dir = os.path.dirname(backend_dir)

# Add both backend_dir and mvp1_dir to sys.path for proper imports
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)  # Add backend dir first for local imports
if mvp1_dir not in sys.path:
    sys.path.insert(1, mvp1_dir)     # Add mvp1 dir for any backend.* imports
# --- End sys.path modification ---

print(f"Current Working Directory: {os.getcwd()}")
print(f"Backend Directory: {backend_dir}")
print(f"MVP1 Directory: {mvp1_dir}")
print(f"Modified sys.path: {sys.path[:3]}...")  # Show first 3 paths

from flask import Flask, request, jsonify
from flask_cors import CORS
import chess
import chess.engine
import chess.pgn
import io
import logging
from dotenv import load_dotenv
import openai
import threading
import subprocess
import tempfile
from werkzeug.utils import secure_filename
import re
from flask_socketio import SocketIO, emit
import atexit
import json
from concurrent.futures import ThreadPoolExecutor
import signal
from etl import config as etl_config  # Local import from backend/etl
from etl.agents.orchestrator import run_pipeline  # Local import
from etl.agents.answer_agent import AnswerAgent  # Local import  
from etl.agents import router_agent_instance, retriever_agent_instance  # Local import
from stockfish_analyzer import (  # Local import from backend/
    analyze_fen_with_stockfish, 
    analyze_fen_with_stockfish_service, 
    init_stockfish as init_stockfish_module, 
    quit_stockfish
)
from etl.config import WEAVIATE_URL, WEAVIATE_OPENING_CLASS_NAME, WEAVIATE_GAMES_CLASS_NAME  # Local import
from etl.agents import opening_agent  # Local import

# +++ Import API blueprints module +++
from api.register import register_blueprints  # Local import from backend/api

load_dotenv(dotenv_path=os.path.join(mvp1_dir, '.env')) # Ensure .env is loaded from project root mvp1

# Initialize Stockfish engine at startup
# Setup basic logging first so init_stockfish_module can log
# This should be done *after* load_dotenv if STOCKFISH_PATH is in .env
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(module)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__) # Get logger for app.py

try:
    logger.info("Attempting to initialize Stockfish engine via app.py startup...")
    if init_stockfish_module(): # Call the imported init_stockfish function
        logger.info("Stockfish engine initialized successfully from app.py.")
    else:
        logger.error("Stockfish engine failed to initialize from app.py. Analysis features might be impacted.")
except Exception as e:
    logger.error(f"Exception during Stockfish initialization in app.py: {e}", exc_info=True)

app = Flask(__name__)

# +++ Basic Logging Configuration +++
# This will help capture logs from other modules like RouterAgent if they use logging.getLogger()
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s %(levelname)s %(name)s %(module)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
# You might want to direct Flask's default logger to use this too, or customize further.
# For now, this sets up basicConfig which other modules using logging.getLogger() will pick up.

CORS(app)  # Allow requests from the frontend
socketio = SocketIO(app, cors_allowed_origins="*")  # Setup SocketIO with CORS

# +++ Register all API blueprints +++
register_blueprints(app)

# Check if voice API endpoints are registered
voice_routes = [rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api/voice')]
if voice_routes:
    app.logger.info(f"Voice API registered with {len(voice_routes)} routes: {[route.rule for route in voice_routes]}")
else:
    app.logger.warning("Voice API routes not found. Check if voice_api_blueprint is registered correctly.")

# In-memory store for RAG query sessions (FEN tracking)
user_sessions = {} # For tracking FEN per session_id in RAG queries
session_lock = threading.Lock() # To protect access to user_sessions

# --- Stockfish Integration ---
# All stockfish logic (engine, init_stockfish, analysis_lock) is now in stockfish_analyzer.py
# We might still call init_stockfish_module() here during app setup if needed,
# or rely on it being called when stockfish_analyzer is imported.
# The stockfish_analyzer module calls init_stockfish() on import.

# --- LLM Client Setup (Anthropic/OpenAI/Deepseek Compatible) ---
# Look for ANTHROPIC_API_KEY first, then OPENAI_API_KEY
api_key = os.getenv("ANTHROPIC_API_KEY")
base_url = None
model_name = "claude-3-5-sonnet-20241022" # Default Anthropic model
llm_provider = "anthropic"

if api_key:
    print("INFO: Found ANTHROPIC_API_KEY, attempting to use with Anthropic endpoint and model claude-3-5-sonnet-20241022.")
    # base_url remains None (default Anthropic), model_name is already set
else:
    print("WARNING: ANTHROPIC_API_KEY environment variable not found.")
    # Fallback to OPENAI_API_KEY
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("INFO: Found OPENAI_API_KEY, attempting to use with default OpenAI endpoint and model gpt-4o.")
        model_name = "gpt-4o"
        llm_provider = "openai"
    else:
        print("WARNING: OPENAI_API_KEY environment variable not found.")
        # Fallback to DEEPSEEK_API_KEY
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            print("INFO: Found DEEPSEEK_API_KEY, attempting to use with Deepseek endpoint.")
            base_url = "https://api.deepseek.com/v1" # Set Deepseek URL
            model_name = "deepseek-chat" # Set Deepseek model
            llm_provider = "deepseek"
        else:
            print("WARNING: Neither ANTHROPIC_API_KEY, OPENAI_API_KEY nor DEEPSEEK_API_KEY found.")
            print("Chat functionality will be disabled.")
            llm_client = None # Explicitly set to None here if no key found

# Import appropriate LLM wrapper based on provider
if api_key and 'llm_client' not in locals(): # Check if llm_client wasn't set to None already
    try:
        if llm_provider == "anthropic":
            from llm.anthropic_llm import AnthropicLLM  # Local import
            llm_client = AnthropicLLM(
                api_key=api_key,
                model_name=model_name,
                max_tokens=2000,
                temperature=0.7
            )
        else:
            # Use OpenAILLM wrapper for OpenAI and Deepseek
            from llm.openai_llm import OpenAILLM  # Local import
            llm_client = OpenAILLM(
                api_key=api_key,
                model_name=model_name,
                max_tokens=2000,
                temperature=0.7,
                base_url=base_url  # Pass base_url for Deepseek support
            )
        print(f"LLM client initialized successfully for provider: {llm_provider}, model: {model_name}")
    except Exception as e:
        print(f"Error initializing LLM client: {e}")
        llm_client = None
elif not api_key: # Ensure client is None if no key was ever found
     llm_client = None

# Instantiate AnswerAgent after llm_client is potentially initialized
# Use the proper answer agent instance from etl.agents that has conversation memory support
try:
    from etl.agents import answer_agent_instance  # Local import
    print("Using enhanced AnswerAgent with conversation memory from etl.agents")
    print(f"Answer agent LLM client status: {answer_agent_instance.llm_client is not None if answer_agent_instance else 'Agent is None'}")
except ImportError as e:
    print(f"Warning: Could not import enhanced AnswerAgent: {e}")
    # Fallback to creating a basic one
    answer_agent_instance = None # Default to None
    if llm_client:
        try:
            answer_agent_instance = AnswerAgent(llm_client=llm_client)
            print("AnswerAgent initialized successfully (fallback).")
        except Exception as e:
            print(f"Error initializing AnswerAgent: {e}")
            # answer_agent_instance remains None
    else:
        print("LLM client not available, AnswerAgent not initialized.")

# Initialize conversation memory system
conversation_memory_manager = None
conversation_summarizer = None

try:
    # Import conversation memory components
    from etl.agents.conversation_memory import initialize_conversation_memory  # Local import
    from etl.agents.conversation_summarizer import initialize_conversation_summarizer  # Local import
    
    # Initialize Redis client for conversation memory
    import redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    
    try:
        redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        # Test Redis connection
        redis_client.ping()
        print(f"Redis connection established at {redis_host}:{redis_port}")
        
        # Initialize conversation memory with SQLite database (file-based for simplicity)
        database_url = os.getenv("CONVERSATION_DB_URL", "sqlite:///conversation_memory.db")
        conversation_memory_manager = initialize_conversation_memory(redis_client, database_url)
        print("Conversation memory manager initialized successfully")
        
        # Update the answer agent with the conversation memory manager
        if answer_agent_instance and conversation_memory_manager:
            answer_agent_instance.conversation_memory_manager = conversation_memory_manager
            print("✅ Answer agent updated with conversation memory manager")
        
        # Initialize conversation summarizer if OpenAI key is available
        if api_key and base_url is None:  # Only for OpenAI API, not Deepseek
            conversation_summarizer = initialize_conversation_summarizer(api_key)
            print("Conversation summarizer initialized successfully")
        
    except redis.ConnectionError as e:
        print(f"Warning: Could not connect to Redis at {redis_host}:{redis_port}: {e}")
        print("Conversation memory will not be available. Consider starting Redis server.")
    except Exception as e:
        print(f"Warning: Failed to initialize Redis client: {e}")
        
except ImportError as e:
    print(f"Warning: Conversation memory system not available: {e}")
    print("Chat will work without conversation memory.")
except Exception as e:
    print(f"Warning: Failed to initialize conversation memory system: {e}")
    print("Chat will work without conversation memory.")

# In-memory store for active games (Session ID -> {'board': chess.Board})
active_games = {} # REINSTATE THIS

# --- Constants ---
# IMPORTANT: Adjust this path based on the actual location and execution method
# Point to the new CLI script
BOARD_TO_FEN_SCRIPT = "/home/marblemaster/Desktop/Cursor/board-to-fen/board_to_fen_cli.py" 
# Use the python executable from the board-to-fen tool's venv
BOARD_TO_FEN_PYTHON_EXECUTABLE = "/home/marblemaster/Desktop/Cursor/board-to-fen/.venv/bin/python"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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

@app.route('/')
def index():
    return "Chess Companion Backend is running!"

# API endpoints have been moved to specific blueprint modules
# See backend/api/ directory for all API routes

# --- Legacy Chat Endpoint (Moved to blueprint) --- 
@app.route('/api/chat', methods=['POST'])
def legacy_chat_endpoint():
    if not llm_client:
        return jsonify({"error": "LLM client not configured. Please set API key."}), 503

    data = request.get_json()
    messages = data.get('messages')
    session_id = data.get('session_id')
    received_fen = data.get('fen')

    # --- Validate Session ID and FEN ---
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if not received_fen:
        return jsonify({"error": "fen is required"}), 400

    user_input = messages[-1]['content'] if messages else ""

    print(f"\n--- Enhanced Chat Request with Conversation Memory ---")
    print(f"Session ID: {session_id}")
    print(f"Received FEN: {received_fen}")
    print(f"User Input: {user_input}")

    # --- Retrieve/Initialize/Synchronize Game State from Memory ---
    if session_id not in active_games:
        print(f"Initializing new game state for session {session_id} with FEN: {received_fen}")
        try:
            initial_board = chess.Board(received_fen)
            active_games[session_id] = {'board': initial_board}
        except ValueError:
            print(f"ERROR: Invalid initial FEN received from frontend: {received_fen}")
            return jsonify({"error": f"Invalid initial FEN provided: {received_fen}"}), 400
    
    session_state = active_games[session_id]
    board = session_state['board']

    # Synchronize backend board with frontend FEN if they differ
    if received_fen != board.fen():
        print(f"FEN mismatch! Frontend FEN: {received_fen}, Backend FEN: {board.fen()}. Updating backend state.")
        try:
            board = chess.Board(received_fen)
            active_games[session_id]['board'] = board
        except ValueError:
            print(f"ERROR: Invalid FEN received from frontend during sync: {received_fen}")
            return jsonify({"error": f"Invalid FEN received: {received_fen}"}), 400

    print(f"Current synchronized FEN for session {session_id}: {board.fen()}")

    # === Use Enhanced Answer Agent with Conversation Memory ===
    if not answer_agent_instance:
        print("ERROR: AnswerAgent not available")
        return jsonify({"error": "Chat AI not initialized. Please check server configuration."}), 503

    try:
        # Use the enhanced answer agent that includes conversation memory
        enhanced_response = answer_agent_instance.generate_answer(
            query=user_input,
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
            print(f"Error generating PGN: {pgn_error}")
            final_pgn = "[PGN generation error]"

        # Get Stockfish analysis for response
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
        
        print(f"Enhanced chat response generated with conversation memory for session {session_id}")
        print(f"Conversation history used: {enhanced_response.get('conversation_history_used', False)}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in enhanced chat processing: {e}")
        return jsonify({"error": f"An error occurred processing your message: {str(e)}"}), 500

# --- Helper Function ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# +++ Update diagnostic print +++
print("DEBUG: Attempting to register /api/fen_upload_test route...") 

# --- New Route for Image Upload --- 
@app.route('/api/fen_upload_test', methods=['POST'])
def fen_from_image_endpoint():
    if 'image' not in request.files:
        return jsonify({"error": "No image file part in the request"}), 400
    
    file = request.files['image']

    if file.filename == '':
        return jsonify({"error": "No image file selected"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename) # Sanitize filename
        # Create a secure temporary file
        temp_file = None
        try:
            # Use NamedTemporaryFile to get a path easily, ensure it's deleted
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file_obj:
                file.save(temp_file_obj.name)
                temp_file_path = temp_file_obj.name
            
            print(f"Saved uploaded image temporarily to: {temp_file_path}")

            # --- Execute the board-to-fen script --- 
            command = [BOARD_TO_FEN_PYTHON_EXECUTABLE, BOARD_TO_FEN_SCRIPT, temp_file_path]
            print(f"Executing command: {' '.join(command)}")
            
            result = subprocess.run(command, capture_output=True, text=True, check=False) # Don't check=True yet

            print(f"board-to-fen stdout: {result.stdout}")
            print(f"board-to-fen stderr: {result.stderr}")

            if result.returncode != 0:
                error_msg = f"board-to-fen script failed: {result.stderr or 'Unknown error'}"
                print(f"ERROR: {error_msg}")
                return jsonify({"error": error_msg}), 500

            # --- Process and Validate Output --- 
            extracted_fen_fragment = result.stdout.strip() 
            if not extracted_fen_fragment:
                 return jsonify({"error": "board-to-fen script returned empty output."}), 500
            
            # --- Construct full FEN ---
            # Assume White to move, standard castling, no en passant, standard clocks
            full_fen = f"{extracted_fen_fragment} w KQkq - 0 1"
            print(f"Constructed full FEN: {full_fen}")

            # Validate the FULL FEN string using python-chess
            try:
                board_check = chess.Board(full_fen)
                print(f"Successfully validated full FEN: {full_fen}")
                # Send the full FEN back to the frontend
                return jsonify({"fen": full_fen}), 200 
            except ValueError:
                print(f"ERROR: Constructed FEN is invalid: {full_fen}")
                # Include the invalid FEN in the error for easier debugging
                return jsonify({"error": f"Failed to parse constructed FEN: {full_fen}"}), 500

        except Exception as e:
            print(f"Error processing image upload: {e}")
            return jsonify({"error": "Internal server error during image processing."}), 500
        finally:
            # --- Clean up the temporary file --- 
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print(f"Removed temporary file: {temp_file_path}")
                except OSError as e:
                    print(f"Error removing temporary file {temp_file_path}: {e}")
    else:
        return jsonify({"error": "Invalid file type. Allowed types: png, jpg, jpeg"}), 400

# --- ETL Endpoints ---
# @app.route('/api/etl/process', methods=['POST'])  # Moved to blueprint
def legacy_process_document_endpoint():
    """Process a document through the ETL pipeline."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not file.filename.lower().endswith(('.docx', '.pdf')):
        return jsonify({"error": "File must be DOCX or PDF"}), 400
    
    try:
        # Save the file to the input directory
        from etl import config as etl_config_local  # Local import, avoid re-using global etl_config name
        from etl.main import run_pipeline_for_file  # Local import
        
        # Ensure input directory exists
        os.makedirs(etl_config_local.INPUT_DIR, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(etl_config_local.INPUT_DIR, file.filename)
        file.save(file_path)
        
        # Run the ETL pipeline
        success, message = run_pipeline_for_file(file_path)
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "filename": file.filename
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message,
                "filename": file.filename
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "filename": file.filename
        }), 500

# @app.route('/api/etl/status', methods=['GET'])  # Moved to blueprint
def legacy_etl_status_endpoint():
    """Get the status of the ETL pipeline."""
    try:
        from etl import config as etl_config_local  # Local import
        
        # Check if input and output directories exist
        input_dir_exists = os.path.exists(etl_config_local.INPUT_DIR)
        output_dir_exists = os.path.exists(etl_config_local.OUTPUT_IMAGE_DIR)
        
        # Count files in each directory
        input_files = len(os.listdir(etl_config_local.INPUT_DIR)) if input_dir_exists else 0
        processed_files = len(os.listdir(etl_config_local.CHUNKS_JSON_DIR)) if os.path.exists(etl_config_local.CHUNKS_JSON_DIR) else 0
        
        # Check if FEN converter is enabled and available
        fen_enabled = etl_config_local.FEN_CONVERTER_ENABLED
        fen_available = os.path.exists(etl_config_local.BOARD_TO_FEN_TOOL_PATH)
        
        # Check if Weaviate is enabled and connected
        weaviate_enabled = etl_config_local.WEAVIATE_ENABLED
        weaviate_connected = False
        
        if weaviate_enabled:
            from etl.weaviate_loader import get_weaviate_client  # Local import
            client = get_weaviate_client()
            weaviate_connected = client is not None
        
        return jsonify({
            "status": "operational",
            "input_directory": {
                "exists": input_dir_exists,
                "path": etl_config_local.INPUT_DIR,
                "file_count": input_files
            },
            "processing": {
                "fen_converter_enabled": fen_enabled,
                "fen_converter_available": fen_available,
                "processed_files": processed_files
            },
            "weaviate": {
                "enabled": weaviate_enabled,
                "connected": weaviate_connected,
                "url": etl_config_local.WEAVIATE_URL
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# @app.route('/api/rag/query', methods=['POST'])  # Moved to blueprint
def legacy_rag_query_endpoint():
    """RAG query endpoint using the new orchestrator"""
    data = request.get_json()
    
    if not data or not data.get('query'):
        return jsonify({"error": "Query is required"}), 400
    
    query = data.get('query')
    session_id = data.get('session_id') 
    
    current_board_fen_for_rag = None
    current_pgn_for_rag = None # ADDED: To store PGN

    if session_id and session_id in active_games:
        with session_lock:
            if session_id in active_games and 'board' in active_games[session_id]:
                board = active_games[session_id]['board']
                current_board_fen_for_rag = board.fen()
                try:
                    # Generate PGN from the board state
                    game_for_pgn = chess.pgn.Game()
                    # Build PGN from move stack
                    # The board in active_games should have the full history
                    node = game_for_pgn
                    for move in board.move_stack:
                        node = node.add_main_variation(move) # Use add_main_variation for simplicity
                    
                    pgn_exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
                    current_pgn_for_rag = game_for_pgn.accept(pgn_exporter)
                    if not current_pgn_for_rag and board.move_stack: # Handle empty PGN if moves exist (should not happen)
                        current_pgn_for_rag = "[Could not generate PGN from move stack]"
                    elif not board.move_stack:
                        current_pgn_for_rag = "[No moves played yet]"

                    print(f"DEBUG: [rag_query_endpoint] Fetched FEN for session {session_id}: {current_board_fen_for_rag}")
                    print(f"DEBUG: [rag_query_endpoint] Generated PGN for session {session_id}: {current_pgn_for_rag}")
                except Exception as e:
                    print(f"ERROR: [rag_query_endpoint] Failed to generate PGN for session {session_id}: {e}")
                    current_pgn_for_rag = "[Error generating PGN]"
            else:
                print(f"DEBUG: [rag_query_endpoint] No board found for session {session_id} in active_games.")
    else:
        print(f"DEBUG: [rag_query_endpoint] No session_id provided or session_id {session_id} not in active_games.")

    if not answer_agent_instance:
        print("ERROR: /api/rag/query called but answer_agent_instance is not available globally.")
        return jsonify({"error": "RAG system not initialized. LLM client or AnswerAgent might be missing."}), 503
    
    if not run_pipeline: # Check if orchestrator imported successfully
        print("ERROR: /api/rag/query called but run_pipeline (orchestrator) is not available.")
        return jsonify({"error": "RAG system's orchestrator is not available."}), 503

    try:
        # Call the new orchestrator\'s run_pipeline function
        pipeline_state = run_pipeline(
            initial_query=query,
            router_agent_instance=router_agent_instance,
            retriever_agent_instance=retriever_agent_instance,
            answer_agent_instance=answer_agent_instance,
            current_board_fen=current_board_fen_for_rag,
            session_pgn=current_pgn_for_rag,
            session_id=session_id  # Pass session_id for conversation memory
        )
        
        # Determine the FEN for which to run analysis for the UI
        # Priority: FEN set by router, then current board FEN from pipeline, then initial FEN.
        final_fen_for_ui_analysis = pipeline_state.get("fen_for_analysis", 
                                      pipeline_state.get("current_board_fen", 
                                                         current_board_fen_for_rag))

        analysis_lines_for_ui = []
        if final_fen_for_ui_analysis:
            app.logger.info(f"Running Stockfish analysis for UI for FEN: {final_fen_for_ui_analysis}")
            analysis_lines_for_ui = analyze_fen_with_stockfish(
                fen_string=final_fen_for_ui_analysis, 
                time_limit=None,  # Quick analysis for UI update
                depth_limit=24,
                multipv=3
            )
            if analysis_lines_for_ui is None: # Ensure it's an empty list if analysis fails
                analysis_lines_for_ui = []
                app.logger.warning(f"Stockfish analysis for UI returned None for FEN: {final_fen_for_ui_analysis}")
        else:
            app.logger.warning("No FEN determined for UI Stockfish analysis in RAG query response.")

        # Construct response from the pipeline_state
        if pipeline_state.get("final_answer"):
            response_data = {
                "query": query,
                "answer": pipeline_state["final_answer"],
                "query_type": pipeline_state.get("query_type"),
                "metadata": pipeline_state.get("router_metadata"), 
                "retrieved_chunks_count": len(pipeline_state.get("retrieved_chunks", [])),
                "analysis_lines": analysis_lines_for_ui, # <<< ADDED ANALYSIS LINES
                "fen": final_fen_for_ui_analysis # <<< FEN for which analysis was run (or current FEN if none by router)
            }
            if pipeline_state.get("error_message"): 
                response_data["note"] = pipeline_state["error_message"]
            app.logger.info(f"RAG Query successful. Returning answer and {len(analysis_lines_for_ui)} analysis lines for FEN: {final_fen_for_ui_analysis}")
            return jsonify(response_data), 200
        elif pipeline_state.get("error_message"):
            app.logger.error(f"RAG pipeline error: {pipeline_state['error_message']}")
            # Even on error, provide any analysis that might have been generated if a FEN was available
            return jsonify({
                "error": pipeline_state["error_message"], 
                "query": query,
                "query_type": pipeline_state.get("query_type"),
                "analysis_lines": analysis_lines_for_ui, # Include analysis if available
                "fen": final_fen_for_ui_analysis    # Include FEN if available
            }), 500 
        else:
            app.logger.error("RAG pipeline did not produce an answer or an error.")
            # Fallback, include analysis if available
            return jsonify({
                "error": "RAG pipeline did not produce an answer or an error.", 
                "query": query,
                "analysis_lines": analysis_lines_for_ui, # Include analysis if available
                "fen": final_fen_for_ui_analysis    # Include FEN if available
            }), 500

    except Exception as e:
        app.logger.error(f"Error during RAG pipeline execution: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred in the RAG pipeline: {str(e)}"}), 500

# @app.route('/api/set_fen', methods=['POST'])  # Moved to blueprint
def legacy_set_fen_endpoint():
    """
    Endpoint to set a FEN position in an active session.
    Used by the LangGraph agent to update the chessboard when a FEN is detected.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    fen = data.get('fen')
    source = data.get('source', 'agent')  # Where the FEN came from (agent, rag, etc.)
    explanation = data.get('explanation', '')  # Optional explanation text

    # Validate the required parameters
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if not fen:
        return jsonify({"error": "fen is required"}), 400

    # Validate the FEN format
    try:
        board = chess.Board(fen)
        valid_fen = board.fen()  # Get the normalized FEN
    except ValueError as e:
        return jsonify({"error": f"Invalid FEN string: {str(e)}"}), 400
    
    # Store in active games or update existing session
    if session_id not in active_games:
        active_games[session_id] = {'board': board}
        app.logger.info(f"[update_backend_fen] Created new session {session_id} with FEN: {new_fen}")
    else:
        active_games[session_id]['board'] = board
        app.logger.info(f"[update_backend_fen] Updated board for session {session_id} with FEN: {new_fen}")
    
    # Emit a WebSocket event with the new FEN
    socketio.emit('fen_update', {
        'session_id': session_id,
        'fen': valid_fen,
        'source': source,
        'explanation': explanation
    })
    
    # Return success with normalized FEN and any relevant info
    return jsonify({
        "success": True,
        "fen": valid_fen,
        "source": source,
        "explanation": explanation
    }), 200

# Add WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    session_id = request.sid  # Use SocketIO's session ID
    app.logger.info(f"Client connected: {session_id}")
    with session_lock:
        if session_id not in active_games:
            active_games[session_id] = {"board": chess.Board()} # No per-session engine anymore
            app.logger.info(f"New game initialized for session {session_id}")
    emit('connection_ack', {'message': 'Connected to backend', 'session_id': session_id})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    app.logger.info(f"Client disconnected: {session_id}")
    with session_lock: # Protect access to active_games
        if session_id in active_games:
            # Clean up Stockfish if it was specific to this session
            if active_games[session_id].get('stockfish_process'):
                try:
                    active_games[session_id]['stockfish_process'].quit()
                    app.logger.info(f"Stockfish engine for session {session_id} shut down.")
                except Exception as e:
                    app.logger.error(f"Error quitting Stockfish for session {session_id}: {e}")
            del active_games[session_id]
            app.logger.info(f"Game resources cleaned up for session {session_id}")

@socketio.on('update_backend_fen')
def handle_update_backend_fen(data):
    session_id = data.get('session_id')
    new_fen = data.get('fen')

    if not session_id or not new_fen:
        app.logger.error(f"[update_backend_fen] Invalid data received: session_id={session_id}, fen={new_fen}")
        return

    with session_lock:
        try:
            # Create chess board with the new FEN to validate it
            board = chess.Board(new_fen)
            
            # Store in active games or update existing session
            if session_id not in active_games:
                active_games[session_id] = {'board': board}
                app.logger.info(f"[update_backend_fen] Created new session {session_id} with FEN: {new_fen}")
            else:
                active_games[session_id]['board'] = board
                app.logger.info(f"[update_backend_fen] Updated board for session {session_id} with FEN: {new_fen}")
            
            # IMPORTANT: Also update user_sessions to keep RAG context in sync
            user_sessions[session_id] = user_sessions.get(session_id, {})
            user_sessions[session_id]['current_fen'] = board.fen()
            app.logger.info(f"[update_backend_fen] Synchronized user_sessions FEN for RAG: {board.fen()}")
            
            # Return success confirmation
            emit('fen_sync_success', {
                'session_id': session_id,
                'fen': board.fen(),
                'timestamp': datetime.now().isoformat()
            })
        except ValueError as e:
            app.logger.error(f"[update_backend_fen] Invalid FEN received for session {session_id}: {new_fen}. Error: {e}")
            emit('fen_sync_error', {
                'session_id': session_id,
                'error': f"Invalid FEN format: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            app.logger.error(f"[update_backend_fen] Unexpected error for session {session_id}: {str(e)}")
            emit('fen_sync_error', {
                'session_id': session_id,
                'error': f"Server error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

@socketio.on('new_move_made')
def handle_new_move(data):
    session_id = data.get('session_id')
    move_uci = data.get('move_uci')
    fen_from_frontend = data.get('fen')  # Get current FEN from frontend

    if not session_id or not move_uci:
        app.logger.error(f"[new_move_made] Invalid data: session_id={session_id}, move_uci={move_uci}")
        return

    # Remove 'q' suffix if it exists (promotion to queen)
    if move_uci.endswith('q') and len(move_uci) > 4:
        # Only remove if it's actually a promotion suffix
        move_uci = move_uci[:-1]
        app.logger.info(f"[new_move_made] Removed promotion suffix 'q' from move: {move_uci}")

    with session_lock:
        # Always sync with frontend FEN first if provided
        if fen_from_frontend and session_id in active_games:
            try:
                # Update the board with the latest FEN from frontend
                active_games[session_id]['board'] = chess.Board(fen_from_frontend)
                app.logger.info(f"[new_move_made] Synced backend board with frontend FEN: {fen_from_frontend}")
                
                # Also update user_sessions for RAG context
                user_sessions[session_id] = user_sessions.get(session_id, {})
                user_sessions[session_id]['current_fen'] = fen_from_frontend
                app.logger.info(f"[new_move_made] Synchronized user_sessions FEN for RAG: {fen_from_frontend}")
            except ValueError as e:
                app.logger.error(f"[new_move_made] Invalid FEN from frontend: {fen_from_frontend}. Error: {e}")
                # Continue with current board state as fallback
        
        # If no frontend FEN or FEN sync failed, try applying the move
        if not fen_from_frontend and session_id in active_games:
            try:
                board = active_games[session_id]['board']
                move = chess.Move.from_uci(move_uci)
                
                if move in board.legal_moves:
                    board.push(move)
                    new_fen = board.fen()
                    app.logger.info(f"[new_move_made] Applied move {move_uci}, new FEN: {new_fen}")
                    
                    # Ensure user_sessions is updated with the new FEN after move
                    user_sessions[session_id] = user_sessions.get(session_id, {})
                    user_sessions[session_id]['current_fen'] = new_fen
                    app.logger.info(f"[new_move_made] Updated user_sessions FEN after move: {new_fen}")
                else:
                    app.logger.warning(f"[new_move_made] Illegal move {move_uci} for session {session_id}. Board FEN: {board.fen()}. Legal moves: {list(board.legal_moves)}")
                    # Emit event for illegal move? Could be added here if needed
                    return
            except Exception as e:
                app.logger.error(f"[new_move_made] Error applying move: {e}")
                # Proceed with analysis using the FEN we have (either from frontend or existing board)

@socketio.on('uci_command')
def handle_uci_command(data):
    session_id = data.get('session_id', request.sid)
    command = data.get('command')

    if not command:
        emit('uci_error', {'error': 'Command not provided', 'session_id': session_id})
        return

    # Use globally imported etl_config instead of etl_config_local
    with session_lock:
        if session_id not in active_games or not etl_config.STOCKFISH_PATH:
            emit('uci_error', {'error': 'Game or Stockfish not initialized for session', 'session_id': session_id})
            return
        
        game_data = active_games[session_id]
        if game_data.get("engine") is None:
            try:
                game_data["engine"] = chess.engine.SimpleEngine.popen_uci(etl_config.STOCKFISH_PATH)
                app.logger.info(f"Stockfish engine started for session {session_id}")
            except Exception as e:
                app.logger.error(f"Failed to start Stockfish for session {session_id}: {e}")
                emit('uci_error', {'error': f'Failed to start Stockfish: {e}', 'session_id': session_id})
                return
        
        engine = game_data["engine"]

    try:
        if command.startswith("position fen"):
            parts = command.split(" ", 2)
            if len(parts) > 2:
                fen_string = parts[2]
                with session_lock:
                    try:
                        # Update the board with the given FEN
                        active_games[session_id]["board"].set_fen(fen_string)
                        app.logger.info(f"Board FEN updated for session {session_id}: {fen_string}")
                        # No need to call engine.position() - we'll set position before analysis
                    except ValueError as e:
                        app.logger.error(f"Invalid FEN in UCI command: {e}")
                        emit('uci_error', {'error': f'Invalid FEN: {e}', 'session_id': session_id})
                        return
        elif command.startswith("position startpos"):
            with session_lock:
                active_games[session_id]["board"].reset()
                if "moves" in command: # e.g. "position startpos moves e2e4 e7e5"
                    moves = command.split("moves")[1].strip().split()
                    for move_uci in moves:
                        try:
                            move = chess.Move.from_uci(move_uci)
                            if move in active_games[session_id]["board"].legal_moves:
                                active_games[session_id]["board"].push(move)
                            else:
                                app.logger.warning(f"Illegal move {move_uci} in UCI command")
                        except ValueError:
                            app.logger.warning(f"Invalid UCI move {move_uci} in command")
            app.logger.info(f"Board position updated from startpos for session {session_id}")
        elif command == "ucinewgame":
            engine.ucinewgame()
            with session_lock:
                 active_games[session_id]["board"].reset()
            app.logger.info(f"Engine ucinewgame for session {session_id}")

        elif command.startswith("go"):
            board = active_games[session_id]["board"]
            # Extract analysis parameters
            depth = 20  # Default depth
            if "depth" in command:
                try:
                    depth_parts = command.split("depth")[1].strip().split()
                    if depth_parts:
                        depth = int(depth_parts[0])
                except (ValueError, IndexError):
                    app.logger.warning(f"Invalid depth parameter, using default {depth}")
            
            # Use a fixed time limit for analysis
            time_limit = chess.engine.Limit(depth=depth, time=5.0)
            
            try:
                # Play the position and get analysis
                result = engine.analyse(board, time_limit, multipv=3)
                
                # Format the response
                lines_info = []
                for i, pv_info in enumerate(result):
                    # Handle score differently based on type
                    if 'score' in pv_info:
                        score_obj = pv_info['score']
                        numerical_score = None
                        mate_value = None
                        evaluation_string = "0.00"
                        
                        try:
                            # Check if this is a mate score by examining the Score object's attributes directly
                            # Print score object for debugging
                            app.logger.debug(f"Score object type: {type(score_obj)}, dir: {dir(score_obj)}")
                            
                            # Use direct attribute access instead of method calls when possible
                            if hasattr(score_obj, 'mate'):
                                # Check if mate is a direct attribute or property
                                if callable(getattr(score_obj, 'mate')):
                                    # It's a method
                                    try:
                                        temp_mate = score_obj.mate()
                                        if temp_mate is not None:
                                            mate_value = temp_mate
                                            evaluation_string = f"Mate in {abs(mate_value)}"
                                    except Exception as me:
                                        app.logger.warning(f"Error calling mate() method: {me}")
                                else:
                                    # It's a direct attribute
                                    temp_mate = score_obj.mate
                                    if temp_mate is not None:
                                        mate_value = temp_mate
                                        evaluation_string = f"Mate in {abs(mate_value)}"
                            
                            # If not mate, try to get centipawn score
                            if mate_value is None:
                                # First try the 'cp' attribute (newer versions)
                                if hasattr(score_obj, 'cp'):
                                    if callable(getattr(score_obj, 'cp')):
                                        try:
                                            # It's a method
                                            cp_value = score_obj.cp()
                                            if cp_value is not None:
                                                numerical_score = cp_value / 100.0
                                        except Exception as ce:
                                            app.logger.warning(f"Error calling cp() method: {ce}")
                                    else:
                                        # It's a direct attribute
                                        cp_value = score_obj.cp
                                        if cp_value is not None:
                                            numerical_score = cp_value / 100.0
                                
                                # Then try 'score' attribute (some versions)
                                elif hasattr(score_obj, 'score'):
                                    if callable(getattr(score_obj, 'score')):
                                        try:
                                            # It's a method
                                            s_value = score_obj.score()
                                            if s_value is not None:
                                                numerical_score = s_value / 100.0
                                        except Exception as se:
                                            app.logger.warning(f"Error calling score() method: {se}")
                                    else:
                                        # It's a direct attribute
                                        s_value = score_obj.score
                                        if s_value is not None:
                                            numerical_score = s_value / 100.0
                                
                                # Try 'white' as a last resort
                                elif hasattr(score_obj, 'white'):
                                    if callable(getattr(score_obj, 'white')):
                                        try:
                                            # It's a method
                                            w_value = score_obj.white()
                                            if w_value is not None:
                                                numerical_score = w_value / 100.0
                                        except Exception as we:
                                            app.logger.warning(f"Error calling white() method: {we}")
                                    else:
                                        # It's a direct attribute
                                        w_value = score_obj.white
                                        if w_value is not None:
                                            numerical_score = w_value / 100.0
                                
                                # Extract evaluation from relative if all else fails
                                elif hasattr(score_obj, 'relative'):
                                    rel = score_obj.relative
                                    if hasattr(rel, 'cp'):
                                        cp_val = rel.cp
                                        if cp_val is not None:
                                            numerical_score = cp_val / 100.0
                                    elif isinstance(rel, (int, float)):
                                        numerical_score = rel / 100.0
                                
                                # Last resort - try to get string representation and parse it
                                if numerical_score is None:
                                    try:
                                        score_str = str(score_obj)
                                        if 'cp' in score_str:
                                            match = re.search(r'cp\s+([+-]?\d+)', score_str)
                                            if match:
                                                numerical_score = int(match.group(1)) / 100.0
                                        elif 'mate' in score_str:
                                            match = re.search(r'mate\s+([+-]?\d+)', score_str)
                                            if match:
                                                mate_value = int(match.group(1))
                                                evaluation_string = f"Mate in {abs(mate_value)}"
                                    except Exception as parsing_e:
                                        app.logger.warning(f"Error parsing score string: {parsing_e}")
                                
                                # If we've found a numerical score, format it
                                if numerical_score is not None:
                                    evaluation_string = f"{'+' if numerical_score > 0 else ''}{numerical_score:.2f}"
                                else:
                                    # Default if nothing worked
                                    numerical_score = 0
                                    evaluation_string = "0.00"
                            
                        except Exception as score_e:
                            app.logger.error(f"Error processing score object: {score_e}")
                            numerical_score = 0
                            evaluation_string = "0.00"
                    else:
                        numerical_score = 0
                        evaluation_string = "0.00"
                        mate_value = None
                    
                    pv = pv_info.get("pv", [])
                    san_moves = []
                    
                    # Convert moves to SAN
                    temp_board = board.copy()
                    for move in pv:
                        san = temp_board.san(move)
                        san_moves.append(san)
                        temp_board.push(move)
                    
                    pv_san = " ".join(san_moves)
                    
                    # Format the response to match what's expected by the frontend
                    lines_info.append({
                        "line_number": i+1,
                        "score": numerical_score,  
                        "evaluation_numerical": numerical_score,
                        "evaluation_string": evaluation_string,
                        "mate_in": mate_value,
                        "depth": pv_info.get("depth", 0),
                        "pv_san": pv_san,
                        "bestmove": san_moves[0] if san_moves else ""
                    })
                
                # Send the analysis back to the client
                emit('uci_response', {
                    'analysis_lines': lines_info,
                    'fen': board.fen(),
                    'session_id': session_id
                })
                app.logger.info(f"Engine analysis completed for session {session_id}: {len(lines_info)} lines")
                
            except chess.engine.EngineError as ee:
                app.logger.error(f"Engine analysis error: {ee}")
                emit('uci_error', {'error': f'Engine analysis error: {ee}', 'session_id': session_id})
            
        else: # For other commands like 'isready', 'setoption'
            # For these commands, just send a simple acknowledgment
            # as we're not directly accessing engine.protocol anymore
            emit('uci_response', {'response': f'Command received: {command}', 'session_id': session_id})
            app.logger.info(f"Simple acknowledgment for UCI command '{command}' sent to session {session_id}")

    except ValueError as e: # e.g. illegal move
        app.logger.error(f"UCI command error for session {session_id} on command '{command}': {e}")
        emit('uci_error', {'error': f'Invalid FEN or move in UCI command: {e}', 'session_id': session_id})
    except chess.engine.EngineError as e:
        app.logger.error(f"Stockfish engine error for session {session_id} on command '{command}': {e}")
        emit('uci_error', {'error': f'Stockfish engine error: {e}', 'session_id': session_id})
        # Attempt to restart engine on error
        try:
            if game_data.get("engine"):
                game_data["engine"].quit()
            game_data["engine"] = chess.engine.SimpleEngine.popen_uci(etl_config.STOCKFISH_PATH)
            app.logger.info(f"Stockfish engine restarted for session {session_id} after error.")
        except Exception as restart_e:
            app.logger.error(f"Failed to restart Stockfish for session {session_id}: {restart_e}")
            game_data["engine"] = None # Mark engine as dead
            emit('uci_error', {'error': f'Stockfish engine failed and could not be restarted: {restart_e}', 'session_id': session_id})

    except Exception as e:
        app.logger.error(f"Unexpected UCI processing error for session {session_id} on command '{command}': {e}")
        emit('uci_error', {'error': f'Unexpected error processing UCI command: {e}', 'session_id': session_id})

# --- Graceful Engine Shutdown (Only if integrated engine exists) ---
# Register shutdown handlers for both clean exit and signals

def shutdown_engine_handler():
    """Shutdown Stockfish engine properly"""
    from stockfish_analyzer import quit_stockfish  # Local import
    quit_stockfish()
    print("Stockfish engine shutdown initiated by shutdown handler")

# Register the function to be called on exit
atexit.register(shutdown_engine_handler)

# Register signal handlers - only in main thread
if threading.current_thread() is threading.main_thread():
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda signum, frame: shutdown_engine_handler())
else:
    logger.warning("Not registering signal handlers as we're not in the main thread")

def get_weaviate_client_for_app():
    # Re-using the client logic from an agent to ensure consistency
    # This could be centralized further in the future.
    # For now, we'll use the one from opening_agent, assuming it's general enough.
    try:
        # The opening_agent.get_weaviate_client() handles headers internally if OpenAI key is present
        client = opening_agent.get_weaviate_client()
        if not client:
            app.logger.error("Failed to get Weaviate client via opening_agent.get_weaviate_client()")
            return None
        # Skip gRPC-based health checks since we're using HTTP-only mode
        # if not client.is_live() or not client.is_ready():
        #     app.logger.error(f"Weaviate client is not live or not ready. Live: {client.is_live()}, Ready: {client.is_ready()}")
        #     return None
        
        # Use HTTP-based connection check instead
        if not client.is_connected():
            app.logger.error("Weaviate client is not connected")
            return None
        app.logger.info(f"Successfully connected to Weaviate at {getattr(client, 'connection_params', {}).get('http', {}).get('host', 'N/A')}")
        return client
    except Exception as e:
        app.logger.error(f"Error getting Weaviate client in app: {e}")
        return None

# Helper function for UUID validation (can be placed at module level or within App context)
def is_valid_uuid(uuid_to_test_str):
    """ Check if uuid_to_test_str is a valid UUID (any version). """
    try:
        # Attempt to convert string to UUID object
        uuid_obj = uuid.UUID(uuid_to_test_str)
        # Ensure the string representation matches the original to catch malformed but parsable strings
        return str(uuid_obj) == uuid_to_test_str.lower() # Compare with lowercase original for consistency
    except ValueError:
        return False

@app.route('/api/game/<string:game_uuid>', methods=['GET'])
def get_game_details(game_uuid: str):
    logger.info(f"🔥 FIXED VERSION: Received request for game details: {game_uuid}")

    # Validate UUID format
    if not is_valid_uuid(game_uuid):
        logger.error(f"Invalid UUID format received for game details: {game_uuid}")
        return jsonify({"error": "Invalid Game ID format"}), 400

    try:
        client = opening_agent.get_weaviate_client()
        if not client:
            logger.error("Failed to get Weaviate client in get_game_details")
            return jsonify({"error": "Database connection failed"}), 503

        games_collection_name = getattr(etl_config, 'WEAVIATE_GAMES_CLASS_NAME', "ChessGame")
        
        # Use Weaviate v3 syntax to fetch game by UUID
        properties = [
            "white_player", "black_player", "event", "site", "round", "date_utc", 
            "result", "eco", "opening_name", "ply_count", "final_fen", "mid_game_fen",
            "pgn_moves", "source_file", "white_elo", "black_elo", "event_date",
            "white_title", "black_title", "white_fide_id", "black_fide_id", "all_ply_fens"
        ]
        
        # Build v3 query to get game by UUID
        response = (client.query
                   .get(games_collection_name, properties)
                   .with_where({
                       "path": ["id"],
                       "operator": "Equal",
                       "valueText": game_uuid
                   })
                   .with_additional(["id"])
                   .with_limit(1)
                   .do())
        
        # Process v3 response format
        if (response and response.get("data") and 
            response["data"].get("Get") and 
            response["data"]["Get"].get(games_collection_name) and
            len(response["data"]["Get"][games_collection_name]) > 0):
            
            game_data = response["data"]["Get"][games_collection_name][0]
            
            # Ensure all_ply_fens is present and is a list
            if 'all_ply_fens' not in game_data or not isinstance(game_data.get('all_ply_fens'), list):
                game_data['all_ply_fens'] = []
                logger.warning(f"Game object {game_uuid} is missing 'all_ply_fens' or it's not a list. Defaulting to empty.")
            
            response_data = {
                "uuid": game_uuid,
                "metadata": {
                    k: game_data.get(k) for k in [
                        "white_player", "black_player", "event", "site", 
                        "round", "date_utc", "result", "eco", "opening_name"
                    ]
                },
                "pgn_moves": game_data.get("pgn_moves", ""),
                "all_ply_fens": game_data.get("all_ply_fens", [])
            }
            logger.info(f"Returning data for game {game_uuid}. Ply FENs count: {len(response_data['all_ply_fens'])}")
            return jsonify(response_data), 200
        else:
            logger.warning(f"Game with UUID {game_uuid} not found in Weaviate.")
            return jsonify({"error": "Game not found"}), 404

    except Exception as e:
        logger.error(f"Error fetching game details for UUID {game_uuid}: {e}")
        return jsonify({"error": f"An error occurred while fetching game details: {str(e)}"}), 500

if __name__ == '__main__':
    try:
        # Set use_reloader to False if it causes issues with Stockfish or background threads
        socketio.run(app, debug=True, port=5001, host='0.0.0.0', use_reloader=False, allow_unsafe_werkzeug=True) 
    finally:
        # This ensures Stockfish is shut down when the app server stops,
        # but only if not using reloader, as reloader creates a child process.
        # If reloader is True, manage Stockfish within each process lifecycle or avoid global engine.
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
             quit_stockfish() # Corrected from shut_down_stockfish_engine() 