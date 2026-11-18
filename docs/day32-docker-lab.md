
# Day 32 — Docker Image & Container Lab

## Project
OpsPulse — Production Application Monitoring & Incident Tracker

## Date
18 November 2026

## Objective
Containerize the existing Day 31 Flask application.

## Application
- Flask application: OpsPulse v2
- Docker image: opspulse:day32
- Container: opspulse-day32
- Container port: 8080
- Host port: 127.0.0.1:8081
- Application server: Gunicorn 23.0.0
- Runtime user: opspulse (UID 10001)

## Build and Run

```bash
cd ~/winter-arc-integration-project/app
docker build -t opspulse:day32 .
docker run -d --name opspulse-day32 -p 127.0.0.1:8081:8080 opspulse:day32
```

## Verification Commands

```bash
docker ps
docker port opspulse-day32
curl -i http://localhost:8081/health
curl -s http://localhost:8081/
docker logs --tail 20 opspulse-day32
docker exec opspulse-day32 id
docker image history opspulse:day32
docker inspect --format '{{json .State.Health}}' opspulse-day32
```

## Verified Results
- Image built successfully
- Container started successfully
- HTTP 200 from /health
- OpsPulse v2 returned from /
- Non-root UID 10001 confirmed
- Docker HEALTHCHECK reported healthy
- FailingStreak = 0

## Failure and Recovery Drill

Scenario: Container intentionally stopped.

Commands:
```bash
docker stop opspulse-day32
docker ps -a
curl -i http://localhost:8081/health
docker logs opspulse-day32
docker start opspulse-day32
```

Recovery verified:
- Container running
- Docker health status healthy
- HTTP 200 from /health

Note: The initial stopped-state output was not captured in the final evidence.

## Lessons
1. Images package the application and dependencies.
2. Containers are instances of images.
3. Host and container ports can differ.
4. Non-root execution reduces privileges.
5. HEALTHCHECK tests application responsiveness.
6. Docker does not automatically restart a container solely because it is unhealthy.

## Next Assignment
Day 33 — Docker Compose with OpsPulse and PostgreSQL.
