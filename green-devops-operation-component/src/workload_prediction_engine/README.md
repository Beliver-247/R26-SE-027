"""
Engine 1 README - Complete Implementation Documentation.

Green DevOps Operation Phase - Engine 1: Workload Prediction

This document describes the complete Engine 1 implementation, module structure,
usage patterns, and integration points.
"""

# Engine 1: Workload Prediction

## Overview

Engine 1 predicts the CPU workload for the **next 30 seconds** using a trained LSTM model
and historical/runtime data. It converts this prediction into:
- Pod count recommendation
- Load level classification (LOW, NORMAL, HIGH)
- Structured output for downstream engines (Carbon Emission, Job Prioritization)

**Key Facts:**
- Prediction window: 30 seconds (1 timestep)
- Input history: 12 timesteps = 6 minutes of data
- Model: PyTorch LSTM (2 layers, 64→32 units)
- Training data: 305,847 sequences from public fastStorage dataset
- Two modes: Cold-start (pre-trained) and Runtime (live metrics)

## Module Structure

### 1. `config.py`
Configuration constants for the entire Engine 1.

**Key variables:**
- `PREDICTION_WINDOW_SECONDS = 30` - Each timestep represents 30 seconds
- `SEQUENCE_LENGTH = 12` - Input sequences have 12 timesteps (6 minutes total)
- `LOAD_LEVEL_THRESHOLDS` - CPU thresholds for LOW/NORMAL/HIGH classification
- `TARGET_CPU_PER_POD` - Target CPU utilization per pod
- `MODEL_PATH` - Path to trained model
- `SCALER_PATH` - Path to normalization scaler

**Usage:**
```python
from config import SEQUENCE_LENGTH, PREDICTION_WINDOW_SECONDS, DEVICE
```

### 2. `model.py`
PyTorch LSTM model architecture matching trained model.

**Class: `LSTMWorkloadPredictor`**
- Input: (batch_size, 12 timesteps, 2 features)
- LSTM Layer 1: 2 → 64 units (Dropout 0.2)
- LSTM Layer 2: 64 → 32 units (Dropout 0.2)
- Dense: 32 → 16 units (ReLU)
- Output: 16 → 1 (CPU prediction)

**Key methods:**
- `forward(x)` - Forward pass through model
- `predict_single(x, device)` - Inference on single sequence
- `count_parameters()` - Get model size
- `get_architecture_summary()` - Human-readable architecture

**Usage:**
```python
from model import LSTMWorkloadPredictor
model = LSTMWorkloadPredictor()
model.load_state_dict(torch.load(model_path))
output = model(input_tensor)
```

### 3. `output_contract.py`
Data classes for input/output contract with next engines.

**Class: `Engine1Output`**
Complete prediction output consumed by Engine 2 and Engine 3:
- `system_id` - Target system
- `timestamp` - ISO format timestamp
- `predicted_cpu` - Predicted CPU percentage (0-100)
- `predicted_load_level` - "LOW", "NORMAL", or "HIGH"
- `recommended_pods` - Pod count recommendation
- `data_source` - "cold_start" or "runtime"
- `model_version` - Model version tag

Methods:
- `to_json()` - Convert to JSON string
- `to_dict()` - Convert to dictionary
- `validate()` - Validate constraints

**Class: `Engine1Request`**
Request input for predictions:
- `system_id` - Target system
- `workload_sequence` - List of [cpu, memory] pairs (length 12)
- `data_source` - "cold_start" or "runtime"

**Usage:**
```python
from output_contract import Engine1Output, create_engine1_output
output = create_engine1_output(
    system_id="system_01",
    predicted_cpu=72.5,
    predicted_load_level="HIGH",
    recommended_pods=3,
    data_source="runtime"
)
print(output.to_json())
```

### 4. `runtime_adapter.py`
Converts live Prometheus metrics and historical data into model-ready sequences.

**Class: `RuntimeAdapter`**

Key methods:
- `prepare_sequence_from_history(timestamps, cpu_values, memory_values)` - From raw data
- `prepare_sequence_from_prometheus(prometheus_data, system_id)` - From Prometheus API
- `prepare_sequence_from_csv(csv_file_path, system_id)` - From CSV file
- `create_test_sequence()` - Synthetic test data (cold-start)
- `validate_sequence(sequence)` - Shape/value validation
- `_resample_to_window(df)` - Resample to 30-second intervals
- `get_sequence_summary(sequence)` - Statistical summary

**Key responsibilities:**
- Handles irregular input intervals (Prometheus scrapes)
- Resamples to uniform 30-second windows
- Normalizes using stored scalers
- Handles missing data via interpolation

**Usage:**
```python
from runtime_adapter import RuntimeAdapter
adapter = RuntimeAdapter()

# From CSV
sequence = adapter.prepare_sequence_from_csv(
    "historical_data.csv",
    "system_01",
    normalize=True,
    scaler_cpu=scaler
)

# From Prometheus
sequence, latest_time = adapter.prepare_sequence_from_prometheus(
    prometheus_response,
    "system_01",
    normalize=True
)

# Test data
test_seq = adapter.create_test_sequence()
```

### 5. `predictor.py`
Core prediction engine with model inference and post-processing.

**Class: `WorkloadPredictor`**

Key methods:
- `load_model()` - Load trained PyTorch model
- `load_scaler()` - Load MinMaxScaler for denormalization
- `validate_sequence(sequence)` - Input validation
- `predict(sequence, system_id, data_source)` - Single prediction → Engine1Output
- `predict_multiple(sequences, system_id)` - Batch prediction
- `_denormalize_cpu(normalized_value)` - Inverse scaler transform
- `_classify_load(cpu_percentage)` - Classify "LOW"/"NORMAL"/"HIGH"
- `_estimate_pods(cpu_percentage)` - Recommend pod count
- `_calculate_confidence(normalized_prediction)` - Confidence score

**Prediction workflow:**
1. Validate input shape (12, 2)
2. Run model inference with `torch.no_grad()`
3. Denormalize prediction (0-1 → 0-100%)
4. Classify load level using thresholds
5. Estimate pod count
6. Build and return Engine1Output

**Usage:**
```python
from predictor import WorkloadPredictor
predictor = WorkloadPredictor()
predictor.load_model()
predictor.load_scaler()

output = predictor.predict(
    sequence,  # shape (12, 2)
    system_id="system_01",
    data_source="runtime"
)
print(output.predicted_cpu, output.predicted_load_level, output.recommended_pods)
```

### 6. `retraining.py`
Continuous learning and model update pipeline.

**Class: `RetrainingManager`**

Key methods:
- `should_retrain(samples_since_last_retrain)` - Determine if retraining needed
- `prepare_retraining_data(X_runtime, y_runtime, X_pretrain, y_pretrain)` - Data loaders
- `fine_tune_model(model, train_loader, val_loader)` - Fine-tuning loop
- `save_checkpoint(model, version, metrics)` - Save model state
- `load_checkpoint(checkpoint_path)` - Load saved checkpoint
- `retrain_or_finetune(X_runtime, y_runtime, ...)` - Complete workflow
- `get_retrain_summary()` - History and status

**Retraining strategy:**
- Collects samples after deployment
- Triggers when: sample count ≥ 100, OR 7 days since last retrain
- Mixes runtime data (70%) with pre-training data (30%) for stability
- Early stopping on validation loss
- Saves checkpoints with metrics and timestamp

**Usage:**
```python
from retraining import RetrainingManager
rm = RetrainingManager("models/trained/workload_predictor_v1.pt")

# Check if retraining needed
if rm.should_retrain(samples_collected):
    model, results = rm.retrain_or_finetune(
        X_runtime,
        y_runtime,
        X_pretrain,
        y_pretrain
    )
    print(f"Retrained. New checkpoint: {results['checkpoint_path']}")
```

### 7. `engine1.py`
High-level orchestrator integrating all components.

**Class: `Engine1Orchestrator`**

Key methods:
- `predict_from_cold_start(system_id, test_data_path)` - Cold-start mode
- `predict_from_runtime(request, prometheus_data)` - Runtime mode
- `batch_predict(sequences, system_id, data_source)` - Batch predictions
- `get_prediction_summary(output)` - Format for logging

**All-in-one initialization:**
```python
from engine1 import Engine1Orchestrator
engine = Engine1Orchestrator()

# Cold-start
output1 = engine.predict_from_cold_start("system_01")

# Runtime
from output_contract import Engine1Request
request = Engine1Request(
    system_id="system_02",
    timestamp="2026-04-15T10:00:00Z",
    workload_sequence=[[...], ...],  # 12 samples
    data_source="runtime"
)
output2 = engine.predict_from_runtime(request)
```

## Data Flow

### Cold-Start Flow
```
1. System deployed (no runtime history)
   ↓
2. RuntimeAdapter.create_test_sequence() → synthetic test data
   ↓
3. Predictor.predict(test_seq) → Engine1Output
   ↓
4. Output sent to Engine 2 & Engine 3
```

### Runtime Flow
```
1. Live system metrics collected (Prometheus/collector)
   ↓
2. RuntimeAdapter.prepare_sequence_from_prometheus(data) → normalized sequence (12, 2)
   ↓
3. Predictor.predict(sequence) → Engine1Output
   ↓
4. Output sent to Engine 2 & Engine 3
   ↓
5. Retraining tracker incremented
   ↓
6. If should_retrain() → Queue retraining job
```

### Retraining Flow
```
1. Runtime samples collected after deployment
   ↓
2. When sample count ≥ 100 OR 7 days elapsed
   ↓
3. RetrainingManager.should_retrain() → True
   ↓
4. Prepare data: 70% runtime + 30% pre-training
   ↓
5. Fine-tune model (5 epochs, early stopping)
   ↓
6. Save checkpoint with metrics
   ↓
7. New model becomes inference model
```

## Key Design Decisions

### 1. 30-Second Timestep Rule
- **Why:** Prometheus scrape interval is typically 30 seconds; aligns with K8s metrics
- **Implementation:** RuntimeAdapter resamples all data to 30-second windows
- **Consequence:** Sequence of 12 timesteps = 6 minutes of history

### 2. Cold-Start Support
- **Why:** System must predict immediately at deployment (no runtime history)
- **Implementation:** Pre-trained model from 305,847 public dataset sequences
- **Consequence:** First predictions use synthetic/test data, improve over time

### 3. Pod Recommendation vs Scaling
- **Why:** Engine 1 recommends, doesn't execute
- **Design:** Formula: `pods = ceil(predicted_cpu / (target_cpu_per_pod * target_utilization))`
- **Example:** 72.5% CPU / (50% × 0.8) = 1.8 → recommend 2 pods
- **Consequence:** Engine 3 refines recommendation based on job affinity/priority

### 4. Load Level Classification
- **Why:** Enables context-aware decisions in downstream engines
- **Thresholds:** 0-30% (LOW), 30-70% (NORMAL), 70-100% (HIGH)
- **Consequence:** Different optimization strategies per level

### 5. Continuous Learning
- **Why:** Model improves as deployment collects real data
- **Strategy:** Fine-tune on 70% runtime + 30% pre-training data (transfer learning)
- **Trigger:** Every 100 samples or 7 days, whichever first
- **Consequence:** Model tracks production distribution while staying stable

## Integration with Next Engines

### Engine 2: Carbon Emission Estimation
**Receives from Engine 1:**
- `predicted_cpu` - Used to estimate energy consumption
- `predicted_memory` - Optional memory prediction
- `recommended_pods` - Optional input for carbon calculation
- `predicted_load_level` - For carbon intensity lookup

**Example usage:**
```python
engine1_output = engine1.predict_from_runtime(request)
carbon_estimate = engine2.estimate_carbon(
    cpu_usage=engine1_output.predicted_cpu,
    pod_count=engine1_output.recommended_pods,
    load_level=engine1_output.predicted_load_level
)
```

### Engine 3: Job Prioritization
**Receives from Engine 1:**
- `predicted_load_level` - Affects scheduling priority
- `recommended_pods` - Baseline for priority-aware adjustment
- `system_id` - Route to correct system scheduler

**Example usage:**
```python
engine1_output = engine1.predict_from_runtime(request)
priority_decisions = engine3.prioritize_jobs(
    predicted_load=engine1_output.predicted_load_level,
    recommended_pods=engine1_output.recommended_pods
)
```

## Usage Examples

### Example 1: Cold-Start Deployment
```python
from engine1 import Engine1Orchestrator

# Initialize on system startup
engine = Engine1Orchestrator()

# Get initial prediction before runtime data exists
output = engine.predict_from_cold_start(
    system_id="app_cluster_01"
)

print(f"Initial prediction: {output.predicted_cpu:.1f}% CPU")
print(f"Load level: {output.predicted_load_level}")
print(f"Recommend: {output.recommended_pods} pods")

# Send to downstream engines
send_to_engine2(output)
send_to_engine3(output)
```

### Example 2: Runtime Prediction Loop
```python
from engine1 import Engine1Orchestrator
from output_contract import Engine1Request
import time

engine = Engine1Orchestrator()

# Prediction loop (runs every 30 seconds after data collection)
while True:
    # Get latest 12 × 30-second samples from monitoring system
    latest_metrics = collector.get_latest_sequence()  # returns [[cpu, mem], ...]
    
    # Create request
    request = Engine1Request(
        system_id="prod_service_v2",
        timestamp=datetime.utcnow().isoformat() + "Z",
        workload_sequence=latest_metrics,
        data_source="runtime"
    )
    
    # Get prediction
    output = engine.predict_from_runtime(request)
    
    # Send to other engines
    send_to_carbon_engine(output)
    send_to_job_scheduler(output)
    
    # Log
    print(f"Predicted: {output.predicted_cpu}% | Pods: {output.recommended_pods}")
    
    time.sleep(30)  # Wait for next 30-second interval
```

### Example 3: FastAPI Integration
```python
from fastapi import FastAPI
from engine1 import Engine1Orchestrator
from output_contract import Engine1Request

app = FastAPI()
engine = Engine1Orchestrator()

@app.post("/predict")
def predict(system_id: str, workload: list):
    """Predict workload for next 30 seconds."""
    request = Engine1Request(
        system_id=system_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        workload_sequence=workload,  # 12 × [cpu, mem]
        data_source="runtime"
    )
    
    output = engine.predict_from_runtime(request)
    return output.to_dict()

@app.get("/cold-start/{system_id}")
def cold_start(system_id: str):
    """Get initial prediction before runtime metrics available."""
    output = engine.predict_from_cold_start(system_id)
    return output.to_dict()
```

### Example 4: Retraining Trigger
```python
from retraining import RetrainingManager
import numpy as np

rm = RetrainingManager("models/trained/workload_predictor_v1.pt")

# After deployment has been running for a while...
runtime_samples = np.load("runtime_sequences.npy")  # (N, 12, 2)
runtime_targets = np.load("runtime_targets.npy")    # (N, 1)

# Check if retraining should happen
if rm.should_retrain(len(runtime_samples)):
    # Retrain
    new_model, results = rm.retrain_or_finetune(
        runtime_samples,
        runtime_targets,
        X_pretrain=np.load("pretrain_sequences.npy"),
        y_pretrain=np.load("pretrain_targets.npy")
    )
    
    print(f"✓ Retraining complete")
    print(f"  Checkpoint: {results['checkpoint_path']}")
    print(f"  Final val loss: {results['metrics']['final_val_loss']:.6f}")
```

## Error Handling

Common error scenarios and solutions:

### 1. Model file not found
```python
try:
    predictor.load_model()
except FileNotFoundError:
    logger.error("Model not found - check MODEL_PATH in config.py")
```

### 2. Sequence shape invalid
```python
is_valid, error = predictor.validate_sequence(sequence)
if not is_valid:
    logger.error(f"Invalid sequence: {error}")
```

### 3. Denormalization fails (scaler issue)
```
WARNING - Scalers not loaded, scaling 0-1 to 0-100
→ Check SCALER_PATH in config.py
→ Ensure pickle file exists and is valid
```

## Performance Characteristics

**Inference speed:**
- Single prediction: ~50-100ms (CPU)
- Batch prediction (32 sequences): ~200-300ms (CPU)
- Latency: Suitable for real-time Kubernetes scaling loops

**Model size:**
- Weights: ~100KB
- Scaler pickle: ~5KB
- Total: ~105KB

**Memory consumption:**
- Model: ~1MB
- Inference batch (32): ~50MB
- Per-pod: Minimal impact

## Future Enhancements

1. **Prometheus integration** - Direct integration with live Prometheus
2. **Multi-step prediction** - Predict next 5-10 timesteps ahead
3. **Uncertainty quantification** - Confidence intervals on predictions
4. **Per-system models** - Model for each deployed system vs global model
5. **Anomaly detection** - Detect and handle distribution shift
6. **GPU support** - CUDA acceleration for batch inference

## Troubleshooting

**Q: Predictions are all zeros**
A: Check denormalization. Verify scaler is loaded: `predictor.scalers is not None`

**Q: Load classification always "NORMAL"**
A: Check thresholds in config.py, verify CPU values are in percentage scale

**Q: Retraining never triggers**
A: Check RETRAINING_CHECKPOINT_INTERVAL in config.py and sample collection

**Q: Memory usage growing over time**
A: Check for data accumulation in retraining manager, implement cleanup

## Support Resources

- Model training: See `scripts/train_lstm_workload_predictor.py`
- Data preparation: See `scripts/prepare_lstm_sequences.py`
- Configuration: See `config.py` for all hyperparameters
- Architecture: See `model.py` for LSTM details
