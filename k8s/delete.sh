#!/bin/bash

echo "Deleting Todo App from Kubernetes..."
echo ""

kubectl delete -f consumer.yaml
kubectl delete -f app.yaml
kubectl delete -f rabbitmq.yaml
kubectl delete -f postgres.yaml
kubectl delete -f configmap.yaml
kubectl delete -f namespace.yaml

echo ""
echo "All resources deleted!"
