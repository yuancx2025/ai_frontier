"""
Lambda entry point for container images.
Routes to the appropriate handler based on LAMBDA_HANDLER environment variable.
"""

import os
import sys

# Get handler name from environment variable
handler_name = os.environ.get('LAMBDA_HANDLER', 'lambda_handlers.scrape_handler.lambda_handler')

# Parse handler path (e.g., "lambda_handlers.scrape_handler.lambda_handler")
parts = handler_name.split('.')
if len(parts) < 2:
    raise ValueError(f"Invalid handler format: {handler_name}")

module_path = '.'.join(parts[:-1])
function_name = parts[-1]

# Import the handler module
try:
    module = __import__(module_path, fromlist=[function_name])
    handler = getattr(module, function_name)
except (ImportError, AttributeError) as e:
    raise ImportError(f"Could not import handler {handler_name}: {e}")

# Lambda runtime interface expects this function
def lambda_handler(event, context):
    """Main Lambda handler that routes to the appropriate handler function."""
    return handler(event, context)

