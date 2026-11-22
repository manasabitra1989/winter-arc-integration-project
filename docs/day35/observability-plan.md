# Day 35 — OpsPulse AWS Observability Plan

## Purpose

Design monitoring, logging, and incident response
for the proposed OpsPulse AWS architecture.

This is a DESIGN ONLY document.

No CloudWatch dashboard, alarm, EC2, ALB, or RDS
resource has been created for this exercise.

## 1. Monitoring signals and thresholds

All thresholds below are initial illustrative values.
They must be tuned using real workload baselines.

| Signal | Source | Proposed trigger | First response |
|---|---|---|---|
| Unhealthy application targets | CloudWatch ALB HealthyHostCount | Healthy target count below 2 for 2 minutes | Inspect target health and EC2 instances |
| ALB 5xx errors | CloudWatch HTTPCode_ELB_5XX_Count | More than 5 errors in 5 minutes | Inspect ALB and target connectivity |
| Flask application errors | Application logs and custom metrics | Error rate greater than 2% for 5 minutes | Inspect application logs and dependencies |
| API latency | ALB TargetResponseTime | p95 greater than 1 second for 5 minutes | Check CPU, database, and request traces |
| EC2 CPU utilization | CloudWatch CPUUtilization | Above 80% for 10 minutes | Check workload and scaling activity |
| EC2 memory usage | CloudWatch Agent custom memory metric | Above 85% for 10 minutes | Investigate memory pressure |
| Database availability | RDS status/events and app readiness checks | RDS failure event or readiness errors | Review RDS events and connectivity |
| PostgreSQL connections | RDS DatabaseConnections | Above 80% of configured connection capacity | Inspect connection pooling and leaks |
| Deployment failure | CI/CD pipeline and deployment events | Failed deployment or failed health verification | Investigate rollout and consider rollback |

## 2. Application logging

OpsPulse should log:

- Request timestamp
- HTTP method and path
- HTTP status code
- Request duration
- Incident ID when appropriate
- Application version
- Correlation/request ID
- Relevant error details

Do not log:

- AWS access keys
- Database passwords
- Authentication tokens
- Sensitive user data
- Full Secrets Manager payloads

## 3. Suggested CloudWatch log groups

Proposed log groups:

    /opspulse/production/application
    /opspulse/production/system
    /opspulse/production/deployment

These are names for the design only.

Suggested initial retention:

    14 days for verbose application logs
    30 days for system and deployment logs

Actual retention should follow security, compliance,
investigation, and cost requirements.

## 4. Metrics vs logs vs alarms

Metrics:

Numerical measurements such as CPU usage and latency.

Logs:

Detailed records explaining failures and events.

Alarms:

Notifications or actions triggered when a metric
crosses a defined threshold.

Example:

An ALB 5xx alarm fires.

The engineer checks target health, application logs,
database health, and recent deployment changes.

## 5. Database monitoring

Monitor:

- RDS availability and failover events
- DatabaseConnections
- CPUUtilization
- FreeableMemory
- FreeStorageSpace
- ReadLatency and WriteLatency
- Application database connection errors

Important:

A healthy EC2 instance does not guarantee that
the PostgreSQL database is accessible.

OpsPulse uses:

    /health — application-process check
    /ready  — database-aware readiness check

## 6. Incident response workflow

1. Receive a CloudWatch alarm.
2. Identify the affected AWS component.
3. Check recent deployments and changes.
4. Review logs, metrics, and events.
5. Identify the root cause.
6. Restore service safely.
7. Verify OpsPulse incident APIs.
8. Document the incident and preventive actions.

## 7. Alert routing

Proposed alert destinations:

- Approved operations notification channel
- On-call incident management system
- Escalation contact for critical production failures

Use appropriate alarm severity and deduplication.

Do not send passwords or sensitive diagnostic
information in alert notifications.

## 8. Cost considerations

Potential CloudWatch charges include:

- Custom metrics
- Log ingestion and storage
- Log queries
- Dashboards
- Some alarm configurations

Check current AWS pricing before enabling
production-scale monitoring.

## 9. Lab completion

The monitoring strategy is documented.

No live CloudWatch configuration was created
or verified during Day 35.
