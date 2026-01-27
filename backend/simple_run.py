#!/usr/bin/env python3
"""Run the Flask app using a simple WSGI server"""

import sys
import os

# Set up Python path
sys.path.insert(0, os.getcwd())

from app import app

if __name__ == '__main__':
    print("Starting Flask development server on 127.0.0.1:5000...")
    print("Press CTRL+C to stop the server")
    sys.stdout.flush()
    
    # Run with threaded=True to handle concurrent requests
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False,
        use_debugger=False,
        threaded=True
    )
