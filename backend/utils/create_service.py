#!/usr/bin/env python3
"""
Service Generator Utility

This script generates a new service file with the proper structure
based on templates. It helps maintain consistency across service
implementations.
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Template for a basic service class
SERVICE_TEMPLATE = '''"""
{service_name} Service

{service_description}
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class {class_name}:
    """
    {class_description}
    """
    
    def __init__(self{init_params}):
        """
        Initialize the {service_name} service.
        
        Args:{init_param_docs}
        """
        self.logger = logger
        {init_body}
    
    def healthcheck(self) -> bool:
        """
        Check if the service is operational.
        
        Returns:
            True if the service is healthy, False otherwise.
        """
        try:
            # TODO: Implement service-specific health check
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
{methods}
    
# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # Create service instance
        service = {class_name}({example_args})
        logger.info(f"{service_name} service initialized")
        
        # Test health check
        is_healthy = service.healthcheck()
        logger.info(f"Health check {'passed' if is_healthy else 'failed'}")
        
        # Example service usage
        {example_usage}
        
    except Exception as e:
        logger.error(f"Error in {service_name} service example: {e}", exc_info=True)
'''METHOD_TEMPLATE = '''
    def {method_name}(self{method_params}) -> {return_type}:
        """
        {method_description}
        
        Args:{method_param_docs}
        
        Returns:
            {return_description}
            
        Raises:
            {raises}
        """
        try:
            # TODO: Implement method
            {method_body}
        except Exception as e:
            self.logger.error(f"Error in {method_name}: {e}")
            raise
'''

def generate_service_file(args):
    """Generate a new service file based on the provided arguments."""
    service_name = args.name
    service_path = args.path or os.path.join('backend', 'services', f"{service_name.lower()}_service.py")
    class_name = args.class_name or ''.join(word.capitalize() for word in service_name.split('_')) + 'Service'
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(service_path), exist_ok=True)
    
    # Check if file already exists
    if os.path.exists(service_path) and not args.force:
        print(f"Error: File {service_path} already exists. Use --force to overwrite.")
        return False    
    # Build the service description
    service_description = args.description or f"Service for {service_name.replace('_', ' ')} functionality."
    class_description = args.class_description or f"Service for {service_name.replace('_', ' ')} operations."
    
    # Build init parameters
    init_params = ""
    init_param_docs = ""
    init_body = "# TODO: Initialize service"
    if args.params:
        init_params = ", " + ", ".join(args.params)
        init_param_docs = "\n            " + "\n            ".join(f"{param.split('=')[0]}: Description for {param.split('=')[0]}." for param in args.params)
        init_body = "\n        ".join(f"self.{param.split('=')[0]} = {param.split('=')[0]}" for param in args.params)
    
    # Build example arguments
    example_args = ""
    if args.params:
        example_args = ", ".join(param.split('=')[1] if '=' in param else param.split(':')[0] for param in args.params)
    
    # Build methods
    methods = ""
    if args.methods:
        for method in args.methods:
            method_name = method
            method_params = ""
            method_param_docs = ""
            return_type = "Any"
            return_description = "Result of the operation."
            raises = "Exception: If an error occurs."
            method_body = "pass  # TODO: Implement method"
            
            methods += METHOD_TEMPLATE.format(
                method_name=method_name,
                method_params=method_params,
                method_param_docs=method_param_docs,
                return_type=return_type,
                method_description=f"Perform {method_name} operation.",
                return_description=return_description,
                raises=raises,
                method_body=method_body
            )    
    # Build example usage
    example_usage = "# TODO: Add example usage"
    if args.methods and len(args.methods) > 0:
        example_usage = f"result = service.{args.methods[0]}()\n        logger.info(f\"Example method result: {{result}}\")"
    
    # Fill the template
    service_content = SERVICE_TEMPLATE.format(
        service_name=service_name.replace('_', ' ').title(),
        service_description=service_description,
        class_name=class_name,
        class_description=class_description,
        init_params=init_params,
        init_param_docs=init_param_docs,
        init_body=init_body,
        methods=methods,
        example_args=example_args,
        example_usage=example_usage
    )
    
    # Write the service file
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    print(f"Created service file: {service_path}")
    return True

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate a new service file")
    parser.add_argument('name', help="Name of the service (e.g., database, cache)")
    parser.add_argument('--path', help="Path to write the service file (default: backend/services/<name>_service.py)")
    parser.add_argument('--class-name', help="Name of the service class (default: derived from service name)")
    parser.add_argument('--description', help="Description of the service")
    parser.add_argument('--class-description', help="Description of the service class")
    parser.add_argument('--params', nargs='+', help="Init parameters (e.g., 'url=None' 'timeout=30')")
    parser.add_argument('--methods', nargs='+', help="Methods to include in the service")
    parser.add_argument('--force', action='store_true', help="Overwrite existing file")
    
    args = parser.parse_args()
    
    try:
        success = generate_service_file(args)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error generating service file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()