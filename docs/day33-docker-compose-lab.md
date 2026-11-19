# Day 33/90 — OpsPulse Docker Compose & PostgreSQL Lab

Date: 19 November 2026
Project: OpsPulse — Production Application Monitoring & Incident Tracker
Repository: https://github.com/manasabitra1989/winter-arc-integration-project

## Objective

Extend the existing OpsPulse Flask application using Docker Compose,
PostgreSQL, container networking, persistent volumes, and incident APIs.

No separate project was created.

## Architecture

Client (curl)
    |
    | localhost:8082
    v
Flask + Gunicorn (app:8080)
    |
    | Internal Docker network
    | Hostname: db
    | Port: 5432
    v
PostgreSQL 17 (db)
    |
    v
Docker named volume: opspulse-day33_postgres-data

## Existing Resources Preserved

- Day 31 host application: port 8080
- Day 32 Docker container: port mapping 8081:8080
- Day 33 Compose application: 127.0.0.1:8082
- Original application routes: GET / and GET /health
- Original GitHub repository and revision tracker

## Step 1 — Pre-flight Checks

docker compose version
docker ps -a
docker volume ls
sudo ss -lntp
git status --short

Verified Docker Compose v5.6.1.
The Day 32 container was stopped with exit code 255.
Docker reported OOMKilled=false; the exact termination cause
was not established.

## Step 2 — Compose Configuration

File: day33-compose/compose.yaml

Services:
- app: Flask/Gunicorn built from the existing app/Dockerfile
- db: postgres:17-alpine

Configuration:
- Project: opspulse-day33
- Host API port: 127.0.0.1:8082
- Internal app port: 8080
- Internal PostgreSQL port: 5432
- Service discovery: hostname db
- DB health check: pg_isready
- Dependency: app waits for healthy db at initial startup
- Persistent named volume: postgres-data

Credentials:
- Database password stored in day33-compose/.env
- .env must remain ignored by Git
- Never commit the database password

## Step 3 — Build and Start Containers

docker compose -f day33-compose/compose.yaml config --quiet
docker compose -f day33-compose/compose.yaml up -d --build
docker compose -f day33-compose/compose.yaml ps

Verified:
- PostgreSQL image downloaded
- Flask application image built
- Compose network created
- PostgreSQL named volume created
- Both containers eventually reported healthy

## Step 4 — Networking Verification

Docker DNS:
docker compose -f day33-compose/compose.yaml exec app python -c "import socket; print(socket.gethostbyname('db'))"

Observed database IP: 172.19.0.2

TCP test:
docker compose -f day33-compose/compose.yaml exec app python -c "import socket; s=socket.create_connection(('db',5432),timeout=5); print('TCP connection successful'); s.close()"

SQL verification:
docker compose -f day33-compose/compose.yaml exec db psql -U opspulse -d opspulse -c "SELECT current_database(), current_user, version();"

Verified PostgreSQL 17.12, database opspulse, and user opspulse.

Learning:
Use Compose service names instead of hardcoded container IPs.
DNS/TCP success does not by itself prove application authentication.

## Step 5 — Flask Database Integration

Added psycopg[binary] to app/requirements.txt.

Modified app/app.py to:
- Read database connection parameters from environment variables
- Connect to PostgreSQL using psycopg
- Create incidents table if necessary
- Preserve GET / and GET /health
- Provide POST /incidents
- Provide GET /incidents
- Use parameterized SQL

Example incident:
Title: Production application unavailable
Severity: HIGH
Status: OPEN

## Step 6 — Build and Verify Application

docker compose -f day33-compose/compose.yaml up -d --build --no-deps app
docker compose -f day33-compose/compose.yaml ps
curl -i http://127.0.0.1:8082/health

Verified GET /health returned HTTP 200.

## Step 7 — Incident API Verification

Create incident:
curl -i -X POST http://127.0.0.1:8082/incidents -H "Content-Type: application/json" -d '{"title":"Production application unavailable","severity":"HIGH"}'

Observed HTTP 201 CREATED and incident ID 1.

Retrieve incidents:
curl -s http://127.0.0.1:8082/incidents

Query database:
docker compose -f day33-compose/compose.yaml exec db psql -U opspulse -d opspulse -c "SELECT id, title, severity, status FROM incidents;"

Verified incident ID 1 exists in PostgreSQL.

## Step 8 — Database Persistence Test

Recreate the database container:
docker compose -f day33-compose/compose.yaml up -d --no-deps --force-recreate db

Verify:
docker compose -f day33-compose/compose.yaml ps
docker compose -f day33-compose/compose.yaml exec db psql -U opspulse -d opspulse -c "SELECT id, title, severity, status FROM incidents;"
curl -i http://127.0.0.1:8082/incidents

Result:
Incident ID 1 survived container recreation.
The incident API returned HTTP 200.

Explanation:
The named volume stores PostgreSQL data separately from the
container writable filesystem.

A persistent volume is not a substitute for backups.

## Step 9 — Controlled Failure and Recovery

Simulated outage:
docker compose -f day33-compose/compose.yaml stop db

Observed:
- PostgreSQL container Exited (0)
- Flask container remained healthy
- GET /incidents returned HTTP 500

Investigation:
docker compose -f day33-compose/compose.yaml ps -a
docker compose -f day33-compose/compose.yaml logs --tail=40 app

Actual error:
psycopg.OperationalError: failed to resolve host 'db':
[Errno -5] No address associated with hostname

Root cause:
PostgreSQL was intentionally stopped. The app could no longer
resolve the database service hostname.

Recovery:
docker compose -f day33-compose/compose.yaml start db
docker compose -f day33-compose/compose.yaml exec db pg_isready -U opspulse -d opspulse
docker compose -f day33-compose/compose.yaml exec db psql -U opspulse -d opspulse -c "SELECT id, title, severity, status FROM incidents;"
curl -i --max-time 10 http://127.0.0.1:8082/incidents

Verified:
- PostgreSQL restarted
- Incident ID 1 remained stored
- GET /incidents returned HTTP 200
- Both containers healthy in final Compose status check

## Key Production Lessons

1. Containers should be replaceable; database data must persist.
2. Compose service names provide DNS-based communication.
3. depends_on with service_healthy controls startup order,
   but does not continuously guarantee dependency availability.
4. Flask /health can be healthy while database operations fail.
5. Logs distinguish DNS failures from application and SQL errors.
6. Recovery must verify both database data and end-user API behavior.
7. Never run docker compose down -v during a data-preservation test.

## Improvements for a Later Lab

- Add database-aware GET /ready
- Return controlled HTTP 503 for database outages
- Add integration tests and schema migrations
- Store credentials using a more appropriate secret mechanism
- Add backup and restore testing

## Interview Questions

Q1. Why use Docker Compose?
A: To define and manage connected application services together.

Q2. How does Flask find PostgreSQL?
A: Through the Compose service hostname db.

Q3. Why use a named volume?
A: To preserve database files across container recreation.

Q4. What is the difference between EXPOSE and ports?
A: EXPOSE documents the intended container port; ports publishes
a container port on the host.

Q5. Why did the incident API fail while Flask was healthy?
A: The health endpoint did not check PostgreSQL connectivity.

Q6. How did we troubleshoot the database outage?
A: Inspect container states, examine Flask logs, identify the
DNS resolution error, restart PostgreSQL, and verify API and SQL.

Q7. What is the difference between healthy and ready?
A: Liveness means the process is functioning; readiness means
the application can serve its required workload.

## Next Assignment

Day 34: Kubernetes integration using the existing OpsPulse
application, with particular attention to Services, probes,
storage, and troubleshooting.
