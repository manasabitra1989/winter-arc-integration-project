# OpsPulse — DevOps Revision Tracker

## Day 30: Initial Skills Assessment

Status:
- Confident
- Need Practice
- Need Help

## Linux
| Skill | Status |
|---|---|
| Users, groups and permissions | Not assessed |
| Processes and services | Practiced — Need Practice |
| Networking and ports | Practiced — Need Practice |
| Logs and troubleshooting | Practiced — Need Practice |
| Shell scripting | Practiced — Need Practice |

## Docker
| Skill | Status |
|---|---|
| Dockerfile and images | Not assessed |
| Container lifecycle | Not assessed |
| Networking and port mapping | Not assessed |
| Volumes and persistence | Not assessed |
| Docker Compose | Not assessed |
| Container security | Not assessed |

## Kubernetes
| Skill | Status |
|---|---|
| Pods and Deployments | Not assessed |
| Services and DNS | Not assessed |
| ConfigMaps and Secrets | Not assessed |
| Health probes | Not assessed |
| Storage and StatefulSets | Not assessed |
| HPA and scaling | Not assessed |
| Rollouts and rollback | Not assessed |
| RBAC | Not assessed |
| Troubleshooting | Not assessed |

## AWS
| Skill | Status |
|---|---|
| IAM and least privilege | Not assessed |
| VPC, subnets and routing | Not assessed |
| EC2 and Security Groups | Not assessed |
| ALB and target groups | Not assessed |
| RDS connectivity | Not assessed |
| EKS and Auto Scaling | Not assessed |
| CloudWatch monitoring | Not assessed |
| Cost management | Not assessed |

## Three Priority Revision Areas

1. Shell scripting — Need Practice
   - Write application health-check scripts.
   - Automate process, port and log checks.

2. Kubernetes Services and networking — Need Practice
   - Understand ClusterIP, Service DNS and Pod communication.
   - Troubleshoot Service selectors and connectivity.

3. AWS ALB and RDS connectivity — Need Practice
   - Trace traffic through public and private subnets.
   - Understand ALB, security groups and database access.

## Weekly Progress

| Day | Topic | Status |
|---|---|---|
| 30 | Planning and Git | Completed |
| 31 | Linux and networking | Completed lab — Need Practice |
| 32 | Docker | Completed — commit b49a4d9 pushed |
| 33 | Docker Compose | Completed lab — Git commit pending |
| 34 | Kubernetes | Pending |
| 35 | AWS design | Pending |
| 36 | Final integration | Pending |

## Reflection

Strengths: Linux monitoring, systemd, cron, troubleshooting, deployment and rollback.

Areas needing revision: Bash/Python fluency, Kubernetes networking and AWS connectivity.

## Day 31 Final Verification — 17 November 2026

### Verified
- Flask OpsPulse v2: HEALTHY, HTTP 200
- systemd: active
- Port 8080: Python process listening
- Deployment script: Bash syntax valid
- Release: matches running app.py
- Broken-release simulation: rollback successful
- Health-check script: successful
- Server monitoring: CPU 5%, RAM 51%, Disk 1%
- Cron: health checks every minute
- Logrotate: working; archived log verified
- Git SSH: configured
- Git main: synchronized with origin/main

### Pending
- GitHub Actions CI verified: PASSED (commit 2189323)
- Decide whether to commit or ignore screenshots/
- Review cron and systemd before Docker port mapping

### Next Assignment
Day 32: Containerize existing OpsPulse with Docker.

### Important
Reuse the existing Flask application.
Do not create a separate project.


## Day 33 Final Verification — 19 November 2026

### Verified
- Docker Compose v5.6.1
- Flask and PostgreSQL containers healthy
- Docker DNS and TCP connectivity to db:5432 successful
- PostgreSQL SQL queries successful
- GET /health: HTTP 200
- POST /incidents: HTTP 201, incident ID 1
- GET /incidents: HTTP 200
- Persistent data retained after database container recreation
- Controlled database outage reproduced HTTP 500
- Logs identified PostgreSQL hostname resolution failure
- PostgreSQL restarted successfully
- Incident ID 1 recovered; application returned HTTP 200

### Key Learning
The Flask liveness endpoint remained healthy while database-dependent
operations failed. A separate database-aware readiness check would
improve production reliability.

### Next Assignment
Day 34: Deploy the existing OpsPulse application to Kubernetes.


## Day 34 — Kubernetes Integration

**Status:** Completed — final verification passed

**Implemented:**
- Local kind cluster running Kubernetes v1.34.11
- PostgreSQL StatefulSet, headless Service, and 1Gi PVC
- Flask Deployment and ClusterIP Service
- ConfigMap and Secret integration
- Incident API verified against PostgreSQL
- Flask Pod replacement and automatic recovery
- PostgreSQL Pod replacement with data persistence
- Database-aware `/ready` endpoint
- Rolling update to Deployment Revision 3
- Liveness and readiness probes

**Troubleshooting:**
- Resolved cgroup v1 compatibility issue using a compatible kind node image
- Resolved localhost:8083 connection refusal by restarting port forwarding
- Investigated readiness probe timeouts during a database outage

**Final verified state:**
- Flask and PostgreSQL Pods: 1/1 Ready
- `/health`: HTTP 200
- `/ready`: HTTP 200
- Incident ID 1 preserved
- PVC: Bound, 1Gi

**Not conclusively verified:**
- EndpointSlice transitioning to ready=false during the database outage

**Documentation:** `docs/day34-kubernetes-lab.md`

**Next:** Day 35 — AWS Architecture and Security revision
