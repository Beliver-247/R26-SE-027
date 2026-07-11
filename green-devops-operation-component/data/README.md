# Data Directory

This directory contains all data used by the system:

## Structure

- `public_datasets/` - Public workload traces and energy profiles for cold-start training
- `collected_metrics/` - Runtime metrics collected from Prometheus after deployment
- `feature_store/` - Engineered features ready for model training

## Cold-Start Datasets

The `public_datasets/` directory contains:
- Azure workload traces
- Google cluster traces
- Energy consumption baselines
- NIST workload patterns

Download using:
```bash
python scripts/fetch_public_datasets.py
```

## Collected Metrics

Post-deployment, `collected_metrics/` stores:
- Raw metric dumps from Prometheus (JSON format)
- Processed time-series data (Parquet format)
- Feature-engineered data for model training

## Feature Store

`feature_store/` contains:
- `workload_features.parquet` - Extracted workload patterns
- `carbon_scenarios.parquet` - Calculated carbon impact scenarios
- `job_priority_data.csv` - Labeled job priority data

These are generated via feature engineering pipeline and used for model training.

## Data Lifecycle

1. **Collection**: Prometheus → collected_metrics/raw/
2. **Processing**: Preprocessing pipeline cleans and normalizes
3. **Feature Engineering**: Features extracted into feature_store/
4. **Training**: Models trained on feature_store data
5. **Archival**: Old data archived after DATA_RETENTION_DAYS

## Usage in Code

```python
from src.data_layer import prometheus_client, data_preprocessor
from src.data_layer import feature_engineer

# Collect metrics
metrics = prometheus_client.collect_metrics()

# Preprocess
clean_data = data_preprocessor.preprocess(metrics)

# Engineer features
features = feature_engineer.engineer_features(clean_data)

# Use for training or inference
```
