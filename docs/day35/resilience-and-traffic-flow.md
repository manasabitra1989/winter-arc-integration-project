# Day 35 — OpsPulse AWS Resilience and Traffic Flow

## Architecture status

This is a design exercise.

The existing AWS VPC, private subnets, route table,
and Security Groups have been configured.

ALB, EC2 Auto Scaling, and RDS are proposed components.
They have not been deployed.

## 1. Normal traffic flow

1. A user sends an HTTPS request on TCP 443.
2. The internet-facing ALB terminates TLS using an
   approved certificate.
3. The ALB selects a healthy OpsPulse application target.
4. The request reaches Flask on TCP 8080.
5. Flask accesses PostgreSQL on TCP 5432.
6. The response returns through the established connections.

Security Group boundaries:

Internet -> ALB SG: TCP 443
ALB SG -> App SG: TCP 8080
App SG -> DB SG: TCP 5432

PostgreSQL has no direct public ingress.

## 2. ALB health checks

Proposed ALB target-group health-check path:

    /health

Application listener port:

    8080

Reason:

/health checks whether the OpsPulse application process
is responding.

The separate /ready endpoint verifies database
connectivity and should be monitored independently.

An ALB using only /health may consider Flask healthy
while database-dependent requests fail.

Health-check behavior, thresholds, and fail-open
conditions must be considered before production use.

## 3. Application instance failure

Scenario:

An OpsPulse EC2 instance stops responding.

Expected design behavior:

1. ALB health checks detect the unhealthy target.
2. ALB avoids unhealthy targets when healthy alternatives exist.
3. EC2 Auto Scaling health checks identify and replace
   unhealthy instances when configured appropriately.
4. The replacement instance starts OpsPulse.
5. The target becomes available after passing health checks.

Requirements:

- Auto Scaling Group across at least two AZs
- Suitable instance health-check settings
- Reliable application bootstrap
- Accessible deployment artifacts
- Required network connectivity
- Monitoring and alerting

This behavior has not been tested in AWS during Day 35.

## 4. Availability Zone failure

Scenario:

Availability Zone ap-south-1a becomes unavailable.

Proposed architecture:

App instances are distributed across AZ 1a and AZ 1b.

The ALB spans public subnets in both AZs.

If one AZ fails, surviving healthy application
capacity in the other AZ can continue handling traffic.

Important:

Actual availability depends on sufficient surviving
capacity, health checks, dependencies, and service
configuration.

Multi-AZ does not guarantee zero downtime.

## 5. PostgreSQL availability

Proposed database architecture:

Amazon RDS PostgreSQL with Multi-AZ availability.

The DB subnet group spans private database subnets
in two Availability Zones.

A managed Multi-AZ deployment can provide automatic
failover to a standby during supported failure events.

For a traditional Multi-AZ DB instance deployment,
the standby is not used for normal read scaling.

The application should use the RDS endpoint and
implement appropriate database retry and reconnection
behavior.

The database has not been deployed during Day 35.

## 6. Deployment and rollback

Proposed deployment approach:

1. Build and test the application artifact.
2. Run security and quality checks.
3. Publish the versioned artifact.
4. Deploy to a staging environment.
5. Roll out to production using a controlled mechanism.
6. Verify application health and incident API behavior.
7. Monitor error rates and target health.
8. Roll back to the last known-good version if needed.

Do not store AWS access keys in GitHub Actions.

Prefer GitHub Actions OIDC with a scoped deployment role.

## 7. Administrative access

Preferred approach:

AWS Systems Manager Session Manager.

Avoid broad inbound SSH access on TCP 22.

Requirements include appropriate IAM permissions,
SSM Agent availability, and network access to required
Systems Manager service endpoints.

Our private subnets currently have no internet default
route, so required VPC endpoints or another approved
connectivity mechanism must be planned.

## 8. Failure response checklist

Application unavailable:
- Check ALB target health.
- Inspect application logs.
- Verify EC2 instance health.
- Inspect Auto Scaling activities.
- Verify database connectivity.

Database unavailable:
- Check RDS status and events.
- Review database connection failures.
- Verify database Security Group rules.
- Check subnet routing and DNS resolution.
- Verify failover and application reconnection.

Deployment failure:
- Review pipeline execution.
- Inspect application startup logs.
- Check target registration and health.
- Compare the new and previous application versions.
- Roll back if needed.

## 9. Learning takeaway

High availability requires multiple layers:

- Healthy application compute
- Load balancing
- Multi-AZ placement
- Database resilience
- Correct network permissions
- Monitoring and recovery procedures

A single healthy EC2 instance is not high availability.
