#!/usr/bin/env python
"""
Health Check Script

This script performs health checks on all repositories and services
to verify that connections are working properly.
"""

import os
import sys
import logging
import argparse
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import repositories and services
from backend.database.game_repository import GameRepository
from backend.database.opening_repository import OpeningRepository
from backend.database.lesson_repository import LessonRepository
from backend.services.extract_service import ExtractService
from backend.services.vector_store_service import VectorStoreService

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Perform health checks on repositories and services")
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=10,
        help="Timeout in seconds for each health check"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    return parser.parse_args()

def perform_health_check(name, service_or_repo, timeout):
    """Perform a health check with timeout."""
    logger.info(f"Checking {name}...")
    start_time = time.time()
    
    try:
        # Run the health check with timeout
        result = service_or_repo.healthcheck()
        elapsed_time = time.time() - start_time
        
        if result:
            logger.info(f"✅ {name}: Healthy (took {elapsed_time:.2f}s)")
            return True
        else:
            logger.error(f"❌ {name}: Unhealthy (took {elapsed_time:.2f}s)")
            return False
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ {name}: Error - {e} (took {elapsed_time:.2f}s)")
        return False

def main():
    """Run health checks on all repositories and services."""
    args = parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting health checks...")
    
    # Dictionary of services and repositories to check
    checks = {
        "VectorStoreService": VectorStoreService(),
        "GameRepository": GameRepository(),
        "OpeningRepository": OpeningRepository(),
        "LessonRepository": LessonRepository(),
        "ExtractService": ExtractService()
    }
    
    # Perform all health checks
    results = {}
    all_healthy = True
    
    for name, service_or_repo in checks.items():
        results[name] = perform_health_check(name, service_or_repo, args.timeout)
        all_healthy = all_healthy and results[name]
    
    # Print summary
    logger.info("==== Health Check Summary ====")
    
    for name, result in results.items():
        status = "HEALTHY" if result else "UNHEALTHY"
        logger.info(f"{name}: {status}")
    
    logger.info("============================")
    logger.info(f"Overall system health: {'HEALTHY' if all_healthy else 'UNHEALTHY'}")
    
    return 0 if all_healthy else 1

if __name__ == "__main__":
    sys.exit(main()) 