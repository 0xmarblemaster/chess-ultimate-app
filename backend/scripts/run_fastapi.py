#!/usr/bin/env python
"""
Run FastAPI Server

This script runs the FastAPI server for the Chess Companion application.
It provides a more controlled way to start the server than running the module directly.
"""

import os
import sys
import logging
import argparse
import uvicorn

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import configuration
from backend import config

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the FastAPI server")
    parser.add_argument(
        "--host", 
        type=str, 
        default=os.getenv("API_HOST", "0.0.0.0"),
        help="Host to run the server on (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=os.getenv("API_PORT", 8000),
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1,
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        default=os.getenv("LOG_LEVEL", "info"),
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)"
    )
    return parser.parse_args()

def main():
    """Run the FastAPI server."""
    args = parse_args()
    
    logger.info(f"Starting FastAPI server on {args.host}:{args.port}")
    logger.info(f"Log level: {args.log_level.upper()}")
    
    # Run the FastAPI app using uvicorn
    uvicorn.run(
        "backend.fastapi_app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level=args.log_level.lower()
    )

if __name__ == "__main__":
    main() 