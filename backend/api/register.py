import logging
from flask import Flask

# Import all API blueprints using local imports  
from api import chess_api_blueprint

# DISABLED: Chat blueprint is disabled due to LLM integration requirements
# If you have working LLM integration, uncomment the following:
try:
    from api import chat_api_blueprint
    chat_enabled = True
    logger = logging.getLogger(__name__)
    logger.info("Chat API enabled - LLM integration detected")
except ImportError:
    chat_enabled = False
    chat_api_blueprint = None

from api import etl_api_blueprint

# DISABLED: Voice blueprint is disabled due to missing dependencies
# If you have voice processing dependencies, uncomment the following:
try:
    from api import voice_api_blueprint
    voice_enabled = True
    logger = logging.getLogger(__name__)
    logger.info("Voice API enabled - voice processing dependencies detected")
except ImportError:
    voice_enabled = False
    voice_api_blueprint = None

# ADD: Learning Mode API
try:
    from api.learning import learning_api
    learning_enabled = True
    logger = logging.getLogger(__name__)
    logger.info("Learning API enabled - lesson repository available")
except ImportError as e:
    learning_enabled = False
    learning_api = None
    logger = logging.getLogger(__name__)
    logger.warning(f"Learning API disabled - missing dependencies: {e}")

from api import health_api_blueprint
from api.folder_monitor import folder_monitor_bp

logger = logging.getLogger(__name__)

def register_blueprints(app: Flask) -> None:
    """
    Register all API blueprints with the Flask application.
    
    Args:
        app: The Flask application instance
    """
    logger.info("Registering API blueprints...")
    
    # Register each blueprint
    app.register_blueprint(chess_api_blueprint)
    if chat_enabled:
        app.register_blueprint(chat_api_blueprint)
    app.register_blueprint(etl_api_blueprint)
    if voice_enabled:
        app.register_blueprint(voice_api_blueprint)
    if learning_enabled:
        app.register_blueprint(learning_api)
    app.register_blueprint(health_api_blueprint)
    app.register_blueprint(folder_monitor_bp, url_prefix='/api/folder')
    
    # Note: Russian education API temporarily disabled due to FastAPI/Flask integration issues
    # The RAG functionality works through direct database access
    logger.info("Russian Education API disabled - using direct database access")
    
    logger.info(f"Registered API routes:")
    
    # Print all registered routes for debugging
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.endpoint:40s} {','.join(rule.methods):20s} {rule}")
    
    for route in sorted(routes):
        logger.info(f"  {route}") 