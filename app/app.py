from flask import Flask, jsonify
from datetime import datetime, timezone

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "application": "OpsPulse",
        "version": "v2",
        "message": "Welcome to OpsPulse Version 2",
        "status": "running"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "application": "OpsPulse",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
