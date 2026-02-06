#!/usr/bin/env python3
"""Simple server runner that starts Waitress with the Flask app"""

import sys
import logging
import time

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

logger.info("Importing Flask app...")
from app import app
import os
logger.info("Flask app imported successfully")

logger.info("Importing Waitress...")
from waitress import serve
logger.info("Waitress imported successfully")

host = os.environ.get('HOST', '127.0.0.1')
try:
    port = int(os.environ.get('PORT', '8001'))
except ValueError:
    port = 8001

logger.info(f"Starting Waitress server on {host}:{port}...")
sys.stdout.flush()
sys.stderr.flush()

logger.info("About to call serve()...")
sys.stdout.flush()

try:
    serve(
        app,
        host=host,
        port=port,
        threads=10,
        _quiet=False,
        channel_timeout=600
    )
except KeyboardInterrupt:
    logger.info("Server interrupted by user")
except Exception as e:
    logger.error(f"Exception in serve: {type(e).__name__}: {e}", exc_info=True)
finally:
    logger.info("Exiting serve()")
    sys.stdout.flush()
    sys.stderr.flush()
