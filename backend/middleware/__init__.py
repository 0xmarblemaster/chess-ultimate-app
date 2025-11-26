"""
Middleware package for Flask application.

Available middleware:
- performance_monitor: Track API request/response times and metrics
"""

from .performance_monitor import setup_performance_monitoring, get_monitor

__all__ = ['setup_performance_monitoring', 'get_monitor']
