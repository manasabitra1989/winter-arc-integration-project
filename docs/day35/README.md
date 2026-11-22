# Day 35/90 — AWS Architecture and Security Design

## 1. Objective

Design a secure, resilient, cost-conscious AWS architecture
for the same OpsPulse application developed on Days 30–34.

Architecture:
Internet -> HTTPS ALB -> Private Flask EC2 instances
-> Private RDS PostgreSQL

Primary proposal: EC2 Auto Scaling across two AZs.

Alternative proposal: Amazon EKS.

This is a DESIGN-FIRST lab. No AWS application stack
was deployed.

## 2. Existing OpsPulse Project

Repository:
https://github.com/manasabitra1989/winter-arc-integration-project

Application:
Python Flask, port 8080

Endpoints:
- /health: Flask process health
- /ready: Database-aware readiness
- /incidents: Incident API

Previous days:
- Day 30: Integration project kickoff
- Day 31: Flask, Linux, monitoring, deployment and rollback
- Day 32: Docker
- Day 33: Docker Compose and PostgreSQL
- Day 34: Kubernetes kind and PostgreSQL StatefulSet
- Day 35: AWS architecture and security design

## 3. AWS Environment

Linux host: Debian2
AWS CLI profile: devops-learner
AWS region: ap-south-1 (Mumbai)

Existing default VPC:
vpc-0db58479bcc738ebc
CIDR: 172.31.0.0/16

We reused the default VPC.
We did NOT create a new VPC for Day 35.

AWS CLI installation was completed on Debian2.
AWS CLI version during the exercise: 2.42.1

Authentication used AWS CLI remote login.

Reference commands:

    aws --version

    aws login --remote \
      --profile devops-learner \
      --region ap-south-1

    aws sts get-caller-identity \
      --profile devops-learner

Never publish AWS login codes, credentials, or tokens.

## 4. Existing Public Networking

Public subnet in ap-south-1a:
subnet-00698086d711aa54c
CIDR: 172.31.32.0/20

Public subnet in ap-south-1b:
subnet-0411976d508d370d9
CIDR: 172.31.0.0/20

An additional existing default subnet is in ap-south-1c:
subnet-06bd1d7967901109e
CIDR: 172.31.16.0/20

Main route table:
rtb-01d69df10874e9a68

Routes:
172.31.0.0/16 -> local
0.0.0.0/0 -> igw-00ceb7cd6b7fcadf5

The proposed internet-facing ALB would use two
appropriate public subnets.

No ALB was deployed in this lab.

## 5. Private Subnets Created

| Tier | AZ | CIDR | Subnet ID |
|---|---|---|---|
| App A | ap-south-1a | 172.31.96.0/24 | subnet-001cffb023e2efc81 |
| App B | ap-south-1b | 172.31.97.0/24 | subnet-055cdbd6069309aea |
| DB A | ap-south-1a | 172.31.98.0/24 | subnet-0c9a19768bdfc303a |
| DB B | ap-south-1b | 172.31.99.0/24 | subnet-0552ecaa76cc21511 |

All four subnets:
- Belong to the existing default VPC
- Have MapPublicIpOnLaunch=False
- Use the Day 35 private route table

Private route table:
rtb-00958f5db5fc68a04

Name:
day35-opspulse-private-rt

Routes:
172.31.0.0/16 -> local

No default route to NAT Gateway or Internet Gateway.

## 6. AWS CLI — Network Creation Reference

The resource IDs above are VERIFIED Day 35 results.

Commands in this section are reproducible references
for how these resources can be created. They are not a
verbatim terminal-history transcript.

DO NOT RERUN CREATE COMMANDS against this account.
The resources already exist.

### Create the private route table

    aws ec2 create-route-table \
      --vpc-id vpc-0db58479bcc738ebc \
      --region ap-south-1 \
      --profile devops-learner

AWS automatically adds the VPC local route.

### Create the application subnets

    aws ec2 create-subnet \
      --vpc-id vpc-0db58479bcc738ebc \
      --availability-zone ap-south-1a \
      --cidr-block 172.31.96.0/24 \
      --region ap-south-1 \
      --profile devops-learner

    aws ec2 create-subnet \
      --vpc-id vpc-0db58479bcc738ebc \
      --availability-zone ap-south-1b \
      --cidr-block 172.31.97.0/24 \
      --region ap-south-1 \
      --profile devops-learner

### Create the database subnets

    aws ec2 create-subnet \
      --vpc-id vpc-0db58479bcc738ebc \
      --availability-zone ap-south-1a \
      --cidr-block 172.31.98.0/24 \
      --region ap-south-1 \
      --profile devops-learner

    aws ec2 create-subnet \
      --vpc-id vpc-0db58479bcc738ebc \
      --availability-zone ap-south-1b \
      --cidr-block 172.31.99.0/24 \
      --region ap-south-1 \
      --profile devops-learner

### Disable automatic public IP assignment

The following shows the operation applied to App A:

    aws ec2 modify-subnet-attribute \
      --subnet-id subnet-001cffb023e2efc81 \
      --no-map-public-ip-on-launch \
      --region ap-south-1 \
      --profile devops-learner

The same setting was applied to the other three
private subnets.

### Associate the private route table

Reference command for App A:

    aws ec2 associate-route-table \
      --route-table-id rtb-00958f5db5fc68a04 \
      --subnet-id subnet-001cffb023e2efc81 \
      --region ap-south-1 \
      --profile devops-learner

This association was completed for all four
Day 35 private subnets.

### Verify subnet settings

    aws ec2 describe-subnets \
      --subnet-ids \
        subnet-001cffb023e2efc81 \
        subnet-055cdbd6069309aea \
        subnet-0c9a19768bdfc303a \
        subnet-0552ecaa76cc21511 \
      --region ap-south-1 \
      --profile devops-learner \
      --query 'Subnets[].{ID:SubnetId,CIDR:CidrBlock,AZ:AvailabilityZone,PublicIP:MapPublicIpOnLaunch}' \
      --output table

### Verify private route table

    aws ec2 describe-route-tables \
      --route-table-ids rtb-00958f5db5fc68a04 \
      --region ap-south-1 \
      --profile devops-learner \
      --query 'RouteTables[].{Routes:Routes,Associations:Associations}' \
      --output json

Expected:
- Only VPC local routing
- Four explicit subnet associations

## 7. Security Groups Created

ALB SG:
day35-opspulse-alb-sg
sg-0e08f8b68789a4fac

App SG:
day35-opspulse-app-sg
sg-0a5f99b745a98ff82

DB SG:
day35-opspulse-db-sg
sg-015e80ebc7cff7210

Verified rules:

| Group | Inbound | Outbound |
|---|---|---|
| ALB | TCP 443 from 0.0.0.0/0 | TCP 8080 to App SG |
| App | TCP 8080 from ALB SG | TCP 5432 to DB SG |
| DB | TCP 5432 from App SG | No outbound rules |

### Security Group creation reference

Example for ALB SG:

    aws ec2 create-security-group \
      --group-name day35-opspulse-alb-sg \
      --description "OpsPulse ALB security group" \
      --vpc-id vpc-0db58479bcc738ebc \
      --region ap-south-1 \
      --profile devops-learner

Corresponding groups were created for App and DB.

Do not rerun this command; the groups already exist.

### Example: permit HTTPS to the ALB

    aws ec2 authorize-security-group-ingress \
      --group-id sg-0e08f8b68789a4fac \
      --protocol tcp \
      --port 443 \
      --cidr 0.0.0.0/0 \
      --region ap-south-1 \
      --profile devops-learner

### Example: ALB to application

    aws ec2 authorize-security-group-ingress \
      --group-id sg-0a5f99b745a98ff82 \
      --protocol tcp \
      --port 8080 \
      --source-group sg-0e08f8b68789a4fac \
      --region ap-south-1 \
      --profile devops-learner

### Example: application to database

    aws ec2 authorize-security-group-ingress \
      --group-id sg-015e80ebc7cff7210 \
      --protocol tcp \
      --port 5432 \
      --source-group sg-0a5f99b745a98ff82 \
      --region ap-south-1 \
      --profile devops-learner

The verified outbound rules were also restricted:
ALB -> App TCP 8080
App -> DB TCP 5432
DB -> no outbound rules

Default allow-all outbound permissions were removed.

The exact rule-management history, including generated
Security Group rule IDs, is not preserved here.

### Verify Security Group rule counts

    aws ec2 describe-security-groups \
      --region ap-south-1 \
      --profile devops-learner \
      --group-ids \
        sg-0e08f8b68789a4fac \
        sg-0a5f99b745a98ff82 \
        sg-015e80ebc7cff7210 \
      --query 'SecurityGroups[].{Name:GroupName,InboundCount:length(IpPermissions),OutboundCount:length(IpPermissionsEgress)}' \
      --output table

Verified result:
- ALB: 1 inbound, 1 outbound
- App: 1 inbound, 1 outbound
- DB: 1 inbound, 0 outbound

See security-group-matrix.md for the full design.

## 8. IAM Review

Existing IAM user:
devops-learner

Verified:
- 10 directly attached managed policies
- 7 inline policies
- 0 IAM group memberships

No new production IAM roles were created.

Proposed roles:
- OpsPulseDeploymentRole
- OpsPulseAppRole
- OpsPulseOperatorRole

See iam-least-privilege.md.

## 9. High Availability

Proposed application:
- ALB in two public AZ subnets
- Auto Scaling instances in two private app subnets
- Target health checks on /health
- Separate monitoring of database-aware /ready

Proposed database:
- Amazon RDS PostgreSQL Multi-AZ
- Private DB subnet group spanning two AZs
- Application database reconnection and retry handling

See resilience-and-traffic-flow.md.

## 10. Observability

Proposed monitoring signals:
- ALB target health
- ALB HTTP 5xx errors
- Application error rate
- API latency
- EC2 CPU and memory
- RDS availability and connections
- Deployment failures

See observability-plan.md.

## 11. Architecture Cost Decision

Preferred:
ALB + EC2 Auto Scaling + private RDS.

Alternative:
ALB + Amazon EKS + private RDS.

Cost drivers:
- Load balancing
- Compute
- Database
- Storage
- Data transfer
- Logging and metrics
- NAT or VPC endpoints
- EKS control plane if using EKS

See cost-comparison.md.

No pricing assumption substitutes for a current
AWS Pricing Calculator estimate.

## 12. Troubleshooting and Lessons

### AWS CLI unavailable on Debian2

Issue:
AWS CLI was not installed on the project host.

Resolution:
Installed AWS CLI v2 and authenticated with the
existing learning profile using remote login.

### Route table visibility in AWS Console

Issue:
Difficulty locating the private route table.

What to check:
- Correct AWS region
- VPC filters
- Route table ID
- Subnet associations

Resolution:
Verified the route table with AWS CLI.

### Private subnet isolation

Issue:
Creating a subnet does not automatically make it
private or attach the intended route table.

Resolution:
- Disabled automatic public IP assignment
- Created a private route table
- Explicitly associated all four subnets
- Verified the resulting settings

### Security Group default egress

Issue:
New Security Groups normally begin with a default
outbound allow rule.

Resolution:
Restricted or removed default outbound permissions
and checked the final inbound/outbound rules.

### Previous lab resources

Older Day 29 Security Groups were not modified.

Existing shared/default VPC resources were preserved.

## 13. Scope and Limitations

Completed in AWS:
- Reused the default VPC
- Created four private subnets
- Created one private route table
- Created three Security Groups
- Inspected IAM user permissions
- Verified network configuration

Not deployed:
- Application Load Balancer
- EC2 Auto Scaling Group
- EC2 application instances
- RDS PostgreSQL
- EKS cluster
- NAT Gateway

No real AWS application traffic or failover was tested.

Actual production deployment would require additional
DNS, IAM, TLS, monitoring, deployment, management,
and connectivity design.

## 14. Assignment Deliverables

- aws-architecture.md
- security-group-matrix.md
- iam-least-privilege.md
- resilience-and-traffic-flow.md
- observability-plan.md
- cost-comparison.md
- README.md

## 15. Final Closure Checklist

- [x] Target architecture designed
- [x] Private subnet design verified
- [x] Security Group rules verified
- [x] IAM role design documented
- [x] Resilience plan documented
- [x] Observability plan documented
- [x] Cost drivers compared
- [ ] Final AWS resource audit
- [ ] Final documentation validation
- [ ] Update revision tracker
- [ ] Git commit and push
- [ ] Troubleshooting and interview review

## 16. Final RDS Snapshot Cleanup

During the Day 35 cost audit, an existing manual
RDS snapshot from Day 29 was discovered.

Snapshot:
day29-postgres-snapshot

Source database:
day29-postgres

Engine:
PostgreSQL

Source database allocated storage:
20 GiB

Initial status:
available

Issue encountered:
The devops-learner IAM user received AccessDenied
for rds:DeleteDBSnapshot.

A subsequent attempt to add an inline cleanup policy
encountered the 2048 non-whitespace character limit
for IAM user inline policies.

Resolution:
Cleanup was handled outside the restricted IAM CLI
session. The exact deletion mechanism was not
independently verified in this lab record.

Final verification command:

    aws rds describe-db-snapshots \
      --snapshot-type manual \
      --region ap-south-1 \
      --profile devops-learner \
      --query 'DBSnapshots[].[DBSnapshotIdentifier,Status]' \
      --output table

Verified result:
No manual RDS DB snapshots returned in ap-south-1.

Important:
This verification does not cover all AWS regions,
automated backups, or unrelated AWS services.
