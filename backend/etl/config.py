from dotenv import load_dotenv
load_dotenv()  # By default, loads .env from the current working directory or parent directories

import os
import sys
import logging

# Add board-to-fen to Python path to ensure the module can be imported
board_to_fen_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "board-to-fen")
if board_to_fen_path not in sys.path:
    sys.path.append(board_to_fen_path)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend directory
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")  # General output directory
OUTPUT_IMAGE_DIR = os.path.join(BASE_DIR, "output_images")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed_data")  # Alias for processed data
EXTRACTED_JSON_DIR = os.path.join(BASE_DIR, "processed_data")
FEN_CONVERTED_JSON_DIR = os.path.join(BASE_DIR, "processed_data")
CHUNKS_JSON_DIR = os.path.join(BASE_DIR, "processed_data")

# Ensure output directories exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(EXTRACTED_JSON_DIR, exist_ok=True)
os.makedirs(FEN_CONVERTED_JSON_DIR, exist_ok=True)
os.makedirs(CHUNKS_JSON_DIR, exist_ok=True)

# Weaviate Configuration
WEAVIATE_URL = "http://localhost:8080"
WEAVIATE_CLASS_NAME = "ChessLessonChunk"  # Fixed: Use ChessLessonChunk for lesson data
WEAVIATE_OPENING_CLASS_NAME = "ChessGame"  # Using ChessGame for openings too (has opening data)
WEAVIATE_GAMES_CLASS_NAME = "ChessGame"
WEAVIATE_ENABLED = True

# Directory for PGN game files
PGN_DATA_DIR = os.path.join(BASE_DIR, "data", "twic_pgn")
os.makedirs(PGN_DATA_DIR, exist_ok=True)

# Embedding Model & LLM Configuration (as per PRD)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# Paths to tools
BOARD_TO_FEN_TOOL_PATH = os.path.join(board_to_fen_path, "board_to_fen_cli.py")
# Use the same Python executable as the frontend for board-to-fen
BOARD_TO_FEN_PYTHON_EXECUTABLE = "/home/marblemaster/Desktop/Cursor/board-to-fen/.venv/bin/python"

# Enable/disable FEN conversion
FEN_CONVERTER_ENABLED = True

# FEN conversion fallback options
FEN_FALLBACK_ENABLED = True  # Whether to use fallback when board-to-fen fails
FEN_FALLBACK_AFTER_ERRORS = 3  # Number of CUDA errors before switching to fallback for all images
# You can manually disable the neural network and just use fallback for all images
FEN_FORCE_FALLBACK = False  # Set to True to force using fallback for all images (skips neural network)

# Check existence for early warning
if not os.path.isfile(BOARD_TO_FEN_TOOL_PATH):
    print(f"Config Warning: FEN conversion script not found at {BOARD_TO_FEN_TOOL_PATH}")
    FEN_CONVERTER_ENABLED = False
    FEN_FORCE_FALLBACK = True  # Force fallback if tool is missing
elif not os.access(BOARD_TO_FEN_TOOL_PATH, os.X_OK):
    print(f"Config Info: FEN conversion script at {BOARD_TO_FEN_TOOL_PATH} may not be directly executable. Will attempt to run with Python interpreter.")

# LangGraph Agent Configuration
ANSWER_AGENT_MODEL_NAME = "gpt-4o"
ANSWER_AGENT_MAX_TOKENS = 4000
ROUTER_AGENT_MODEL_NAME = "gpt-4o"  # Or a faster model like "gpt-3.5-turbo"
ROUTER_AGENT_MAX_TOKENS = 500     # Routers typically need shorter responses
RETRIEVER_TOP_K = 25  # Updated from 3 to 25 to reflect expanded database (53,884 games)
print(f"🔧 CONFIG DEBUG: RETRIEVER_TOP_K is set to {RETRIEVER_TOP_K}")  # Debug print
STOCKFISH_PATH = os.getenv("STOCKFISH_ENGINE_PATH", "/usr/games/stockfish") # Path to Stockfish executable
OPENING_BOOK_PATH = os.getenv("OPENING_BOOK_FILE_PATH", os.path.join(BASE_DIR, "data", "openings", "default_book.bin")) # Placeholder path

# General settings
DEFAULT_LANGUAGE = "ru"  # Default language for processing if not detected

# Logging configuration
LOG_LEVEL = "INFO"

# Logging
logger = logging.getLogger(__name__)

# Helper functions for LLM configuration
def get_model_name():
    """Get the model name for LLM calls"""
    return ANSWER_AGENT_MODEL_NAME

def get_max_tokens():
    """Get the max tokens for LLM calls"""
    return ANSWER_AGENT_MAX_TOKENS

def get_temperature():
    """Get the temperature for LLM calls"""
    return 0.7  # Default temperature

print(f"ETL Config loaded. Input dir: {INPUT_DIR}, Weaviate URL: {WEAVIATE_URL}")
if OPENAI_API_KEY:
    print("OpenAI API Key is set.")
else:
    print("Warning: OPENAI_API_KEY is not set. This might be required for embedding or agent functionality.") 