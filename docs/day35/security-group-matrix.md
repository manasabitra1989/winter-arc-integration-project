# Day 35 — OpsPulse AWS Security Group Matrix

## Purpose

Document the security boundaries for the OpsPulse
Flask + PostgreSQL AWS architecture.

Region: ap-south-1
VPC: vpc-0db58479bcc738ebc

These Security Groups exist in AWS.

No Day 35 ALB, EC2, or RDS workload has been deployed.

## Security Group IDs

| Tier | Security Group | ID |
|---|---|---|
| ALB | day35-opspulse-alb-sg | sg-0e08f8b68789a4fac |
| Application | day35-opspulse-app-sg | sg-0a5f99b745a98ff82 |
| Database | day35-opspulse-db-sg | sg-015e80ebc7cff7210 |

## Inbound traffic matrix

| Source | Destination | Protocol | Port | Purpose |
|---|---|---|---|---|
| Internet (0.0.0.0/0) | ALB SG | TCP | 443 | Client HTTPS access |
| ALB SG | App SG | TCP | 8080 | Forward requests to Flask |
| App SG | DB SG | TCP | 5432 | PostgreSQL connections |

The database has no direct public inbound rule.

## Outbound traffic matrix

| Source | Destination | Protocol | Port |
|---|---|---|---|
| ALB SG | App SG | TCP | 8080 |
| App SG | DB SG | TCP | 5432 |
| DB SG | None | - | - |

## Security Group behavior

Security Groups are stateful.

Response traffic for an allowed connection does not
require a matching reverse-direction rule.

Security Group references permit communication from
network interfaces associated with the referenced group.

They do not provide application-level authentication.

## Network boundaries

Existing public subnets inherit the main route table,
which has an Internet Gateway default route.

All four OpsPulse private subnets explicitly use:
rtb-00958f5db5fc68a04

The private route table has only:
172.31.0.0/16 -> local

All four private subnets have automatic public IPv4
assignment disabled.

## Operational access

Do not expose SSH port 22 to the internet.

Prefer AWS Systems Manager Session Manager with
appropriately scoped IAM and network connectivity.

## Important production considerations

The current Security Group rules are a simplified lab
configuration.

Before deploying actual workloads, evaluate:

- DNS resolution and VPC DNS settings
- Systems Manager connectivity
- CloudWatch agent and logging connectivity
- Container image downloads and package updates
- Required AWS API calls
- VPC endpoints and NAT gateway requirements
- TLS configuration and certificate management
- ALB health-check port and application health endpoints

The current application egress policy only allows TCP
5432 to the database Security Group.

That is not sufficient for every production dependency.

No traffic-flow test has been performed against actual
AWS application or database workloads.

## Verified results

ALB SG:
- 1 inbound rule
- 1 outbound rule

Application SG:
- 1 inbound rule
- 1 outbound rule

Database SG:
- 1 inbound rule
- 0 outbound rules
