import logging
from typing import Dict, Any, Optional
from ..weaviate_loader import get_weaviate_client

logger = logging.getLogger(__name__)

def get_weaviate_client():
    """
    Get a Weaviate client using the weaviate_loader function.
    This is a wrapper to provide the same interface as expected by the backend.
    """
    from ..weaviate_loader import get_weaviate_client as _get_weaviate_client
    return _get_weaviate_client()

def find_opening_by_fen(fen: str) -> Dict[str, Any]:
    """
    Simplified mock function that pretends to look up an opening by FEN
    
    Parameters:
    -----------
    fen : str
        The FEN string to look up
        
    Returns:
    --------
    Dict
        A dictionary with opening information (or error message)
    """
    logger.info(f"Mock find_opening_by_fen called for FEN: {fen}")
    
    return {
        "message": "Opening database is not available in this version.",
        "type": "system_message"
    } 