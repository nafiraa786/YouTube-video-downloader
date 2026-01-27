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
logger.info("Flask app imported successfully")

logger.info("Importing Waitress...")
from waitress import serve
logger.info("Waitress imported successfully")

logger.info("Starting Waitress server on 127.0.0.1:5000...")
sys.stdout.flush()
sys.stderr.flush()

logger.info("About to call serve()...")
sys.stdout.flush()

try:
    serve(
        app, 
        host='127.0.0.1', 
        port=5000, 
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
