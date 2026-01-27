#!/usr/bin/env python3
"""Debug Flask app to diagnose socket binding issues"""

import sys
import traceback
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health():
    print("Health endpoint called", file=sys.stderr)
    return jsonify({'status': 'ok', 'message': 'Backend is running'})

if __name__ == '__main__':
    try:
        print("=" * 60)
        print("Starting Flask app on 0.0.0.0:5000...")
        print("=" * 60)
        sys.stdout.flush()
        sys.stderr.flush()
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except OSError as e:
        print(f"Socket error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
