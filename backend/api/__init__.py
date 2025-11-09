from .chess import chess_api_blueprint
from .chat import chat_api_blueprint  # Re-enabled with conversation memory
from .etl import etl_api_blueprint
from .voice import voice_api_blueprint
from .health import health_api_blueprint

__all__ = [
    'chess_api_blueprint',
    'chat_api_blueprint',  # Re-enabled with conversation memory
    'etl_api_blueprint',
    'voice_api_blueprint',
    'health_api_blueprint'
]

# This file makes it easy to import all blueprints at once:
# from api import chess_api_blueprint, chat_api_blueprint, etl_api_blueprint, voice_api_blueprint 