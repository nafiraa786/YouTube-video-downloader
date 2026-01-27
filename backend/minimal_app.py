#!/usr/bin/env python3
"""Minimal Flask app to test basic functionality"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Backend is running'})

@app.route('/api/video-info', methods=['POST'])
def video_info():
    return jsonify({'success': True, 'message': 'This would fetch video info'})

if __name__ == '__main__':
    print("Starting minimal Flask app on 0.0.0.0:5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
