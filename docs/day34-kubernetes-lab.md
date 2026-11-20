# Day 34 — Kubernetes Integration Lab

## Project

OpsPulse — Production Application Monitoring & Incident Tracker

Repository:
https://github.com/manasabitra1989/winter-arc-integration-project

This lab extends the SAME OpsPulse application developed on Days 30–33.

## Learning objectives

- Create a local Kubernetes cluster using kind
- Understand Deployments and StatefulSets
- Deploy Flask and PostgreSQL
- Configure ConfigMaps and Secrets
- Understand ClusterIP and headless Services
- Use PersistentVolumeClaims
- Practice Kubernetes self-healing
- Perform rolling updates
- Understand liveness and readiness probes
- Simulate and recover from database outages

## Environment

Host: Debian 12
Cluster: opspulse
Context: kind-opspulse
Node: opspulse-control-plane
Kubernetes: v1.34.11
Namespace: opspulse
Docker: 29.9.2
Host RAM: approximately 3.7 GiB
Swap: 1 GiB

No AWS resources were created for this lab.

## 1. Kubernetes installation troubleshooting

Initially attempted to create the cluster using the
default kind node image.

The cluster creation failed during kubeadm setup.

Diagnostic commands:

    docker info --format 'CgroupVersion={{.CgroupVersion}} CgroupDriver={{.CgroupDriver}}'
    stat -fc %T /sys/fs/cgroup
    docker exec opspulse-control-plane journalctl -u kubelet -n 60

Observed:

    CgroupVersion=1
    CgroupDriver=cgroupfs
    kubelet is configured to not run on a host using cgroup v1

Cause:

The selected newer Kubernetes node image did not support
the host's legacy cgroup v1 configuration.

Lab workaround:

    kind delete cluster --name opspulse
    kind create cluster --name opspulse --image kindest/node:v1.34.11 --wait 180s

Verification:

    kind get clusters
    kubectl config current-context
    kubectl get nodes
    kubectl get pods -A
    kubectl get storageclass

Result:

The opspulse-control-plane node reached Ready.

Note:

Using a compatible node image is a temporary lab workaround.
Migrating the host to cgroup v2 is a future improvement.

## 2. Load application images

Existing Day 33 application image:

    docker images opspulse-day33-app

Load application:

    kind load docker-image opspulse-day33-app:latest --name opspulse

Load database:

    kind load docker-image postgres:17-alpine --name opspulse

Verify images in the node:

    docker exec opspulse-control-plane crictl images | grep opspulse
    docker exec opspulse-control-plane crictl images | grep postgres

The kind node has its own container image store.

## 3. Create Kubernetes namespace

    kubectl create namespace opspulse
    kubectl get namespaces

Namespaces logically group Kubernetes resources.

## 4. Configure the application

Manifest:

    kubernetes/day34/configmap.yaml

ConfigMap:

    opspulse-config

Keys:

    DATABASE_HOST=db
    DATABASE_PORT=5432
    DATABASE_NAME=opspulse
    DATABASE_USER=opspulse

Commands:

    kubectl apply -f kubernetes/day34/configmap.yaml
    kubectl get configmap opspulse-config -n opspulse

Database credentials are stored separately in a Secret.

Secret creation:

    read -rs -p "Enter Kubernetes PostgreSQL password: " K8S_DB_PASS; echo

    kubectl create secret generic opspulse-db-secret -n opspulse --from-literal=POSTGRES_PASSWORD="$K8S_DB_PASS" --from-literal=DATABASE_PASSWORD="$K8S_DB_PASS"

    unset K8S_DB_PASS

    kubectl get secret opspulse-db-secret -n opspulse

The password must not be committed to Git.

Kubernetes Secrets are not automatically encrypted simply
because their data is represented using base64 encoding.

## 5. Deploy PostgreSQL

Manifest:

    kubernetes/day34/postgres.yaml

Resources:

- Headless Service: db
- StatefulSet: postgres
- Pod: postgres-0
- PVC: postgres-data-postgres-0

Image:

    postgres:17-alpine

Database port:

    5432

PVC:

    1Gi
    ReadWriteOnce
    StorageClass: standard

Commands:

    kubectl apply --dry-run=server -f kubernetes/day34/postgres.yaml
    kubectl apply -f kubernetes/day34/postgres.yaml
    kubectl get pods -n opspulse
    kubectl get pvc -n opspulse
    kubectl get svc -n opspulse

Database readiness:

    kubectl exec -n opspulse postgres-0 -- pg_isready -U opspulse -d opspulse

SQL validation:

    kubectl exec -n opspulse postgres-0 -- psql -U opspulse -d opspulse -c "SELECT current_database(), current_user;"

The db Service has ClusterIP None because it is headless.

Important:

Never delete the PVC while trying to recover the database.

The local-path volume may be lost if the kind cluster is deleted.

## 6. Deploy Flask

Manifest:

    kubernetes/day34/app.yaml

Resources:

- Deployment: opspulse-app
- ClusterIP Service: opspulse-app
- Flask application Pod

Initial image:

    opspulse-day33-app:latest

Commands:

    kubectl apply --dry-run=server -f kubernetes/day34/app.yaml
    kubectl apply -f kubernetes/day34/app.yaml
    kubectl get deployments -n opspulse
    kubectl get pods -n opspulse
    kubectl get svc -n opspulse

Service ClusterIP observed:

    10.96.18.103

Service port:

    8080

Flask connects to PostgreSQL using:

    db:5432

This uses Kubernetes Service DNS.

## 7. Test Flask and incident creation

Start port forwarding in a separate terminal:

    kubectl port-forward -n opspulse svc/opspulse-app 8083:8080 --address 127.0.0.1

Then test:

    curl -i http://127.0.0.1:8083/
    curl -i http://127.0.0.1:8083/health
    curl -i http://127.0.0.1:8083/incidents

Create an incident:

    curl -i -X POST http://127.0.0.1:8083/incidents -H "Content-Type: application/json" -d '{"title":"Kubernetes application health check failed","severity":"HIGH"}'

Observed:

    HTTP 201 CREATED
    id: 1
    severity: HIGH
    status: OPEN

Retrieve incidents:

    curl -s http://127.0.0.1:8083/incidents

Verify directly in PostgreSQL:

    kubectl exec -n opspulse postgres-0 -- psql -U opspulse -d opspulse -c "SELECT id, title, severity, status FROM incidents;"

Result:

Incident ID 1 was stored successfully.

This Kubernetes database is separate from the Day 33
Docker Compose database.

## 8. Flask self-healing exercise

Delete the application Pod:

    kubectl delete pod -n opspulse -l app=opspulse-app

Watch recovery:

    kubectl get pods -n opspulse -w

Verify:

    kubectl get pods -n opspulse -o wide
    kubectl get deployment opspulse-app -n opspulse

Observed:

Original Pod:

    opspulse-app-77864c7f6-ch27s

Replacement Pod:

    opspulse-app-77864c7f6-hwf2x

Deployment:

    1/1 Ready

Incident ID 1 remained available.

Explanation:

The Deployment's ReplicaSet recreated the missing
application Pod to maintain the desired replica count.

## 9. PostgreSQL StatefulSet recovery

Delete only the PostgreSQL Pod:

    kubectl delete pod postgres-0 -n opspulse

Watch recovery:

    kubectl get pods -n opspulse -w

Verify data:

    kubectl exec -n opspulse postgres-0 -- psql -U opspulse -d opspulse -c "SELECT id, title, severity, status FROM incidents;"

Observed:

PostgreSQL returned as postgres-0.

Incident ID 1 survived.

Explanation:

StatefulSets retain stable Pod identities and reuse
existing persistent storage claims.

This test does not establish multi-node database HA.

## 10. Troubleshooting local port forwarding

Observed error:

    curl: (7) Failed to connect to 127.0.0.1 port 8083

Cause:

No active local forwarding listener was available.

Fix:

    kubectl port-forward -n opspulse svc/opspulse-app 8083:8080 --address 127.0.0.1

Keep the forwarding terminal open while using curl in
another terminal.

## 11. Database-aware readiness improvement

Original configuration:

    livenessProbe  -> /health
    readinessProbe -> /health

Problem:

Flask could report HTTP 200 even when PostgreSQL was
unavailable.

Added to app/app.py:

    GET /ready

The new endpoint executes SELECT 1 through psycopg.

Expected behavior:

    Database available   -> HTTP 200
    Database unavailable -> HTTP 503

Python syntax validation:

    python3 -m py_compile app/app.py

Build updated image:

    docker build -t opspulse:day34 ./app

Load into kind:

    kind load docker-image opspulse:day34 --name opspulse

Verify:

    docker exec opspulse-control-plane crictl images | grep opspulse

Update app.yaml:

    image: opspulse:day34

Probe configuration:

    livenessProbe -> /health
    readinessProbe -> /ready

Apply:

    kubectl apply --dry-run=server -f kubernetes/day34/app.yaml
    kubectl apply -f kubernetes/day34/app.yaml

Watch:

    kubectl rollout status deployment/opspulse-app -n opspulse --timeout=120s

Revision 2 rollout succeeded.

## 12. Simulate database outage

Stop PostgreSQL intentionally:

    kubectl scale statefulset postgres -n opspulse --replicas=0

Observe:

    kubectl get pods -n opspulse
    kubectl describe pod -n opspulse -l app=opspulse-app

Observed warning:

    Readiness probe failed
    context deadline exceeded
    Client.Timeout exceeded while awaiting headers

Interpretation:

The readiness endpoint did not respond within the
configured one-second Kubernetes probe timeout.

This was observed during the controlled database outage.

EndpointSlice check:

    kubectl get endpointslice -n opspulse -l kubernetes.io/service-name=opspulse-app -o jsonpath='{range .items[*].endpoints[*]}address={.addresses} ready={.conditions.ready}{"\n"}{end}'

Observed at the time checked:

    ready=true

Therefore the transition to ready=false was NOT
conclusively captured during this exercise.

Do not describe endpoint removal as verified.

Recover PostgreSQL:

    kubectl scale statefulset postgres -n opspulse --replicas=1
    kubectl rollout status statefulset/postgres -n opspulse --timeout=120s

Recovery verified:

    Flask 1/1 Running
    PostgreSQL 1/1 Running
    GET /ready HTTP 200
    EndpointSlice ready=true
    Incident ID 1 preserved

## 13. Improve readiness timeout

Initial readiness probe timeout:

    1 second

Final lab setting:

    timeoutSeconds: 6
    failureThreshold: 3

Reason:

Avoid premature probe timeout when performing the
PostgreSQL readiness query.

Applied updated manifest:

    kubectl apply --dry-run=server -f kubernetes/day34/app.yaml
    kubectl apply -f kubernetes/day34/app.yaml

Verification:

    kubectl rollout status deployment/opspulse-app -n opspulse --timeout=120s
    kubectl describe deployment opspulse-app -n opspulse

Result:

Deployment Revision 3 successfully rolled out.

Final probe configuration:

    Liveness: /health, timeout 1 second
    Readiness: /ready, timeout 6 seconds

## 14. Final verification

Commands:

    kubectl get nodes
    kubectl get all -n opspulse
    kubectl get pvc -n opspulse
    free -h
    docker ps --format 'table {{.Names}}\t{{.Status}}'

Application endpoint checks:

    kubectl exec -n opspulse deployment/opspulse-app -- python -c "import urllib.request; print('Liveness:', urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=5).status); print('Readiness:', urllib.request.urlopen('http://127.0.0.1:8080/ready',timeout=10).status)"

Observed final state:

    Node: Ready
    Kubernetes version: v1.34.11
    Flask Pod: 1/1 Running
    PostgreSQL Pod: 1/1 Running
    Deployment: 1/1 Available
    StatefulSet: 1/1 Ready
    Liveness: HTTP 200
    Readiness: HTTP 200
    PVC: Bound, 1Gi
    Incident ID 1: preserved
    Container restarts: 0

Final memory snapshot:

    Total RAM: 3.7 GiB
    Used RAM: 2.2 GiB
    Available RAM: 1.6 GiB
    Swap used: 415 MiB

Only the kind control-plane Docker container was running
in the final Docker container audit.

## 15. Important limitations

- Single-node kind is a learning environment.
- Local-path storage is not cross-node durable storage.
- PostgreSQL has one replica, not production HA.
- A Kubernetes Secret is not automatically encrypted at rest.
- A six-second probe timeout is a lab choice, not a universal standard.
- Database-aware readiness may affect availability when PostgreSQL is down.
- The /ready endpoint needs production hardening, including a
  bounded database connection timeout and broader error handling.
- Service endpoint removal during the outage was not verified.
- The Day 33 Docker Compose database and Day 34 Kubernetes
  database contain separate incident records.

## 16. Production troubleshooting challenge

Scenario:

Users report HTTP errors from the incident API.

The Flask process is running, but its Kubernetes Pod
is NotReady.

Investigation commands:

    kubectl get pods -n opspulse
    kubectl describe pod -n opspulse -l app=opspulse-app
    kubectl logs deployment/opspulse-app -n opspulse --tail=50
    kubectl get statefulset postgres -n opspulse
    kubectl get endpointslice -n opspulse -l kubernetes.io/service-name=opspulse-app

Questions:

1. Is the Flask process alive?
2. Is the Pod Ready?
3. Is PostgreSQL reachable?
4. Are Service endpoints ready?
5. Should we restart Flask or repair PostgreSQL first?

## 17. Interview questions

1. What is a Kubernetes Pod?
2. What is the difference between a Deployment and a StatefulSet?
3. Why does Kubernetes need Services?
4. What is a headless Service?
5. What is the difference between a PV and a PVC?
6. What happens when a Deployment Pod is deleted?
7. What happens when a StatefulSet Pod is deleted?
8. What is the difference between liveness and readiness?
9. How do ConfigMaps differ from Secrets?
10. What happens during a rolling update?
11. Why is an application Pod Running but NotReady?
12. How would you troubleshoot database connectivity in Kubernetes?

## 18. Next step

Day 35:

AWS Architecture and Security revision, using the OpsPulse
application architecture as a reference.

Avoid creating chargeable AWS resources unless explicitly
required for the exercise.

Preserve the existing Day 33 Docker volume and Day 34 PVC.
