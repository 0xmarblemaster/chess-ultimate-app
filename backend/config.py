"""
Configuration Module for Chess Companion

This module provides centralized configuration management for the application.
Configuration values are loaded from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Union

# Load environment variables from .env file if present
load_dotenv()

# ==== Logging Configuration ====
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# ==== LLM Configuration ====
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# ==== Stockfish Configuration ====
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish")
STOCKFISH_DEPTH = int(os.environ.get("STOCKFISH_DEPTH", "16"))
STOCKFISH_TIMEOUT = int(os.environ.get("STOCKFISH_TIMEOUT", "30"))

# ==== FEN Converter Configuration ====
FEN_MODEL_PATH = os.environ.get("FEN_MODEL_PATH", None)
PYTHON_EXECUTABLE = os.environ.get("PYTHON_EXECUTABLE", "python")

# ==== Database Configuration ====
WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY", "")
WEAVIATE_GRPC_URL = os.environ.get("WEAVIATE_GRPC_URL", "localhost:50051")

# ==== API Configuration ====
API_PORT = int(os.environ.get("API_PORT", "5000"))
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() in ("true", "1", "yes", "y", "t")

# ==== Text-to-Speech / Speech-to-Text Configuration ====
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# ==== Chess Engine Parameters ====
DEFAULT_THINKING_TIME = int(os.environ.get("DEFAULT_THINKING_TIME", "5"))  # seconds
MAX_THINKING_TIME = int(os.environ.get("MAX_THINKING_TIME", "30"))  # seconds
SKILL_LEVEL = int(os.environ.get("SKILL_LEVEL", "20"))  # 0-20

# ==== ETL Configuration ====
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))

# Configuration validation
def validate_config() -> Dict[str, str]:
    """
    Validate the configuration and return any warnings or errors.
    
    Returns:
        Dict[str, str]: Dictionary of config keys with warning/error messages
    """
    issues = {}
    
    # Check required API keys
    if not OPENAI_API_KEY and LLM_PROVIDER == "openai":
        issues["OPENAI_API_KEY"] = "Missing OpenAI API key while OpenAI is the selected provider"
    
    if not DEEPSEEK_API_KEY and LLM_PROVIDER == "deepseek":
        issues["DEEPSEEK_API_KEY"] = "Missing DeepSeek API key while DeepSeek is the selected provider"
    
    # Check for Stockfish path
    if STOCKFISH_PATH == "stockfish":
        import shutil
        if not shutil.which("stockfish"):
            issues["STOCKFISH_PATH"] = "Default 'stockfish' not found in PATH. Set STOCKFISH_PATH."
    
    return issues

# Example usage
if __name__ == "__main__":
    import json
    print("Chess Companion Configuration:")
    print(json.dumps({k: v for k, v in globals().items() 
                   if k.isupper() and not k.startswith('_')}, indent=2))
    
    issues = validate_config()
    if issues:
        print("\nConfiguration Warnings:")
        for key, message in issues.items():
            print(f"- {key}: {message}")
    else:
        print("\nConfiguration valid. No issues detected.")