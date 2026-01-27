#!/usr/bin/env python3
"""
WSGI server wrapper for the Flask application
Uses Python's wsgiref which works reliably on Windows
"""

import sys
import os
import logging
from wsgiref.simple_server import make_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the Flask app
from app import app

def run_server():
    """Run the WSGI server"""
    host = '0.0.0.0'
    port = 8001
    
    logger.info(f"Starting server on {host}:{port}...")
    logger.info("Press CTRL+C to stop the server")
    
    # Create the WSGI server
    httpd = make_server(host, port, app)
    
    logger.info(f"Server is running on http://{host}:{port}")
    logger.info("Waiting for requests...")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        httpd.server_close()
        logger.info("Server closed")

if __name__ == '__main__':
    try:
        run_server()
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)
