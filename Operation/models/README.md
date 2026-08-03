# Models Directory

This directory stores trained models, feature scalers, and evaluation metrics.

## Structure

- `trained/` - Production model artifacts (pickled models)
- `scalers/` - Feature scaling/encoding objects
- `metrics/` - Model evaluation results

## Trained Models

### Workload Predictor
- **File**: `trained/workload_predictor_v1.pkl`
- **Type**: LSTM time-series model
- **Input**: Historical workload metrics (30 features)
- **Output**: Predicted pod count for next 30 seconds
- **Accuracy**: See `metrics/workload_metrics.json`

### Carbon Estimator
- **File**: `trained/carbon_estimator_v1.pkl`
- **Type**: Linear/non-linear regression model
- **Input**: Resource specifications, energy source
- **Output**: Carbon emissions in grams CO2e

### Job Prioritizer
- **File**: `trained/job_prioritizer_v1.pkl`
- **Type**: Classification model
- **Input**: Job metadata (type, duration, deadline)
- **Output**: Priority classification (critical/important/delayable)

## Feature Scalers

Scalers maintain model input distribution:
- `scalers/workload_scaler.pkl` - StandardScaler for workload features
- `scalers/carbon_encoder.pkl` - OneHotEncoder for categorical features
- `scalers/job_encoder.pkl` - Encoder for job features

## Model Loading

```python
import pickle

# Load model
with open('models/trained/workload_predictor_v1.pkl', 'rb') as f:
    model = pickle.load(f)

# Load scaler
with open('models/scalers/workload_scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# Make prediction
features_scaled = scaler.transform(features)
prediction = model.predict(features_scaled)
```

## Model Versioning

Models are versioned: `v1.0`, `v1.1`, etc.
- Keep historical versions for fallback
- Store metadata: training date, accuracy, dataset source
- See `metrics/` for version comparison

## Model Retraining

Models are automatically retrained when:
- 7+ days of historical data collected
- Scheduled daily (after initial 7-day period)
- Manual retraining via `scripts/train_cold_start_models.py --use-collected-data`

New models are tested and rolled forward only if performance improves.

## Size Estimates

- Workload predictor: ~50 MB
- Carbon estimator: ~10 MB
- Job prioritizer: ~5 MB
- Scalers: ~2 MB total

Total: ~70 MB
