# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Todo App on Minikube.

## Prerequisites

- Minikube installed and running
- kubectl configured to work with Minikube
- Docker image pushed to Docker Hub: `haykhayrapetyan09/simple-todo-app:latest`

## Quick Deploy

```bash
# Make sure Minikube is running
minikube start

# Deploy everything
chmod +x deploy.sh
./deploy.sh

# Get the service URL
minikube service todo-app-service -n todo-app --url
```

## Manual Deployment

If you prefer to deploy manually:

```bash
# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Create ConfigMap and Secrets
kubectl apply -f configmap.yaml

# 3. Deploy PostgreSQL
kubectl apply -f postgres.yaml

# 4. Deploy RabbitMQ
kubectl apply -f rabbitmq.yaml

# 5. Wait for database and message queue
kubectl wait --for=condition=ready pod -l app=postgres -n todo-app --timeout=120s
kubectl wait --for=condition=ready pod -l app=rabbitmq -n todo-app --timeout=120s

# 6. Deploy Flask App
kubectl apply -f app.yaml

# 7. Deploy Consumer
kubectl apply -f consumer.yaml

# 8. Check status
kubectl get pods -n todo-app

# 9. Access the application
minikube service todo-app-service -n todo-app
```

## Resources Created

- **Namespace**: `todo-app`
- **ConfigMap**: `todo-config` - environment variables
- **Secret**: `todo-secrets` - sensitive data (passwords)
- **PVC**: `postgres-pvc` - 1Gi storage for PostgreSQL
- **Deployments**:
  - `postgres` (1 replica)
  - `rabbitmq` (1 replica)
  - `todo-app` (2 replicas)
  - `todo-consumer` (1 replica)
- **Services**:
  - `postgres-service` (ClusterIP:5432)
  - `rabbitmq-service` (ClusterIP:5672)
  - `todo-app-service` (NodePort:30000)

## Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n todo-app

# Expected output:
# NAME                            READY   STATUS    RESTARTS   AGE
# postgres-xxxxx                  1/1     Running   0          2m
# rabbitmq-xxxxx                  1/1     Running   0          2m
# todo-app-xxxxx                  1/1     Running   0          1m
# todo-app-xxxxx                  1/1     Running   0          1m
# todo-consumer-xxxxx             1/1     Running   0          1m

# Check services
kubectl get svc -n todo-app

# View logs
kubectl logs -f -l app=todo-consumer -n todo-app
```

## Access the Application

```bash
# Get the URL
minikube service todo-app-service -n todo-app --url

# Or open in browser directly
minikube service todo-app-service -n todo-app
```

The app will be accessible at `http://<minikube-ip>:30000`

## Testing

1. Open the application URL in your browser
2. Add some tasks
3. Complete and delete tasks
4. Watch the consumer logs to see event processing:
   ```bash
   kubectl logs -f -l app=todo-consumer -n todo-app
   ```

## Scaling

Scale the Flask app to handle more traffic:

```bash
# Scale to 3 replicas
kubectl scale deployment todo-app --replicas=3 -n todo-app

# Verify
kubectl get pods -n todo-app
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl get pods -n todo-app

# Describe problematic pod
kubectl describe pod <pod-name> -n todo-app

# Check logs
kubectl logs <pod-name> -n todo-app
```

### Database connection issues

```bash
# Check if PostgreSQL is running
kubectl get pods -l app=postgres -n todo-app

# Check PostgreSQL logs
kubectl logs -l app=postgres -n todo-app

# Verify service
kubectl get svc postgres-service -n todo-app
```

### RabbitMQ connection issues

```bash
# Check RabbitMQ status
kubectl get pods -l app=rabbitmq -n todo-app

# Check logs
kubectl logs -l app=rabbitmq -n todo-app
```

### Image pull issues

If the app can't pull the Docker image:

```bash
# Make sure the image is pushed to Docker Hub
docker push haykhayrapetyan09/simple-todo-app:latest

# Or build and load into Minikube
eval $(minikube docker-env)
docker build -t haykhayrapetyan09/simple-todo-app:latest ..
```

## Cleanup

```bash
# Delete all resources
./delete.sh

# Or delete the namespace (removes everything)
kubectl delete namespace todo-app

# Verify cleanup
kubectl get all -n todo-app
```

## Notes

- The app uses NodePort service type, accessible on port 30000
- PostgreSQL data persists in a PersistentVolume
- ConfigMap stores non-sensitive configuration
- Secrets store sensitive data (passwords)
- The consumer and app use the same Docker image but different commands
