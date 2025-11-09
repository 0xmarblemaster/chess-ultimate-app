"""
Logging utilities for the Chess Companion application.

This module provides standard logging setup for the application with consistent
formatting and behavior across different components.
"""

import logging
import os
import sys
from typing import Optional, Dict, Any, Union

# Import central configuration
from backend.config import LOG_LEVEL

# Check if rich is available for fancy console logging
try:
    from rich.logging import RichHandler
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

def setup_logging(
    name: Optional[str] = None,
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    use_rich: Optional[bool] = None,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging with standard configuration.
    
    Args:
        name: The logger name. If None, the root logger will be configured.
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to the LOG_LEVEL from config.
        format_string: Custom format string for log messages.
        use_rich: Whether to use Rich for fancy console logging.
                  Defaults to True if available and not in a non-TTY environment.
        log_file: Optional log file to write logs to.
        log_dir: Optional directory for log files. Used only if log_file is provided.
                If None, logs will be saved in the current directory.
                
    Returns:
        The configured logger instance.
    """
    # Default to configured log level if not specified
    if level is None:
        level = LOG_LEVEL
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Default format string
    if format_string is None:
        format_string = '%(asctime)s %(levelname)s %(name)s %(module)s: %(message)s'
    
    # Default for rich if not specified
    if use_rich is None:
        use_rich = RICH_AVAILABLE and sys.stdout.isatty()
    
    # Configure root logger as base
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure console handler
    if use_rich and RICH_AVAILABLE:
        console = Console()
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            console=console,
            show_time=False,  # Rich adds its own time
            show_path=False
        )
        # Simpler format for Rich since it adds its own formatting
        formatter = logging.Formatter('%(message)s')
    else:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(format_string)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure file handler if requested
    if log_file:
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, log_file)
        else:
            log_file_path = log_file
            
        file_handler = logging.FileHandler(log_file_path)
        file_formatter = logging.Formatter(format_string)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Get the requested logger (or root if name is None)
    logger = logging.getLogger(name) if name else root_logger
    
    # Log initial configuration
    logger.debug(f"Logging configured. Level: {level}, Rich: {use_rich and RICH_AVAILABLE}")
    if log_file:
        logger.debug(f"Logging to file: {log_file_path}")
    
    return logger


# Example usage
if __name__ == "__main__":
    # Set up the root logger
    logger = setup_logging(level="DEBUG", use_rich=True)
    
    # Log messages at different levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Create a child logger
    child_logger = logging.getLogger("chess_companion.service")
    child_logger.info("This is a message from a child logger")
    
    # Show exception handling
    try:
        1/0
    except Exception as e:
        logger.exception("An exception occurred:")