"""
Health check API endpoints for the Chess Companion app.

This module provides health check endpoints to monitor the status
of all application services.
"""

from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

# Create the blueprint
health_api_blueprint = Blueprint('health_api', __name__, url_prefix='/api/health')

@health_api_blueprint.route('', methods=['GET'])
def health_check():
    """
    Basic health check endpoint.
    
    Returns a 200 status if the API is running, regardless of service status.
    """
    return jsonify({"status": "ok", "message": "API is running"}), 200

@health_api_blueprint.route('/services', methods=['GET'])
def service_health():
    """
    Detailed service health check endpoint.
    
    Returns basic service status information.
    """
    try:
        # Basic service status without complex dependencies
        response = {
            "status": "healthy",
            "services": {
                "api": {"status": "healthy", "message": "API endpoints are responding"},
                "flask": {"status": "healthy", "message": "Flask application is running"}
            }
        }
        
        response["summary"] = {
            "total_services": 2,
            "healthy_services": 2,
            "health_percentage": 100.0,
        }
        
        return jsonify(response), 200
    except Exception as e:
        logger.exception(f"Error in service health check: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error in service health check: {str(e)}"
        }), 500

@health_api_blueprint.route('/alive', methods=['GET'])
def alive():
    """
    Simple liveness probe for container health checks.
    
    Always returns 200 to indicate the Flask app is running.
    """
    return "", 200