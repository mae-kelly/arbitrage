#!/bin/bash
# Kubernetes deployment script

set -e

ENVIRONMENT=${1:-staging}
NAMESPACE="arbitrage-system"

echo "🚀 Deploying to $ENVIRONMENT environment..."

# Build and push images
echo "🏗️ Building Docker images..."
docker build -t arbitrage-bot:latest .
docker build -t ml-server:latest -f inference_engine/Dockerfile inference_engine/

# Tag for registry (replace with your registry)
# docker tag arbitrage-bot:latest your-registry/arbitrage-bot:latest
# docker push your-registry/arbitrage-bot:latest

# Apply Kubernetes manifests
echo "☸️ Applying Kubernetes manifests..."
kubectl apply -k k8s/overlays/$ENVIRONMENT

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/arbitrage-bot -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/ml-server -n $NAMESPACE

# Show status
echo "📊 Deployment status:"
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE

echo "✅ Deployment complete!"
echo "📝 Access Grafana: kubectl port-forward service/grafana 3000:3000 -n $NAMESPACE"
echo "📝 Access Prometheus: kubectl port-forward service/prometheus 9090:9090 -n $NAMESPACE"
