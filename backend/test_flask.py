#!/usr/bin/env python3
"""Simple test Flask app to verify Flask can bind to port 5000"""

from flask import Flask

app = Flask(__name__)

@app.route('/test')
def test():
    return {'status': 'ok'}

if __name__ == '__main__':
    print("Starting test Flask app on 0.0.0.0:5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
