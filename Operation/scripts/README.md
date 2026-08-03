# Scripts Directory

Utility scripts for data preparation, training, and deployment.

## Data Pipeline Overview

Complete workflow for cold-start model training:

```
Raw CSV Files → Combine → Validate → Preprocess → Train LSTM → Deploy
```

## Scripts

### 1. `combine_workload_datasets.py`
**Combines multiple CSV workload datasets into a single normalized dataset.**

**Purpose**: Cold-start data preparation from public datasets (e.g., Google Cluster traces, Azure VMs)

**Usage**:
```bash
python combine_workload_datasets.py
```

**Output**:
- File: `data/processed/workload_data.csv`
- Columns: `timestamp`, `cpu`, `memory`, `system_id`
- Records: 25 files × variable rows per file

**Features**:
- ✅ Dynamic column detection (pattern-matching, no hard-coded assumptions)
- ✅ Automatic type conversion with error handling
- ✅ Missing value removal (per-column to preserve temporal sequences)
- ✅ Timestamp sorting for temporal consistency
- ✅ System ID extraction from filenames
- ✅ Comprehensive logging with progress tracking
- ✅ Memory-efficient iterative loading

**Configuration**:
```python
# Edit in script or pass as arguments
INPUT_FOLDER = "path/to/csv/files"
NUM_FILES = 25
OUTPUT_PATH = "data/processed/workload_data.csv"
```

---

### 2. `validate_workload_data.py`
**Validates data quality and generates comprehensive QA report.**

**Purpose**: Verify combined dataset is suitable for ML training

**Usage**:
```bash
python validate_workload_data.py
```

**Validation Checks**:
- ✅ Column presence and types
- ✅ Null/NaN value detection
- ✅ Numeric range validation (negative values, outliers)
- ✅ System ID distribution analysis
- ✅ Timestamp sorting and gap detection
- ✅ Record count per system

**Output**:
Console report with:
- Column validation status
- Data type summary
- Null value counts
- CPU/Memory statistics (min, max, mean, std)
- System distribution (unique systems, records per system)
- Per-system timestamp consistency (sorted, gaps, intervals)

**Example Output**:
```
1. COLUMN VALIDATION
   Has all required columns: True

2. DATA TYPES
   timestamp: int64
   cpu: float64
   memory: float64
   system_id: object

3. NUMERIC RANGES
   CPU Usage:
     Min: 0.00, Max: 98.50
     Mean: 45.32, Std: 28.15
   Memory Usage:
     Min: 2.50, Max: 96.80
     Mean: 62.14, Std: 21.47

4. SYSTEM DISTRIBUTION
   Unique systems: 435
   Min records per system: 1200
   Max records per system: 8900
   Avg records per system: 5340
```

---

### 3. `prepare_lstm_sequences.py`
**Transforms workload data into sequences for LSTM model training.**

**Purpose**: Preprocess time-series data for neural network training

**Usage**:
```bash
python prepare_lstm_sequences.py
```

**Configuration**:
```python
sequence_length = 12      # 12 timesteps = 6 minutes of 30-sec samples
test_split = 0.2          # 20% for testing, 80% for training
```

**Processing Steps**:
1. ✅ Load normalized workload data
2. ✅ MinMax normalize features to [0, 1] for stable LSTM training
3. ✅ Create overlapping sequences of specified length
4. ✅ Prepare system-level datasets (per-system LSTM models)
5. ✅ Prepare global dataset (combined-system LSTM model)
6. ✅ Train/test split with no data leakage
7. ✅ Save preprocessed arrays + scalers for inference

**Output Locations**:
```
data/preprocessed/
├── system/
│   ├── system_001/    # Per-system LSTM data
│   │   ├── X_train.npy
│   │   ├── X_test.npy
│   │   ├── y_train.npy
│   │   ├── y_test.npy
│   ├── system_002/
│   │   └── ...
│   └── scalers.pkl    # Feature scalers for inference
│
└── global/            # Combined system LSTM data
    ├── X_train.npy
    ├── X_test.npy
    ├── y_train.npy
    ├── y_test.npy
    └── scalers.pkl
```

**Array Shapes**:
- `X_train.npy`: `(n_sequences, 12, 2)` - 12 timesteps, 2 features (CPU, memory)
- `y_train.npy`: `(n_sequences,)` - Target CPU at next timestep

**Example Processing**:
```
Input: 1000 records per system
Sequences: 988 (with overlap)
Train sequences: 790 (79%)
Test sequences: 198 (20%)

Both CPU and memory normalized to [0, 1]
Ready for feed to LSTM layer with 12 timesteps input
```

---

### 4. `train_model.py` (placeholder)
**Train LSTM model on preprocessed sequences.**

Coming soon:
- LSTM architecture definition
- Training loop with callbacks
- Model validation and benchmarking
- Checkpoint saving
- Hyperparameter tuning

---

### 5. `deploy_controller.py` (placeholder)
**Deploy trained controller to Kubernetes cluster.**

Coming soon:
- Model loading and inference
- Kubernetes API integration
- Scaling decision execution
- Monitoring and logging

## Quick Start Example

```bash
# Step 1: Combine raw datasets
python combine_workload_datasets.py
# Output: data/processed/workload_data.csv

# Step 2: Validate data quality
python validate_workload_data.py
# Review console report for issues

# Step 3: Prepare for ML training
python prepare_lstm_sequences.py
# Output: data/preprocessed/{system,global}/ with .npy arrays and scalers

# Step 4: [TODO] Train models
# python train_model.py

# Step 5: [TODO] Deploy to K8s
# python deploy_controller.py
```

## Data Files Location

```
green-devops-operation-component/
├── data/
│   ├── raw/                    # Original CSV files from public datasets
│   ├── processed/
│   │   └── workload_data.csv   # Combined normalized dataset
│   └── preprocessed/
│       ├── system/             # Per-system LSTM sequences
│       ├── global/             # Global LSTM sequences
│       └── train/              # [TODO] Trained model weights
```

## Dependencies

Required packages (in `requirements.txt`):
- `pandas` - CSV reading and dataframe operations
- `numpy` - Array operations
- `scikit-learn` - MinMaxScaler for normalization
- `tensorflow` / `pytorch` - LSTM model training (for step 4)
