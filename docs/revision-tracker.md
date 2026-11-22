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
| 33 | Docker Compose | Completed — commit d80871d pushed |
| 34 | Kubernetes | Completed — commit 0e4084b pushed |
| 35 | AWS design | Completed — commit 7b39a0c pushed |
| 36 | Incident dashboard and management | Implemented and browser-tested — Git commit pending |

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

## Day 35 — AWS Architecture and Security Design

**Status:** Documentation completed and pushed to GitHub.

### Completed
- Reused existing AWS default VPC in ap-south-1.
- Created four private application/database subnets in two AZs.
- Created and associated one private route table.
- Created three least-privilege network Security Groups.
- Reviewed IAM managed policies, inline policies and groups.
- Designed an ALB + EC2 Auto Scaling + RDS architecture.
- Documented IAM roles and deployment security.
- Documented resilience, health checks and failover.
- Designed CloudWatch observability and incident response.
- Compared EC2 Auto Scaling and EKS cost drivers.
- Verified the Day 29 manual RDS snapshot is absent.

### Not deployed
- Application Load Balancer
- EC2 Auto Scaling Group
- Amazon RDS PostgreSQL
- Amazon EKS
- NAT Gateway

### Lessons learned
- Default VPC resources can be reused for a design lab.
- Private subnet design requires routing and IP checks.
- Security Groups are stateful.
- IAM read access does not imply delete permission.
- Inline policy size limits can block additional policies.
- Manual RDS snapshots require explicit cleanup review.

### Documentation
See docs/day35/README.md and supporting design files.

## Days 34–36 — Consolidated Revision Notes

### Day 34 — Kubernetes: What We Learned

**Status:** Completed and pushed to GitHub.

Practical work:
- Deployed the existing OpsPulse Flask application to kind.
- Used Kubernetes v1.34.11 with the Debian2 environment.
- Deployed PostgreSQL as a StatefulSet.
- Created a headless Service and a 1Gi PVC.
- Used ConfigMaps and Secrets for application configuration.
- Configured Flask liveness and database-aware readiness probes.
- Tested Flask Pod replacement and automatic recovery.
- Tested PostgreSQL Pod replacement and data persistence.
- Practiced rolling updates.

Important concepts to remember:

1. **Deployment:** Maintains the required number of application Pods.
2. **StatefulSet:** Provides stable identity and storage handling for
   stateful workloads such as PostgreSQL.
3. **PVC:** Requests persistent storage independent of Pod lifetime.
4. **Service:** Provides stable network access to changing Pods.
5. **ConfigMap:** Stores non-sensitive configuration.
6. **Secret:** Stores sensitive configuration, with additional access
   controls required for secure production usage.
7. **Liveness probe:** Determines whether a container should restart.
8. **Readiness probe:** Determines whether a Pod should receive
   Service traffic.

Troubleshooting lessons:
- kind cluster setup encountered cgroup v1 compatibility issues.
- A compatible node image was used.
- Local port forwarding had to be restarted after connection refusal.
- Database outages affected readiness behavior.
- Readiness EndpointSlice transition was not conclusively verified.

Interview practice:
- Why use a StatefulSet for PostgreSQL?
- How does a PVC preserve data after a Pod replacement?
- How do readiness and liveness probes differ?
- What happens when a Deployment Pod is deleted?
- How would you troubleshoot an unhealthy Kubernetes Service?

Revision priority:
- Practice Service DNS, EndpointSlices and readiness behavior.
- Practice rollout history, rollback and troubleshooting commands.

### Day 35 — AWS Architecture: What We Learned

**Status:** Architecture documentation completed and pushed.

Verified implementation:
- Reused the existing default VPC in ap-south-1.
- Created four private subnets across two Availability Zones.
- Created and associated a private route table.
- Verified no internet default route in the private route table.
- Created separate ALB, application and database Security Groups.
- Reviewed IAM permissions and policy limitations.
- Documented AWS architecture, observability and cost choices.
- Confirmed the previously identified Day 29 manual RDS
  snapshot was absent during verification.

Architecture designed:

    Internet
       |
    Public ALB (HTTPS 443)
       |
    EC2 Application Tier (TCP 8080)
       |
    PostgreSQL RDS (TCP 5432)

Important:
- This architecture was designed, not fully deployed.
- ALB, EC2 Auto Scaling and RDS were not provisioned.
- CloudWatch alarms were planned, not deployed.
- Account-wide AWS billing clearance was not established.

Security concepts:
1. Public subnets provide the intended entry point for the ALB.
2. Application servers should be placed in private subnets.
3. Database instances should be isolated in private DB subnets.
4. ALB SG allows HTTPS from clients.
5. App SG allows application traffic from the ALB SG.
6. DB SG allows PostgreSQL traffic from the App SG.
7. IAM controls AWS API permissions.
8. Security Groups control network traffic.
9. Security Groups are stateful.

Troubleshooting lessons:
- IAM AccessDenied requires checking identity-based permissions.
- IAM inline policy size limits can block policy updates.
- Manual RDS snapshots require separate cleanup verification.
- Designing private subnets does not automatically provide
  outbound internet, DNS endpoints or software update access.

Interview practice:
- Why place EC2 application instances in private subnets?
- How does ALB forward requests to application targets?
- How do IAM and Security Groups differ?
- What happens during an Availability Zone failure?
- What is the difference between an architecture design
  and a verified deployment?

Revision priority:
- Practice ALB target health and application routing.
- Review Multi-AZ RDS behavior and network connectivity.
- Continue IAM least-privilege and AWS cost-control practice.

### Day 36 — Flask Dashboard and Incident Management

**Status:** Application and browser tests passed.
Git documentation and commit are still pending.

Implemented:
- Created app/templates/dashboard.html.
- Added GET /dashboard to Flask.
- Added incident statistics cards.
- Displayed incidents retrieved from PostgreSQL.
- Added the browser Create Incident form.
- Implemented PATCH /incidents/<id>.
- Added Resolve and Reopen buttons.
- Rebuilt the Flask Docker image after source changes.
- Connected Windows Chrome through PuTTY SSH port forwarding.

Verified:
- Flask Docker container healthy.
- PostgreSQL Docker container healthy.
- GET /ready returned HTTP 200.
- GET /dashboard returned HTTP 200 after correction.
- Existing incidents survived application rebuilds.
- Incident #3 created successfully through the browser.
- Incident Resolve and Reopen interactions worked.
- Browser counts matched GET /incidents results.

Final observed incident states:
- ID 1: OPEN
- ID 2: OPEN
- ID 3: RESOLVED

Final observed dashboard counts:
- Total: 3
- Open: 2
- Resolved: 1
- Critical: 1

Troubleshooting 1 — /ready returned HTTP 404:

Root cause:
- Docker container used an older application image.

Fix:

    docker compose up -d --build --no-deps app

Learning:
- Restarting a container does not rebuild its image.
- Verify source code and deployed image separately.

Troubleshooting 2 — /dashboard returned HTTP 500:

Error:

    jinja2.exceptions.TemplateNotFound: dashboard.html

Root cause:
- Dockerfile copied app.py but not templates/.

Fix in app/Dockerfile:

    COPY templates/ ./templates/

Verification:

    docker compose exec app ls -lh /app/templates/
    curl -I http://127.0.0.1:8082/dashboard

Learning:
- Docker images contain only packaged build-context files.
- A passing container health check does not prove all routes work.
- Application logs reveal the actual exception.

Browser connectivity:
- Windows PuTTY uses a local SSH tunnel.
- Local source port: 8082
- Remote destination: 127.0.0.1:8082
- Browser URL: http://127.0.0.1:8082/dashboard

API revision:

    GET   /health
    GET   /ready
    GET   /incidents
    POST  /incidents
    PATCH /incidents/<id>
    GET   /dashboard

Key concepts to remember:

1. **Flask route:** Associates a URL with Python application code.
2. **HTML:** Defines browser page structure.
3. **CSS:** Controls the visual presentation.
4. **JavaScript:** Calls APIs and updates dashboard elements.
5. **POST:** Creates a new incident.
6. **PATCH:** Changes an existing incident.
7. **SQL UPDATE:** Persists the status change in PostgreSQL.
8. **Dockerfile COPY:** Packages required files into the image.
9. **HTTP 404:** Requested application route or resource not found.
10. **HTTP 500:** Server-side request processing failed.
11. **SSH local forwarding:** Securely accesses the local-only service.
12. **Persistent database:** Survives application container replacement.

Interview practice:
- What causes TemplateNotFound in a Flask Docker application?
- Why can /health return 200 while /dashboard returns 500?
- What is the difference between POST and PATCH?
- Why are parameterized SQL queries useful?
- Why should PostgreSQL data not be stored inside the Flask container?
- Why did we use a PuTTY tunnel instead of publicly exposing port 8082?

Production troubleshooting challenge:

A new dashboard release returns HTTP 500, while /health
is still healthy.

Suggested investigation:
1. Inspect HTTP status.
2. Check application container logs.
3. Identify the Python traceback.
4. Inspect packaged files inside the container.
5. Check Dockerfile and build context.
6. Correct the Docker image.
7. Deploy the corrected image.
8. Verify dashboard, database readiness and incident persistence.

Revision priority:
- Practice Flask API structure and JavaScript fetch().
- Practice Docker builds and runtime debugging.
- Add automated tests for incident create/update endpoints.
- Add monitoring metrics, CI/CD and alerting in later days.

## Next Revision Milestones

- Day 37: Incident filtering, charts and UI improvements.
- Day 38: Full-application Docker Compose improvements.
- Day 39: GitHub Actions CI pipeline verification.
- Day 40: Automated deployment and rollback.
- Day 41: Prometheus metrics.
- Day 42: Grafana dashboards and alerting.
- Day 43: Kubernetes integration of the updated application.
- Day 44: Final end-to-end demo, recovery and documentation.

These are planned milestones, not verified completions.
