# Day 35 — AWS Cost-Aware Architecture Comparison

## Objective

Compare two possible AWS architectures for OpsPulse.

This document contains design estimates and cost
drivers, not an actual AWS bill or deployment quote.

Region: ap-south-1 (Mumbai)

## Option A — ALB + EC2 Auto Scaling + RDS

Architecture:

Users
  -> HTTPS Application Load Balancer
  -> EC2 Auto Scaling Group in private subnets
  -> Amazon RDS PostgreSQL in private DB subnets

Advantages:
- Simpler operations for our existing Flask application
- Familiar Linux and EC2 administration
- Auto Scaling supports instance replacement
- Multi-AZ placement improves resilience
- No EKS control-plane charge

Disadvantages:
- EC2 operating system maintenance
- Need a reliable deployment and patching mechanism
- Application scaling occurs at instance level
- Instance bootstrap and health checks need management

Potential charges:
- Application Load Balancer hours and LCUs
- EC2 instances
- EBS storage
- RDS instance and storage
- Backups beyond applicable allowances
- CloudWatch logs, metrics, and alarms
- Data transfer
- NAT Gateway or VPC endpoints if used
- Public IPv4 addresses where applicable

## Option B — ALB + Amazon EKS + RDS

Architecture:

Users
  -> HTTPS Application Load Balancer
  -> EKS Kubernetes Service and Pods
  -> Amazon RDS PostgreSQL in private DB subnets

Advantages:
- Kubernetes-native workload management
- Pod-level scheduling and scaling
- Deployments, rolling updates, and readiness probes
- Consistent container orchestration
- Useful for teams already operating Kubernetes

Disadvantages:
- More Kubernetes operational knowledge required
- Cluster and node maintenance responsibilities
- Additional IAM, RBAC, networking, and add-on design
- Additional EKS cluster charges

Potential charges:
- EKS cluster pricing
- Kubernetes worker compute or Fargate
- Application Load Balancer hours and LCUs
- EBS or other persistent storage
- RDS instance and storage
- CloudWatch monitoring
- Network traffic
- NAT Gateways or VPC endpoints
- Public IPv4 addresses where applicable
- Optional EKS capabilities and features

## Comparison Matrix

| Factor | EC2 Auto Scaling | EKS |
|---|---|---|
| Complexity | Lower | Higher |
| Compute scaling | Instance level | Pod and node level |
| Security | IAM and Security Groups | IAM, RBAC, Security Groups |
| High availability | Multi-AZ Auto Scaling | Multi-AZ nodes and Pods |
| Deployment | Instance deployment strategy | Kubernetes rolling deployment |
| EKS cluster charge | No | Yes |
| Database | Private RDS | Private RDS |
| Learning fit | AWS infrastructure | Kubernetes operations |

## Cost Calculation Approach

Calculate monthly costs using the AWS Pricing
Calculator for the Mumbai region.

Include:
1. Expected number and type of compute instances
2. Approximate hours per month
3. ALB capacity and traffic
4. RDS instance class and storage
5. EKS control plane, if applicable
6. Monitoring and log volume
7. Network connectivity and data transfer
8. Backups, storage, and public IPv4 usage

Do not assume Free Tier eligibility.

## Decision

Preferred design for this exercise:

Option A — ALB + EC2 Auto Scaling + private RDS.

Reason:

OpsPulse is currently a relatively small Flask
application with PostgreSQL.

EC2 Auto Scaling gives us an opportunity to practice
AWS high-availability and deployment concepts without
adding a Kubernetes control-plane dependency.

Option B remains a suitable future alternative when
Kubernetes orchestration is an actual requirement.

## Current AWS Resource Status

Existing Day 35 resources:
- Four private subnets
- One private route table
- Three Security Groups

Not deployed for Day 35:
- ALB
- EC2 instances
- RDS database
- EKS cluster
- NAT Gateway

Previously completed resource audits did not find
running resources in those charged categories.

A fresh final audit is required before closing Day 35.

## Official Pricing References

https://aws.amazon.com/ec2/pricing/
https://aws.amazon.com/eks/pricing/
https://aws.amazon.com/elasticloadbalancing/pricing/
https://aws.amazon.com/rds/postgresql/pricing/
https://aws.amazon.com/vpc/pricing/
https://aws.amazon.com/cloudwatch/pricing/
https://calculator.aws/
