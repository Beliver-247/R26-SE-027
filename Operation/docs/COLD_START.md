# Cold Start Strategy

## Problem

At initial deployment, the system has no historical Kubernetes metrics. Models need training data to function.

## Solution: Multi-Phase Cold Start

### Phase 1: Pre-Trained Models on Public Data

**What**: Use models pre-trained on public workload datasets

**Public Datasets Used**:
- Azure workload traces
- Google cluster traces
- NIST/academic workload patterns
- Energy consumption baselines

**Location**: `data/public_datasets/`

**Preparation**:
```bash
python scripts/fetch_public_datasets.py
python scripts/train_cold_start_models.py
```

**Models Generated**:
- `models/trained/workload_predictor_v1.pkl`
- `models/trained/carbon_estimator_v1.pkl`
- `models/trained/job_prioritizer_v1.pkl`

### Phase 2: Live Metric Collection

**Timeline**: Days 1-7 of deployment

**What's Happening**:
1. System runs with Phase 1 models
2. Prometheus collects real cluster metrics
3. Metrics stored in `data/collected_metrics/raw/`
4. Features engineered into `data/feature_store/`

**No retraining yet** - system operates on pre-trained models

**Configuration** (in `config/default.yaml`):
```yaml
metric_collection:
  enabled: true
  interval_seconds: 30
  retention_days: 90
```

### Phase 3: Initial Model Retraining (Day 7+)

**Timeline**: After 7 days of historical data collection

**What**:
1. Extract training data from collected metrics (`data/feature_store/`)
2. Retrain all three models with real data
3. Validate model performance
4. Deploy new models if better than Phase 1 models
5. Fall back to Phase 1 models if new models worse (safety)

**Trigger**:
```yaml
model:
  retraining:
    min_historical_days: 7  # Start retraining after 7 days
    interval_hours: 24      # Then retrain daily
```

**Process**:
```bash
# Automatic (runs in background job)
# Or manual:
python scripts/train_cold_start_models.py --use-collected-data
```

**Stored Outputs**:
- New model: `models/trained/workload_predictor_v2.pkl`
- Metadata: Training date, accuracy, data source
- Metrics: `models/metrics/workload_metrics.json`

### Phase 4: Continuous Improvement

**Timeline**: After initial retraining

**What**:
- Weekly/daily retraining with accumulated data
- Model versioning and fallback
- Performance monitoring
- Automatic model roll-forward if improvements detected

## Configuration for Cold Start

**In `.env.example`**:
```bash
# Models
PREDICTION_MODEL_PATH=models/trained/workload_predictor_v1.pkl
CARBON_MODEL_PATH=models/trained/carbon_estimator_v1.pkl
JOB_PRIORITIZER_MODEL_PATH=models/trained/job_prioritizer_v1.pkl

# Data collection
METRIC_COLLECTION_INTERVAL=30
DATA_RETENTION_DAYS=90

# Retraining
RETRAINING_INTERVAL_HOURS=24
MIN_HISTORICAL_DAYS_FOR_RETRAINING=7
```

**In `config/default.yaml`**:
```yaml
cold_start:
  enabled: true
  use_public_datasets: true
  public_dataset_path: data/public_datasets/
  transition_to_live_data_days: 7

metric_collection:
  enabled: true
  interval_seconds: 30
  storage_path: data/collected_metrics/

model_retraining:
  enabled: true
  min_historical_days: 7
  interval_hours: 24
  fallback_on_error: true
  keep_historical_versions: 3

feature_engineering:
  window_size_seconds: 300
  lag_features: [30, 60, 120, 300]
```

## Deployment Timeline

```
Day 0 (Deployment)
├─ Load pre-trained models (public data)
├─ Start Prometheus metric collection
├─ API operational with Phase 1 models
└─ Background job: collect metrics every 30s

Days 1-7
├─ System using public-data models
├─ Real metrics accumulated in data/collected_metrics/
├─ Feature engineering running continuously
└─ NO retraining yet

Day 7+
├─ Background job: Retrain with 7 days of real data
├─ Compare new models vs. public-data models
├─ If better → deploy new models
│  ├─ Update models/trained/workload_predictor_v2.pkl
│  ├─ Update config to use v2
│  └─ Keep v1 as fallback
└─ If worse → keep using v1, try again tomorrow

Ongoing
├─ Daily retraining with rolling window
├─ Continuous metric collection
├─ Automated model versioning
└─ Performance monitoring and alerting
```

## Failure Modes & Safeguards

### Model Retraining Fails
- **Fallback**: Continue using previous best model
- **Alert**: Logged but doesn't break system
- **Retry**: Attempts again tomorrow

### Prediction Quality Degrades
- **Detection**: MAE threshold exceeded
- **Action**: Revert to previous model version
- **Alert**: Alert in Prometheus

### No Historical Data Available
- **Action**: Continue with pre-trained models
- **Duration**: Indefinite if data collection disabled
- **Recovery**: Re-enable collection, wait 7+ days

### Prometheus Unavailable
- **Action**: Use cached metrics for 1 hour
- **After 1 hour**: Predictions degrade gracefully
- **Recovery**: Restart once Prometheus available

## Monitoring Cold Start Health

### Metrics to Watch

```bash
# Check data collection
curl http://localhost:8000/metrics | grep "collected_metrics"

# Check model performance
curl http://localhost:8000/metrics | grep "model_accuracy"

# Check prediction quality
kubectl logs -n green-devops -l app=operation-phase | grep "MAE\|RMSE"
```

### Grafana Dashboard

Dashboard: `monitoring/grafana/dashboards/cold_start_health.json`

Shows:
- Historical data accumulated (days)
- Model accuracy (public vs. real)
- Prediction errors over time
- Retraining status

## Best Practices

1. **Before Deployment**:
   - Run `python scripts/fetch_public_datasets.py`
   - Run `python scripts/train_cold_start_models.py`
   - Verify models exist in `models/trained/`

2. **First 7 Days**:
   - Monitor system logs
   - Check Prometheus is scraping metrics
   - Verify no errors in metric collection

3. **Day 7+**:
   - Monitor retraining logs
   - Check model accuracy improvements
   - Verify predictions match reality

4. **Ongoing**:
   - Keep historical models as fallback
   - Monitor drift in predictions
   - Regular manual validation of key decisions

## Troubleshooting

### "No data in collected_metrics"
```bash
# Check Prometheus connection
python -c "from src.data_layer.prometheus_client import PrometheusClient; PrometheusClient().ping()"

# Check collection job is running
kubectl logs -n green-devops -l job-type=metric-collection
```

### Models not retraining
```bash
# Check retraining job
kubectl logs -n green-devops -l job-type=retraining

# Manually trigger
python scripts/train_cold_start_models.py --use-collected-data
```

### Predictions poor quality
```bash
# Check feature engineering
python -c "
from src.data_layer.feature_engineer import FeatureEngineer
fe = FeatureEngineer()
features = fe.get_latest_features()
print('Latest features:', features)
"

# Compare with public dataset distributions
python scripts/analyze_distribution_shift.py
```

## References

- Public Datasets: See `data/public_datasets/README.md`
- Feature Engineering: See `src/data_layer/feature_engineer.py`
- Retraining Logic: See `src/background_jobs/retraining_job.py`
