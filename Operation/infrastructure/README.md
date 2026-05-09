# Infrastructure Directory

This directory contains Infrastructure as Code for deploying the Green DevOps Operation Component.

## Structure

- `terraform/` - Terraform configuration for cloud infrastructure
- `k8s_manifests/` - Kubernetes YAML manifests
- `docker/` - Docker configuration and docker-compose
- `helm/` - Helm chart for Kubernetes deployment

## Deployment Methods

### 1. Using Terraform
```bash
cd terraform
terraform init
terraform plan -var-file=environments/prod.tfvars
terraform apply -var-file=environments/prod.tfvars
```

### 2. Using Kubernetes Manifests
```bash
kubectl apply -f k8s_manifests/
kubectl get pods -n green-devops
```

### 3. Using Helm Chart
```bash
helm install operation-phase ./helm/ -f helm/values-prod.yaml -n green-devops
```

### 4. Using Docker Compose (Development)
```bash
docker-compose -f docker/docker-compose.yaml up
```

## Prerequisites

- Terraform (for Terraform deployment)
- kubectl configured with cluster access
- Helm 3+ (for Helm deployment)
- Docker & Docker Compose (for local dev)

## Configuration

See `terraform/environments/` for environment-specific configurations.

## Next Steps

1. Edit Terraform variables in `terraform/environments/prod.tfvars`
2. Update K8s manifests in `k8s_manifests/` for your environment
3. Customize Helm values in `helm/values-prod.yaml`
4. Follow deployment guide in `docs/DEPLOYMENT.md`
