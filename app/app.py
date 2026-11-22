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




@app.route("/ready")
def readiness():
    """Check whether the application can query PostgreSQL."""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "ready", "database": "connected"}), 200
    except psycopg.OperationalError:
        app.logger.warning("Readiness check failed: PostgreSQL unavailable")
        return jsonify({"status": "not_ready", "database": "unavailable"}), 503



@app.route("/dashboard")
def dashboard():
    from flask import render_template
    return render_template("dashboard.html")

@app.route("/incidents/<int:incident_id>", methods=["PATCH"])
def update_incident(incident_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    status = data.get("status")

    if status not in ("OPEN", "RESOLVED"):
        return jsonify({"error": "Invalid status"}), 400

    with get_db_connection() as conn:
        incident = conn.execute(
            """
            UPDATE incidents
            SET status = %s
            WHERE id = %s
            RETURNING id, title, severity, status, created_at
            """,
            (status, incident_id)
        ).fetchone()

    if incident is None:
        return jsonify({"error": "Incident not found"}), 404

    return jsonify(incident), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
