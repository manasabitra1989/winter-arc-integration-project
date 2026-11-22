# Day 36 — OpsPulse Incident Management Dashboard

## 1. Objective

Build a working browser dashboard on top of the existing
OpsPulse Flask API and PostgreSQL database.

This is a continuation of the Day 30–35 integration project,
not a new application.

## 2. Technology Stack

- Python 3.13 and Flask 3.1.3
- HTML, CSS and JavaScript
- PostgreSQL 17
- Docker and Docker Compose
- Gunicorn
- Git and GitHub
- PuTTY SSH local port forwarding

## 3. Architecture

Windows Chrome Browser
        |
        | localhost:8082/dashboard
        v
PuTTY SSH Tunnel
        |
        v
Debian2 Linux Host
        |
        | 127.0.0.1:8082
        v
Flask + Gunicorn Docker Container
        |
        | PostgreSQL connection
        v
PostgreSQL Docker Container
        |
        v
Persistent Docker Volume

This is a local deployment, not an AWS deployment.

## 4. Existing Environment

Project location:

    ~/winter-arc-integration-project

Python environment activation:

    cd ~/winter-arc-integration-project
    source app/.venv/bin/activate

Verification:

    which python
    python --version
    python -m pip show Flask

Existing Compose directory:

    day33-compose/

Application host port: 8082
Application container port: 8080
PostgreSQL container port: 5432

## 5. Container Recovery

Initial containers were stopped.

Commands:

    docker ps -a

    cd day33-compose
    docker compose up -d
    docker compose ps

Verified:
- Flask container healthy
- PostgreSQL container healthy

Important: Do not run docker compose down -v.
That could remove the named database volume.

## 6. Readiness Endpoint Troubleshooting

Problem:

    GET /ready -> HTTP 404

The source file already contained /ready, but the running
Docker image was older.

Verification:

    grep -n -A 10 '@app.route("/ready")' ../app/app.py

Fix:

    docker compose up -d --build --no-deps app

Result:

    GET /ready -> HTTP 200
    database: connected

Lesson:
Changing source code does not automatically update an
existing Docker image.

## 7. Dashboard Implementation

Created:

    app/templates/dashboard.html

Added Flask route:

    @app.route("/dashboard")
    def dashboard():
        from flask import render_template
        return render_template("dashboard.html")

The HTML template includes:
- Incident statistics cards
- Create Incident form
- Incident records table
- Resolve and Reopen actions
- JavaScript API calls

Dashboard statistics are calculated from GET /incidents.

## 8. Docker TemplateNotFound Troubleshooting

Problem:

    GET /dashboard -> HTTP 500

Logs:

    docker compose logs --tail=50 app

Root cause:

    jinja2.exceptions.TemplateNotFound: dashboard.html

The Dockerfile copied only app.py.

Container verification:

    docker compose exec app ls -lh /app/templates/

Initially, the directory was missing.

Fix added to app/Dockerfile:

    COPY templates/ ./templates/

Rebuild:

    docker compose up -d --build --no-deps app

Verification:

    docker compose exec app ls -lh /app/templates/
    curl -I http://127.0.0.1:8082/dashboard

Result:

    HTTP/1.1 200 OK

Lesson:
A healthy container does not guarantee every route works.
Application templates must be packaged in the Docker image.

## 9. API Endpoints

GET /health
    Checks Flask application availability.

GET /ready
    Checks database connectivity.

GET /incidents
    Retrieves incident records.

POST /incidents
    Creates an incident.

PATCH /incidents/<id>
    Changes an incident status to OPEN or RESOLVED.

GET /dashboard
    Serves the browser dashboard.

## 10. Incident Resolution API

Added a PATCH endpoint to app/app.py.

Example request:

    curl -i -X PATCH \
      http://127.0.0.1:8082/incidents/3 \
      -H "Content-Type: application/json" \
      -d '{"status":"RESOLVED"}'

The Flask API executes a parameterized PostgreSQL UPDATE
statement and returns the updated incident.

Invalid status -> HTTP 400.
Missing incident -> HTTP 404.

## 11. Browser Access

Application is bound to localhost on Debian2.

PuTTY tunnel:

    Direction: Local
    Source port: 8082
    Destination: 127.0.0.1:8082

Browser URL:

    http://127.0.0.1:8082/dashboard

The SSH tunnel allows browser access without exposing
the application port publicly.

## 12. End-to-End Testing

Initial incident records:
- ID 1: Production application unavailable
- ID 2: Production server disk usage above 90 percent

Created through browser:
- ID 3: OpsPulse dashboard end-to-end test
- Severity: HIGH
- Initial status: OPEN

Observed counters after creation:

    Total: 3
    Open: 3
    Resolved: 0
    Critical: 1

Tested Resolve through the browser.

Observed:

    Total: 3
    Open: 1
    Resolved: 2
    Critical: 1

Tested Reopen through the browser.

Final verified state:

    Total: 3
    Open: 2
    Resolved: 1
    Critical: 1

Final incident statuses:
- ID 1: OPEN
- ID 2: OPEN
- ID 3: RESOLVED

API verification:

    curl -sS http://127.0.0.1:8082/incidents

Database records survived application container rebuilds.

## 13. Useful Verification Commands

    docker compose ps

    docker compose logs --tail=50 app

    curl -i http://127.0.0.1:8082/health

    curl -i http://127.0.0.1:8082/ready

    curl -I http://127.0.0.1:8082/dashboard

    curl -sS http://127.0.0.1:8082/incidents

    python -m py_compile ../app/app.py

## 14. Production Troubleshooting Challenge

Scenario:
The Flask container reports healthy, but /dashboard
returns HTTP 500.

Investigation:
1. Check the application logs.
2. Identify the Python exception.
3. Check whether dashboard.html exists inside Docker.
4. Inspect Dockerfile COPY instructions.
5. Correct the packaging issue.
6. Rebuild only the Flask application.
7. Verify HTTP 200 and existing incident data.

Key lesson:
Health checks must cover the correct failure conditions.
A successful /health response does not validate every route.

## 15. Interview Preparation

Q1. Why was /ready returning HTTP 404?
A: The running image did not contain the latest Flask route.

Q2. Why was /dashboard returning HTTP 500?
A: Flask could not find dashboard.html inside the image.

Q3. Why did we rebuild only the app service?
A: To deploy new application code without unnecessarily
recreating the existing PostgreSQL service.

Q4. What is the difference between POST and PATCH?
A: POST creates a new incident; PATCH updates an existing one.

Q5. What does the SSH tunnel provide?
A: Encrypted access from the Windows browser to a service
bound to localhost on Debian2.

Q6. Why did incident records survive the app rebuild?
A: They were stored in PostgreSQL, separately from the
recreated Flask container, with persistent database storage.

## 16. Remaining Integration Milestones

- Improve incident filtering and visualizations
- Complete and verify GitHub Actions CI/CD
- Automate deployment
- Add Prometheus metrics
- Add Grafana dashboards and alerting
- Deploy the enhanced app to Kubernetes
- Perform final end-to-end recovery demonstrations

Day 36 delivers the first working incident management
dashboard. It does not complete the full DevOps integration.
