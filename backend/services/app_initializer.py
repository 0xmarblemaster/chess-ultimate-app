"""
Application Initializer Service

This service coordinates the startup of all application components,
ensuring they are initialized in the correct order with proper dependency management.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Set, Tuple

# Import central configuration
import backend.config as app_config
from backend.utils.logging import setup_logging

# Import services
# from backend.services.stockfish_engine import StockfishEngine  # Commented out - module doesn't exist
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class ApplicationInitializer:
    """
    Coordinates initialization of all application components.
    
    This class ensures that services are started in the correct order,
    with proper dependency management. It also provides health checks
    and status information for all initialized components.
    """
    
    def __init__(self):
        """Initialize the application initializer."""
        self.services = {}
        self.service_status = {}
        self.initialized = False
        self.config = app_config.get_config()
    
    def setup_logging(self, level: Optional[str] = None, log_file: Optional[str] = None):
        """
        Set up logging for the application.
        
        Args:
            level: Optional override for the log level.
            log_file: Optional log file to write logs to.
        """
        try:
            # Default to configured log level if not specified
            if level is None:
                level = self.config.get('LOG_LEVEL', 'INFO')
            
            # Set up log file path if provided
            log_dir = None
            if log_file:
                log_dir = os.path.join(self.config.get('BACKEND_DIR', '.'), 'logs')
            
            # Configure logging
            logger = setup_logging(
                name='chess_companion',
                level=level,
                log_file=log_file,
                log_dir=log_dir
            )
            
            # Set initialized logger for this module
            globals()['logger'] = logger
            
            logger.info(f"Logging initialized at level {level}")
            if log_file:
                logger.info(f"Logs will be written to {os.path.join(log_dir or '.', log_file)}")
                
            return True
            
        except Exception as e:
            print(f"Error setting up logging: {e}")
            return False
    
    def initialize_services(self) -> bool:
        """
        Initialize all application services in the correct order.
        
        Returns:
            True if all services were initialized successfully, False otherwise.
        """
        if self.initialized:
            logger.warning("Services already initialized. Call reset() before reinitializing.")
            return True
        
        logger.info("Initializing application services...")
        
        try:
            # Initialize Stockfish engine service if enabled
            if app_config.is_feature_enabled("STOCKFISH_ENABLED"):
                logger.info("Stockfish engine service is enabled but module not available - skipping...")
                self.service_status['stockfish'] = {
                    'status': 'disabled',
                    'message': 'Stockfish engine module not available'
                }
            else:
                logger.info("Stockfish engine service disabled in configuration")
                self.service_status['stockfish'] = {
                    'status': 'disabled',
                    'message': 'Stockfish engine service disabled in configuration'
                }
            
            # Initialize LLM service
            logger.info("Initializing LLM service...")
            try:
                # Determine API key and model to use - prioritize ANTHROPIC_API_KEY first
                api_key = (self.config.get('ANTHROPIC_API_KEY') or 
                          self.config.get('OPENAI_API_KEY') or 
                          self.config.get('DEEPSEEK_API_KEY'))
                
                base_url = None
                if not self.config.get('ANTHROPIC_API_KEY') and not self.config.get('OPENAI_API_KEY') and self.config.get('DEEPSEEK_API_KEY'):
                    base_url = self.config.get('DEEPSEEK_BASE_URL')
                
                if api_key:
                    llm_service = LLMService(
                        api_key=api_key,
                        model_name=self.config.get('DEFAULT_LLM_MODEL'),
                        base_url=base_url,
                        max_tokens=self.config.get('DEFAULT_LLM_MAX_TOKENS'),
                        temperature=self.config.get('DEFAULT_LLM_TEMPERATURE')
                    )
                    
                    # Check if the LLM service is healthy
                    is_healthy, message = llm_service.healthcheck()
                    if is_healthy:
                        self.services['llm'] = llm_service
                        self.service_status['llm'] = {
                            'status': 'healthy',
                            'message': 'LLM service initialized successfully',
                            'provider': llm_service.provider,
                            'model': llm_service.model_name
                        }
                        logger.info(f"LLM service initialized successfully with provider {llm_service.provider}")
                    else:
                        self.service_status['llm'] = {
                            'status': 'unhealthy',
                            'message': message,
                            'provider': llm_service.provider if hasattr(llm_service, 'provider') else 'unknown',
                            'model': llm_service.model_name if hasattr(llm_service, 'model_name') else 'unknown'
                        }
                        logger.warning(f"LLM service healthcheck failed: {message}")
                else:
                    self.service_status['llm'] = {
                        'status': 'disabled',
                        'message': 'No API key found for LLM service'
                    }
                    logger.warning("LLM service disabled - no API key found")
                    
            except Exception as e:
                self.service_status['llm'] = {
                    'status': 'error',
                    'message': f'Error initializing LLM service: {str(e)}'
                }
                logger.error(f"Error initializing LLM service: {e}", exc_info=True)
            
            # Add initialization for other services here as needed
            # - ChessBoard service
            # - Whisper STT service
            # - ElevenLabs TTS service
            # - Weaviate client
            # - Retriever/Router/Answer agents
            
            self.initialized = True
            logger.info("Application services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing application services: {e}", exc_info=True)
            return False
    
    def get_service(self, service_name: str) -> Any:
        """
        Get a service instance by name.
        
        Args:
            service_name: The name of the service to retrieve.
            
        Returns:
            The service instance, or None if the service is not found or not initialized.
        """
        return self.services.get(service_name)
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all services.
        
        Returns:
            A dictionary of service statuses.
        """
        return self.service_status
    
    def healthcheck(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform a health check on all initialized services.
        
        Returns:
            A tuple containing:
            - Boolean indicating if all services are healthy
            - Dictionary with detailed health information for each service
        """
        if not self.initialized:
            return False, {'status': 'error', 'message': 'Application not initialized'}
        
        all_healthy = True
        health_info = {
            'status': 'healthy',
            'services': {}
        }
        
        # Check Stockfish service
        if 'stockfish' in self.services:
            try:
                stockfish_healthy = self.services['stockfish'].healthcheck()
                health_info['services']['stockfish'] = {
                    'status': 'healthy' if stockfish_healthy else 'unhealthy',
                    'message': 'Healthcheck passed' if stockfish_healthy else 'Healthcheck failed'
                }
                if not stockfish_healthy:
                    all_healthy = False
            except Exception as e:
                all_healthy = False
                health_info['services']['stockfish'] = {
                    'status': 'error',
                    'message': f'Error during healthcheck: {str(e)}'
                }
        elif 'stockfish' in self.service_status:
            # Service known but not initialized
            health_info['services']['stockfish'] = self.service_status['stockfish']
            if self.service_status['stockfish'].get('status') != 'disabled':
                all_healthy = False
        
        # Check LLM service
        if 'llm' in self.services:
            try:
                llm_healthy, llm_message = self.services['llm'].healthcheck()
                health_info['services']['llm'] = {
                    'status': 'healthy' if llm_healthy else 'unhealthy',
                    'message': llm_message,
                    'provider': self.services['llm'].provider,
                    'model': self.services['llm'].model_name
                }
                if not llm_healthy:
                    all_healthy = False
            except Exception as e:
                all_healthy = False
                health_info['services']['llm'] = {
                    'status': 'error',
                    'message': f'Error during healthcheck: {str(e)}'
                }
        elif 'llm' in self.service_status:
            # Service known but not initialized
            health_info['services']['llm'] = self.service_status['llm']
            if self.service_status['llm'].get('status') != 'disabled':
                all_healthy = False
        
        # Add healthchecks for other services here as needed
        
        if not all_healthy:
            health_info['status'] = 'unhealthy'
        
        return all_healthy, health_info
    
    def shutdown(self) -> None:
        """Shutdown all services gracefully."""
        logger.info("Shutting down application services...")
        
        # Shutdown Stockfish engine
        if 'stockfish' in self.services:
            logger.info("Shutting down Stockfish engine service...")
            try:
                self.services['stockfish'].quit()
                logger.info("Stockfish engine service shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down Stockfish engine: {e}")
        
        # Add shutdown for other services here as needed
        
        self.initialized = False
        logger.info("Application services shut down successfully")
    
    def reset(self) -> None:
        """Reset the initializer to allow reinitialization."""
        self.shutdown()
        self.services = {}
        self.service_status = {}
        self.initialized = False


# Singleton instance for application-wide use
app_initializer = ApplicationInitializer()

# Example usage
if __name__ == "__main__":
    # Set up logging
    setup_logging(level="INFO")
    
    try:
        # Initialize services
        success = app_initializer.initialize_services()
        logger.info(f"Service initialization {'succeeded' if success else 'failed'}")
        
        # Get service status
        status = app_initializer.get_service_status()
        logger.info(f"Service status: {status}")
        
        # Perform healthcheck
        healthy, health_info = app_initializer.healthcheck()
        logger.info(f"Application healthcheck: {'Healthy' if healthy else 'Unhealthy'}")
        logger.info(f"Health details: {health_info}")
        
        # Use a service
        stockfish_service = app_initializer.get_service('stockfish')
        if stockfish_service:
            result = stockfish_service.analyze_fen(
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            )
            logger.info(f"Stockfish analysis: {result[:2] if result else 'Failed'}")
        
        # Shutdown
        app_initializer.shutdown()
        
    except Exception as e:
        logger.exception(f"Error in application initialization example: {e}") 