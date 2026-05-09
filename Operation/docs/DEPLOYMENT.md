# Deployment Guide

## Prerequisites

- **Kubernetes cluster** (local or cloud)
- **Prometheus** for metrics collection
- **Python 3.9+**
- **Docker** (for containerization)
- **kubectl** configured with cluster access
- **Terraform** (optional, for infrastructure provisioning)

## Installation Steps

### 1. Prepare Environment

```bash
# Clone repository
git clone <repo>
cd green-devops-operation-component

# Create Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download Cold-Start Datasets

```bash
# Fetch public workload traces and energy profiles
python scripts/fetch_public_datasets.py

# This downloads datasets to data/public_datasets/
```

### 3. Train Initial Models

```bash
# Train models on public datasets
python scripts/train_cold_start_models.py

# Models will be saved to models/trained/
# Scalers will be saved to models/scalers/
```

### 4. Configure System

Edit configuration files in `config/`:

```yaml
# config/default.yaml
environment: prod
kubernetes:
  namespace: green-devops
  service_account: operation-phase

# config/carbon_config.yaml
carbon_rates:
  default_gco2e_per_kwh: 0.4
  pue_factor: 1.2

# config/sla_config.yaml
sla_thresholds:
  response_time_ms: 100
  cpu_utilization: 0.8

# config/scaling_config.yaml
scaling:
  min_replicas: 1
  max_replicas: 20
  scale_up_threshold_percent: 70
  scale_down_threshold_percent: 30
```

### 5. Build Docker Image

```bash
# Build image
docker build -f infrastructure/docker/Dockerfile -t green-devops-operation:latest .

# (Optional) Push to registry
docker tag green-devops-operation:latest myregistry/green-devops-operation:latest
docker push myregistry/green-devops-operation:latest
```

### 6. Deploy to Kubernetes

#### Option A: Using kubectl directly

```bash
# Create namespace
kubectl create namespace green-devops

# Create ConfigMaps for configuration
kubectl create configmap operation-config \
  --from-file=config/default.yaml \
  --from-file=config/carbon_config.yaml \
  --from-file=config/sla_config.yaml \
  --from-file=config/scaling_config.yaml \
  --from-file=config/job_policies.yaml \
  -n green-devops

# Create ServiceAccount and RBAC
kubectl apply -f infrastructure/k8s_manifests/rbac.yaml

# Deploy the component
kubectl apply -f infrastructure/k8s_manifests/deployment.yaml
kubectl apply -f infrastructure/k8s_manifests/service.yaml

# Verify deployment
kubectl get pods -n green-devops
kubectl logs -n green-devops -l app=operation-phase -f
```

#### Option B: Using Helm

```bash
# Install using Helm
helm install operation-phase \
  ./infrastructure/helm/ \
  -n green-devops \
  -f infrastructure/helm/values-prod.yaml

# Verify
helm list -n green-devops
kubectl get pods -n green-devops
```

#### Option C: Using Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Review changes
terraform plan -var-file=environments/prod.tfvars

# Apply
terraform apply -var-file=environments/prod.tfvars
```

### 7. Verify Deployment

```bash
# Check if pod is running
kubectl get pods -n green-devops

# Check logs
kubectl logs -n green-devops -l app=operation-phase

# Test health endpoint
kubectl port-forward -n green-devops svc/operation-phase 8000:8000
curl http://localhost:8000/health

# Test API
curl http://localhost:8000/api/v1/predict
```

### 8. Configure Prometheus Scraping

Add to Prometheus config:

```yaml
scrape_configs:
  - job_name: 'operation-phase'
    static_configs:
      - targets: ['operation-phase:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

Then reload Prometheus:

```bash
kubectl rollout restart -n monitoring deployment/prometheus
```

### 9. Import Grafana Dashboards

```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Visit http://localhost:3000
# Login with default credentials
# Import dashboards from monitoring/grafana/dashboards/
```

## Configuration Details

### Environment-Specific Settings

Create environment-specific config overrides:

```bash
config/
├── default.yaml      # Base config
├── dev.yaml          # Development overrides
├── prod.yaml         # Production overrides
└── staging.yaml      # Staging overrides
```

Load via environment variable:
```bash
export ENVIRONMENT=prod
python -m src.api.main
```

### Carbon Calculation Parameters

Edit `config/carbon_config.yaml`:

```yaml
carbon_rates:
  # grams CO2 per kWh (varies by region/energy source)
  us_average: 0.385
  eu_average: 0.238
  asia_average: 0.520

pue_factors:
  # Power Usage Effectiveness by data center
  standard_datacenter: 1.5
  efficient_datacenter: 1.1
  hyperscale_cloud: 1.08
```

### SLA Configuration

Edit `config/sla_config.yaml`:

```yaml
sla:
  response_time_ms: 100
  availability_percent: 99.9
  cpu_threshold_percent: 80
  memory_threshold_percent: 85
  
  # Scale up when metrics exceed thresholds
  scale_up_threshold: 70
  scale_down_threshold: 20
```

### Scaling Rules

Edit `config/scaling_config.yaml`:

```yaml
scaling:
  min_replicas: 1
  max_replicas: 50
  
  # Behavior
  scale_up_percent_per_decision: 25
  scale_down_percent_per_decision: 25
  
  # Stabilization
  scale_up_stabilization_minutes: 5
  scale_down_stabilization_minutes: 10
```

## Troubleshooting

### Pod not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n green-devops

# Check logs
kubectl logs <pod-name> -n green-devops

# Common issues:
# - Config not found: Verify ConfigMap is created
# - Model not found: Verify models/trained/ directory
# - K8s API access: Check RBAC and ServiceAccount
```

### Metrics not collecting

```bash
# Check Prometheus scraping
# Visit http://prometheus:9090/targets

# Check if operation-phase appears and is "UP"
# If "DOWN", check:
# - Service DNS: operation-phase.green-devops.svc.cluster.local
# - Port: 8000
# - Metrics endpoint: /metrics
```

### High latency

```bash
# Check resource usage
kubectl top pod <pod-name> -n green-devops

# If high CPU:
# - Check model loading time
# - Reduce prediction frequency
# - Use simpler model (ARIMA instead of LSTM)

# If high memory:
# - Reduce historical data retention
# - Implement metric caching cleanup
```

## Updating the Component

```bash
# Update image
docker build -f infrastructure/docker/Dockerfile -t green-devops-operation:new-version .

# Roll out new version
kubectl set image deployment/operation-phase \
  operation-phase=green-devops-operation:new-version \
  -n green-devops

# Monitor rollout
kubectl rollout status deployment/operation-phase -n green-devops
```

## Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/operation-phase -n green-devops

# Check rollout history
kubectl rollout history deployment/operation-phase -n green-devops

# Rollback to specific revision
kubectl rollout undo deployment/operation-phase --to-revision=2 -n green-devops
```

## Uninstalling

```bash
# Using kubectl
kubectl delete namespace green-devops

# Using Helm
helm uninstall operation-phase -n green-devops

# Using Terraform
cd infrastructure/terraform
terraform destroy -var-file=environments/prod.tfvars
```
