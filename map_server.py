from flask import Flask, jsonify, send_from_directory
import os
import json

app = Flask(__name__)

@app.route('/drones')
def drones():
    try:
        with open('drone_status.json', 'r') as f:
            data = json.load(f)
    except Exception:
        data = {}
    return jsonify(data)

@app.route('/')
def serve_map():
    return send_from_directory('.', 'live_map.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
