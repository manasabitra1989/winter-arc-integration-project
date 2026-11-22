# Day 35 — OpsPulse AWS Architecture

## Design status

Proposed architecture only. Networking and security groups
exist, but ALB, EC2 Auto Scaling, and RDS are not deployed.

## Architecture diagram

```mermaid
flowchart TB
    USERS["Internet Users"]
    IGW["Internet Gateway"]

    subgraph VPC["AWS Default VPC - 172.31.0.0/16"]

        subgraph PUBLIC["Public Subnet Tier"]
            ALB["Application Load Balancer<br/>HTTPS 443 - TLS termination"]
        end

        subgraph APP_TIER["Private Application Tier - EC2 Auto Scaling"]
            APP_A["AZ 1a - Flask<br/>172.31.96.0/24"]
            APP_B["AZ 1b - Flask<br/>172.31.97.0/24"]
        end

        subgraph DB_TIER["Private Database Tier - RDS Multi-AZ"]
            DB_A["AZ 1a - DB subnet<br/>172.31.98.0/24"]
            DB_B["AZ 1b - DB subnet<br/>172.31.99.0/24"]
            RDS[("RDS PostgreSQL<br/>Managed Multi-AZ")]
        end

        ALB -->|"TCP 8080"| APP_A
        ALB -->|"TCP 8080"| APP_B

        APP_A -->|"TCP 5432"| RDS
        APP_B -->|"TCP 5432"| RDS

        RDS -.->|"Subnet group"| DB_A
        RDS -.->|"Subnet group"| DB_B
    end

    USERS -->|"HTTPS 443"| IGW
    IGW --> ALB

    CW["CloudWatch Monitoring"]
    IAM["IAM Roles / SSM"]

    APP_A -.-> CW
    APP_B -.-> CW
    IAM -.-> APP_A
    IAM -.-> APP_B
```

## Existing network

VPC: vpc-0db58479bcc738ebc

Main route table:
rtb-01d69df10874e9a68
- VPC local route
- Default route to Internet Gateway

Private route table:
rtb-00958f5db5fc68a04
- 172.31.0.0/16 -> local
- No default internet route

### Private application subnets

AZ 1a: 172.31.96.0/24
AZ 1b: 172.31.97.0/24

### Private database subnets

AZ 1a: 172.31.98.0/24
AZ 1b: 172.31.99.0/24

## Security-group design

Internet -> ALB: TCP 443
ALB SG -> App SG: TCP 8080
App SG -> DB SG: TCP 5432
Database: no direct internet ingress

## Availability and recovery

- ALB distributes traffic across healthy application targets.
- EC2 Auto Scaling replaces unhealthy application instances.
- Two AZs reduce dependence on a single Availability Zone.
- RDS Multi-AZ provides database failover in the proposed design.
- Rolling deployments require health checks and rollback controls.

## Operations and monitoring

- ALB target health and HTTP 5xx
- OpsPulse application errors and latency
- EC2 CPU and memory monitoring
- RDS availability and connection metrics
- Deployment failures and rollback events
- CloudWatch alarms and defined log retention

## Private connectivity considerations

Current private subnets have local routing only.

Production application instances would need a planned
solution for AWS API access, image downloads, patching,
monitoring, and administration.

Possible choices include carefully scoped VPC endpoints
and NAT where necessary. Costs must be reviewed first.

The current App SG outbound rule allows only PostgreSQL
traffic, so additional approved rules would be required
before a real deployment.

## Cost and deployment scope

No ALB, EC2, RDS, NAT Gateway, or EKS resource was
deployed for this Day 35 architecture exercise.
