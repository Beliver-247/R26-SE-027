# Kubernetes Manifests

This directory contains Kubernetes YAML manifests for deploying the Green DevOps Operation Component.

## Files

- `namespace.yaml` - Kubernetes namespace
- `deployment.yaml` - Main application deployment
- `service.yaml` - Service for component  
- `configmap.yaml` - Configuration data
- `secrets.yaml` - Sensitive data
- `rbac.yaml` - Service account and roles
- `prometheus_scrape.yaml` - Prometheus scrape config

## Deployment

```bash
# Apply all manifests
kubectl apply -f k8s_manifests/

# Or individual files
kubectl apply -f k8s_manifests/namespace.yaml
kubectl apply -f k8s_manifests/configmap.yaml
kubectl apply -f k8s_manifests/deployment.yaml
```

## Verification

```bash
# Check deployment
kubectl get deployment -n green-devops

# Check pods
kubectl get pods -n green-devops

# Check logs
kubectl logs -f -n green-devops -l app=operation-phase
```

## Customization

Edit manifests to match your environment:
- Image registry and tag
- Resource limits
- Environment variables
- Volume mounts
- Node selectors
