import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, request

app = Flask(__name__)


def get_db_connection():
    """Connect to PostgreSQL using Docker Compose variables."""
    return psycopg.connect(
        host=os.environ.get("DATABASE_HOST", "db"),
        port=int(os.environ.get("DATABASE_PORT", "5432")),
        dbname=os.environ.get("DATABASE_NAME", "opspulse"),
        user=os.environ.get("DATABASE_USER", "opspulse"),
        password=os.environ["DATABASE_PASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    )


def initialize_database():
    """Create the incidents table if it does not exist."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


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


@app.route("/incidents", methods=["POST"])
def create_incident():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    title = data.get("title")
    severity = data.get("severity", "MEDIUM")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "A non-empty title is required"}), 400

    if not isinstance(severity, str) or severity.upper() not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        return jsonify({"error": "Invalid severity"}), 400

    initialize_database()

    with get_db_connection() as conn:
        incident = conn.execute(
            """
            INSERT INTO incidents (title, severity)
            VALUES (%s, %s)
            RETURNING id, title, severity, status, created_at
            """,
            (title.strip(), severity.upper())
        ).fetchone()

    return jsonify(incident), 201


@app.route("/incidents", methods=["GET"])
def list_incidents():
    initialize_database()

    with get_db_connection() as conn:
        incidents = conn.execute(
            """
            SELECT id, title, severity, status, created_at
            FROM incidents
            ORDER BY id
            """
        ).fetchall()

    return jsonify(incidents)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
