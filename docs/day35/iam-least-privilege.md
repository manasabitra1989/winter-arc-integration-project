# Day 35 — OpsPulse IAM Least-Privilege Design

## Objective

Design IAM access for the existing OpsPulse Flask and
PostgreSQL project, following the Day 35 assignment.

This document is DESIGN ONLY.
No new IAM roles or policies were created in AWS.

## 1. Deployment Pipeline Role

Proposed role:
OpsPulseDeploymentRole

Actor:
GitHub Actions CI/CD pipeline.

Trust relationship:
GitHub Actions OIDC provider, restricted to the approved
repository, branch, and workflow or environment.

Example repository:
manasabitra1989/winter-arc-integration-project

Required actions depend on the deployment method.

For the proposed EC2 Auto Scaling architecture:
- Upload approved deployment artifacts to designated storage.
- Trigger an approved deployment mechanism.
- Read deployment and rollout status.
- Use iam:PassRole only if the deployment mechanism
  requires it, scoped to an approved role and service.

If Amazon ECR is selected:
- Allow required image push/pull operations only for
  the designated OpsPulse repository.

Resource scope:
- Approved OpsPulse deployment resources only.
- Designated artifact storage or container repository.
- Approved deployment service resources.

Restrictions:
- No broad AdministratorAccess.
- No unnecessary IAM user or policy management.
- No permanent access keys stored in GitHub secrets.
- No unrestricted iam:PassRole.

## 2. Application Workload Role

Proposed role:
OpsPulseAppRole

Actor:
EC2 instances running OpsPulse.

Trust relationship:
AWS EC2 service principal, ec2.amazonaws.com.

EC2 instances receive the role through an instance profile.

Suggested permissions, only if required:
- Read specific OpsPulse application parameters.
- Retrieve the specific PostgreSQL credential secret,
  if AWS Secrets Manager is selected.
- Write application logs and metrics to designated
  CloudWatch destinations.
- Use approved Systems Manager functionality through
  an appropriately scoped instance policy.

Resource scope:
- OpsPulse-specific parameters and secrets.
- OpsPulse-specific CloudWatch log groups.
- Approved management resources.

Important:
RDS PostgreSQL network connections do not automatically
require AWS IAM permissions.

Traditional PostgreSQL authentication uses database
credentials, while IAM database authentication is a
separate optional capability.

Restrictions:
- No AdministratorAccess.
- No wildcard access to all Secrets Manager secrets.
- No permanent AWS keys inside app.py or Docker images.
- No unnecessary EC2 or VPC administration permissions.

## 3. Human Operator Role

Proposed role:
OpsPulseOperatorRole

Actor:
Authorized DevOps or Platform Engineer.

Trust relationship:
Approved IAM Identity Center or organizational identity
provider, with role assignment and MFA where applicable.

Suggested permissions:
- Describe relevant EC2, ALB, VPC, and RDS resources.
- Read approved CloudWatch metrics and logs.
- Inspect deployment and target health.
- Start approved Systems Manager sessions.
- Perform tightly scoped recovery operations only
  when authorized.

Resource scope:
- OpsPulse project resources where supported.
- Approved AWS account and environment.
- Specific management actions rather than broad admin.

Restrictions:
- MFA where applicable.
- No shared IAM accounts.
- No unrestricted production database access.
- No permanent application access keys.

## 4. IAM vs Security Groups

IAM:
Determines who can call AWS APIs and what actions
they can perform.

Security Groups:
Control network traffic permitted to and from
associated AWS network interfaces.

Example:

IAM may permit an operator to inspect RDS status.

Database Security Group permits PostgreSQL TCP 5432
only from the OpsPulse Application Security Group.

Both layers have different responsibilities.

## 5. Current Learning Account Findings

IAM user:
devops-learner

Direct managed policies:
10

Inline policies:
7

IAM group memberships:
0

These are existing lab permissions, not proposed
production application permissions.

Actual policy contents and any permissions boundary
have not been fully reviewed.

Do not remove existing learning-account permissions
without verifying their use in other assignments.

## 6. Security Principles

- Apply least privilege.
- Separate human and machine identities.
- Prefer short-lived credentials and role assumption.
- Avoid hard-coded access keys.
- Restrict trust relationships.
- Review access periodically.
- Monitor IAM activity through appropriate audit services.
