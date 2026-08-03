# Troubleshooting Guide

## Common Issues

### Deployment Issues

#### Pod fails to start: ImagePullBackOff

**Problem**: Docker image not found or not accessible.

**Solutions**:
```bash
# Check image exists
docker images | grep green-devops

# If not found, build it
docker build -f infrastructure/docker/Dockerfile -t green-devops-operation:latest .

# If using registry, verify credentials
kubectl get secrets -n green-devops
```

#### Pod crashes: CrashLoopBackOff

**Problem**: Application exits immediately on startup.

**Solutions**:
```bash
# Check logs
kubectl logs -n green-devops -l app=operation-phase

# Common causes:
# 1. Config file not found
kubectl get configmap -n green-devops

# 2. Models not found
kubectl exec -it -n green-devops <pod-name> -- ls models/trained/

# 3. Environment variables missing
kubectl get pods -o yaml -n green-devops | grep env -A 10
```

#### Pod not reaching Ready state

**Problem**: Liveness/readiness probes failing.

**Solutions**:
```bash
# Check probe configuration
kubectl get deployment operation-phase -n green-devops -o yaml | grep -A 5 "livenessProbe"

# Test probe manually
kubectl port-forward svc/operation-phase -n green-devops 8000:8000
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

---

### Metrics & Data Collection Issues

#### No metrics in Prometheus

**Problem**: Prometheus not collecting metrics.

**Solutions**:
```bash
# Verify Prometheus service URL
echo $PROMETHEUS_URL
curl $PROMETHEUS_URL/api/v1/query?query=up

# Check if operation-phase is registered target
curl $PROMETHEUS_URL/api/v1/targets | grep operation-phase

# Check pod metrics endpoint
kubectl port-forward svc/operation-phase -n green-devops 8000:8000
curl http://localhost:8000/metrics
```

#### Prometheus connection fails

**Problem**: Cannot reach Prometheus server.

**Solutions**:
```bash
# Test network connectivity
kubectl exec -it -n green-devops <pod-name> -- \
  curl http://prometheus:9090/api/v1/targets

# Check DNS resolution
kubectl exec -it -n green-devops <pod-name> -- \
  nslookup prometheus

# Update Prometheus URL in config
kubectl edit configmap operation-phase-config -n green-devops
```

#### Historical data not being collected

**Problem**: `data/collected_metrics/` is empty.

**Solutions**:
```bash
# Check metric collection job is running
kubectl get cronjob -n green-devops
kubectl logs -n green-devops -l job-type=metric-collection

# Check data path configuration
kubectl get cm operation-phase-config -n green-devops -o yaml | grep "collected_metrics"

# Manually trigger collection
kubectl exec -it -n green-devops <pod-name> -- \
  python -m src.background_jobs.metrics_collection_job
```

---

### Model & Prediction Issues

#### Models not found

**Problem**: Models not loading at startup.

**Solutions**:
```bash
# Verify models exist in container
kubectl exec -it -n green-devops <pod-name> -- \
  ls -la models/trained/

# If missing, download datasets and train
kubectl exec -it -n green-devops <pod-name> -- \
  python scripts/fetch_public_datasets.py

kubectl exec -it -n green-devops <pod-name> -- \
  python scripts/train_cold_start_models.py

# Copy models back to container (if needed)
kubectl cp models/trained/workload_predictor_v1.pkl \
  green-devops/<pod-name>:/app/models/trained/
```

#### Poor prediction accuracy

**Problem**: MAE/RMSE metrics are very high.

**Solutions**:
```bash
# Check model metadata
python -c "
import pickle
with open('models/trained/workload_predictor_v1.pkl', 'rb') as f:
    model = pickle.load(f)
    print('Model:', model)
"

# Compare with public dataset distributions
python scripts/analyze_distribution_shift.py

# Check feature engineering
python -c "
from src.data_layer.feature_engineer import FeatureEngineer
fe = FeatureEngineer()
features = fe.get_latest_features()
print('Features shape:', features.shape)
print('Features values:', features.describe())
"

# Retrain model with current data
python scripts/train_cold_start_models.py --use-collected-data --force
```

#### Model retraining not happening

**Problem**: Models not being updated after 7 days.

**Solutions**:
```bash
# Check retraining job
kubectl get cronjob -n green-devops | grep retraining

# Check job history
kubectl get jobs -n green-devops | grep retraining

# Check retraining logs
kubectl logs -n green-devops -l job-type=retraining

# Manually trigger retraining
kubectl exec -it -n green-devops <pod-name> -- \
  python -m src.background_jobs.retraining_job

# Check if data old enough
python -c "
import os
from datetime import datetime, timedelta
raw_metrics = 'data/collected_metrics/raw/'
files = os.listdir(raw_metrics)
if files:
    first_file = min(files)
    print(f'Oldest metric: {first_file}')
else:
    print('No metrics collected yet')
"
```

---

### Kubernetes Integration Issues

#### Cannot scale pods

**Problem**: /decide/scaling returns error or doesn't execute.

**Solutions**:
```bash
# Check RBAC permissions
kubectl get rolebinding -n green-devops
kubectl describe rolebinding operation-phase-scaling -n green-devops

# Verify service account
kubectl get sa -n green-devops
kubectl get clusterrole operation-phase-scaler

# Test K8s API access
kubectl exec -it -n green-devops <pod-name> -- \
  python -c "
from kubernetes import client, config
config.load_incluster_config()
apps = client.AppsV1Api()
deployments = apps.list_deployment_for_all_namespaces()
print(f'Found {len(deployments.items)} deployments')
"

# Check if target deployment exists
kubectl get deployment <deployment-name> -n <namespace>

# Manually check API connection
kubectl logs -n green-devops | grep -i "kubernetes\|k8s\|api"
```

#### Pod scaling doesn't take effect

**Problem**: /decide/scaling succeeds but pods don't change.

**Solutions**:
```bash
# Check if decision was executed
kubectl logs -n green-devops -l app=operation-phase | grep "scaling_executed"

# Check actual pod count
kubectl get pods -n <namespace> -l <label>

# Check deployment update
kubectl describe deployment <name> -n <namespace>

# Verify HPA not interfering
kubectl get hpa -n <namespace>

# Check deployment configuration
kubectl get deployment <name> -n <namespace> -o yaml | grep -A 5 "replicas"
```

---

### Job Prioritization Issues

#### Jobs not being delayed

**Problem**: All jobs marked as critical, none delayed.

**Solutions**:
```bash
# Check job policies configuration
kubectl get cm operation-phase-config -n green-devops -o yaml | grep -A 20 "job_policies"

# Verify job metadata (labels/annotations)
kubectl get jobs -n <namespace> -o yaml | grep -E "labels:|annotations:" -A 3

# Test job prioritizer
python -c "
from src.job_prioritization_engine.prioritizer import Prioritizer
prioritizer = Prioritizer()
result = prioritizer.prioritize({
    'job_id': 'test-001',
    'job_type': 'batch_processing'
})
print(result)
"

# Check if jobs tracked
kubectl logs -n green-devops | grep "job_prioritization"
```

#### Unfair job delays

**Problem**: Some jobs always delayed, others never.

**Solutions**:
```bash
# Check fairness metrics
curl http://localhost:8000/metrics | grep fairness

# Review job priorities in logs
kubectl logs -n green-devops | grep "job.*priority"

# Check queue state
kubectl exec -it -n green-devops <pod-name> -- \
  python -c "
from src.job_prioritization_engine.queue_manager import JobQueueManager
manager = JobQueueManager()
queued = manager.get_queued_jobs()
print(f'Queued jobs: {len(queued)}')
for job in queued[:5]:
    print(f'  {job[\"job_id\"]}: delayed {job[\"delay_time_sec\"]}s')
"

# Adjust fairness rules in config
kubectl edit cm operation-phase-config -n green-devops
```

---

### API Issues

#### API not responding

**Problem**: Cannot reach running API service.

**Solutions**:
```bash
# Check service status
kubectl get svc -n green-devops

# Port forward
kubectl port-forward svc/operation-phase -n green-devops 8000:8000

# Test locally
curl http://localhost:8000/health

# Check pod logs
kubectl logs -f -n green-devops -l app=operation-phase | tail -20

# Check service selectors
kubectl get svc operation-phase -n green-devops -o yaml | grep -A 5 "selector"
```

#### Slow API responses

**Problem**: API requests taking >500ms.

**Solutions**:
```bash
# Check latency metrics
curl http://localhost:8000/metrics | grep "duration"

# Check resource usage
kubectl top pod -n green-devops -l app=operation-phase

# Check Prometheus query performance
curl -X GET "http://prometheus:9090/api/v1/query?query=node_up" --verbose

# Increase pod resources
kubectl set resources deployment operation-phase -n green-devops \
  --limits=cpu=2,memory=4Gi \
  --requests=cpu=500m,memory=1Gi

# Scale to multiple replicas
kubectl scale deployment operation-phase -n green-devops --replicas=3
```

#### 500 Internal Server Error

**Problem**: API endpoints returning errors.

**Solutions**:
```bash
# Check pod logs
kubectl logs -n green-devops -l app=operation-phase --tail=50

# Look for exceptions
kubectl logs -n green-devops -l app=operation-phase | grep -i "exception\|error\|traceback"

# Enable debug logging
kubectl set env deployment/operation-phase -n green-devops LOG_LEVEL=DEBUG

# Check dependencies
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Restart pod
kubectl delete pod -n green-devops -l app=operation-phase
```

---

### Configuration Issues

#### Configuration not updating

**Problem**: Changes to config files don't take effect.

**Solutions**:
```bash
# Reload configuration without restart
curl -X POST http://localhost:8000/admin/reload-config

# Or restart pod
kubectl delete pod -n green-devops -l app=operation-phase

# Or rolling update
kubectl rollout restart deployment/operation-phase -n green-devops

# Verify new config loaded
curl http://localhost:8000/admin/config
```

#### Invalid configuration

**Problem**: "Config validation failed" error.

**Solutions**:
```bash
# Check syntax
python -c "import yaml; yaml.safe_load(open('config/default.yaml'))"

# Validate schema
python -c "
from src.shared.config import load_config
try:
    config = load_config()
    print('Config valid')
except Exception as e:
    print(f'Config error: {e}')
"

# Check specific file
kubectl exec -it -n green-devops <pod-name> -- \
  python -c "
import yaml
with open('config/default.yaml') as f:
    print(yaml.safe_load(f))
"
```

---

### Performance Issues

#### High CPU usage

**Problem**: Pod using 100% CPU.

**Solutions**:
```bash
# Check top consuming processes
kubectl exec -it -n green-devops <pod-name> -- top

# Check model inference time
curl http://localhost:8000/metrics | grep prediction_duration

# Profile code
pip install py-spy
py-spy record -o profile.svg -- kubectl exec -it -n green-devops <pod-name> -- python ...

# Reduce feature computation frequency
kubectl edit cm operation-phase-config -n green-devops
# Increase METRIC_COLLECTION_INTERVAL
```

#### High memory usage

**Problem**: Pod using large amounts of memory.

**Solutions**:
```bash
# Check memory growth
kubectl top pod -n green-devops -l app=operation-phase

# Check for memory leaks
kubectl exec -it -n green-devops <pod-name> -- \
  python -c "import tracemalloc; tracemalloc.start()"

# Reduce historical data retention
kubectl set env deployment/operation-phase -n green-devops DATA_RETENTION_DAYS=30

# Increase pod memory limits
kubectl set resources deployment/operation-phase -n green-devops \
  --limits=memory=4Gi
```

---

### Log Analysis

#### Finding errors in logs

```bash
# Show only errors
kubectl logs -n green-devops -l app=operation-phase | grep -E "ERROR|CRITICAL|Exception"

# Show last 100 lines
kubectl logs -n green-devops -l app=operation-phase --tail=100

# Follow logs in real-time
kubectl logs -f -n green-devops -l app=operation-phase

# Search specific time range
kubectl logs -n green-devops -l app=operation-phase --since=1h

# Export logs to file
kubectl logs -n green-devops -l app=operation-phase > logs/pod-debug.log
```

---

## Getting Help

1. **Check logs**: `kubectl logs -n green-devops -l app=operation-phase`
2. **Check status**: `kubectl get pods -n green-devops`
3. **Check events**: `kubectl describe pod -n green-devops <pod-name>`
4. **Check metrics**: `curl http://localhost:8000/health`
5. **Review docs**: Check relevant documentation file
6. **Check config**: `kubectl get cm -n green-devops`

### Debug Mode

Enable debug mode for verbose logging:

```bash
kubectl set env deployment/operation-phase -n green-devops LOG_LEVEL=DEBUG
kubectl rollout restart deployment/operation-phase -n green-devops
kubectl logs -f -n green-devops -l app=operation-phase
```

### Support Resources

- Architecture: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- Deployment: [docs/DEPLOYMENT.md](DEPLOYMENT.md)
- API: [docs/API.md](API.md)
- Cold Start: [docs/COLD_START.md](COLD_START.md)
