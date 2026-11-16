# OpsPulse — Architecture Documentation

## 1. Project Overview

OpsPulse is an incident tracking and health
monitoring application built with Python Flask.

The application will be deployed using Linux,
Docker, Docker Compose and Kubernetes.

An AWS production architecture will be designed
without creating paid cloud resources.

## 2. Application Components

- Nginx: Reverse proxy for HTTP requests.
- Flask: Handles application logic and APIs.
- PostgreSQL: Stores incident records.
- GitHub: Stores source code and documentation.
- GitHub Actions: Planned CI/CD automation.

## 3. Stage 1 — Local Linux

User / Browser
      |
      v
Debian WSL2
      |
      v
Python Flask Application
      |
      v
HTTP Response

Initial application port: 8080

Day 31 will verify processes, permissions,
listening ports, logs and application health.

## 4. Stage 2 — Docker

User / Browser
      |
      v
Linux Host Port 8080
      |
      v
Docker Container
      |
      v
Flask Application

The Flask application will run in a non-root
container where practical.

## 5. Stage 3 — Docker Compose

User / Browser
      |
      v
Nginx Reverse Proxy
      |
      v
Flask Application
      |
      v
PostgreSQL Database
      |
      v
Persistent Docker Volume

Compose will manage service networking,
environment variables, health checks and
persistent database storage.

Database port 5432 will not be publicly exposed.

## 6. Stage 4 — Kubernetes (kind)

User / kubectl port-forward
      |
      v
Kubernetes ClusterIP Service
      |
      v
Flask Deployment
      |
      +---- Flask Pod 1
      |
      +---- Flask Pod 2
      |
      v
PostgreSQL Service
      |
      v
PostgreSQL with Persistent Storage

Kubernetes will manage:

- Deployments and Pods
- Services and internal networking
- ConfigMaps and configuration
- Readiness and liveness probes
- Scaling
- Rolling updates and rollback

Nginx integration is optional in the local
Kubernetes deployment.

## 7. Stage 5 — AWS Architecture (Design Only)

Internet
    |
    v
Public HTTPS Application Load Balancer
    |
    v
Private Application Subnets
    |
    v
EC2 Auto Scaling Group or Amazon EKS
    |
    v
Private Amazon RDS PostgreSQL

The proposed architecture will include:

- VPC and two Availability Zones
- Public and private subnets
- Internet Gateway and route tables
- NAT Gateway only if required
- Security Groups
- IAM least-privilege roles
- TLS termination at the ALB
- CloudWatch monitoring
- Backup and recovery planning

No AWS resources will be created without
cost verification and approval.

## 8. Application Health

Planned endpoints:

GET /       - Application homepage
GET /health - Application process health
GET /ready  - Database dependency readiness

The /health endpoint should not depend on
PostgreSQL availability.

The /ready endpoint should check whether the
application can access its required database.

## 9. Failure and Recovery

We will practise safe failures involving:

- Application process stopped
- Docker container stopped
- Incorrect database hostname
- Kubernetes Service misconfiguration
- Deployment rollback

Each incident report will record:

Symptom -> Evidence -> Root Cause -> Fix
-> Verification

## 10. Security Principles

- No credentials committed to Git.
- Application and database use least privilege.
- PostgreSQL is not directly exposed.
- Non-root containers where possible.
- Separate non-secret configuration and secrets.
- Only disposable local environments are
  used for intentional failure tests.
