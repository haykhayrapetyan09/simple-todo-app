#!/bin/bash

echo "Deploying Todo App to Kubernetes..."
echo ""

# Apply namespace
echo "Creating namespace..."
kubectl apply -f namespace.yaml

# Apply configmap and secrets
echo "Creating ConfigMap and Secrets..."
kubectl apply -f configmap.yaml

# Apply PostgreSQL
echo "Deploying PostgreSQL..."
kubectl apply -f postgres.yaml

# Apply RabbitMQ
echo "Deploying RabbitMQ..."
kubectl apply -f rabbitmq.yaml

# Wait for database and message queue to be ready
echo "Waiting for PostgreSQL and RabbitMQ to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n todo-app --timeout=120s
kubectl wait --for=condition=ready pod -l app=rabbitmq -n todo-app --timeout=120s

# Apply Flask App
echo "Deploying Flask App..."
kubectl apply -f app.yaml

# Apply Consumer
echo "Deploying Consumer..."
kubectl apply -f consumer.yaml

echo ""
echo "Deployment complete!"
echo ""
echo "Check status with: kubectl get pods -n todo-app"
echo "Get service URL with: minikube service todo-app-service -n todo-app --url"
