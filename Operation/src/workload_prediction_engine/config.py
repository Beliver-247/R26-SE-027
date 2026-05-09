"""
Configuration constants for Engine 1 - Workload Prediction.
Green DevOps Operation Phase component.
"""

# Time-series parameters
PREDICTION_WINDOW_SECONDS = 30  # 1 timestep = 30 seconds
SEQUENCE_LENGTH = 12  # Number of timesteps in input sequence
HISTORICAL_WINDOW_SECONDS = PREDICTION_WINDOW_SECONDS * SEQUENCE_LENGTH  # 6 minutes

# Model parameters
INPUT_FEATURES = 2  # CPU and memory usage
OUTPUT_FEATURE = 1  # Next step CPU prediction
MODEL_VERSION = "balanced"
MODEL_PATH = "models/trained/workload_predictor_balanced.pt"
SCALER_PATH = "data/preprocessed/balanced_dataset/scaler.pkl"

# LSTM architecture (must match trained model)
LSTM_HIDDEN_SIZE_1 = 64
LSTM_HIDDEN_SIZE_2 = 32
DENSE_HIDDEN_SIZE = 16
DROPOUT_RATE = 0.2

# Load classification thresholds (CPU percentage)
LOAD_LEVEL_THRESHOLDS = {
    'LOW': 30.0,      # CPU < 30% is LOW
    'NORMAL': 70.0,   # 30% <= CPU < 70% is NORMAL
    'HIGH': 100.0     # CPU >= 70% is HIGH
}

# Pod scaling parameters
TARGET_CPU_PER_POD = 50.0  # Target CPU utilization per pod (%)
TARGET_UTILIZATION = 0.8   # Target overall utilization (80%)
MIN_PODS = 1
MAX_PODS = 10

# Data source modes
DATA_SOURCE_COLD_START = "cold_start"
DATA_SOURCE_RUNTIME = "runtime"

# Retraining parameters
RETRAINING_BATCH_SIZE = 32
RETRAINING_EPOCHS = 5
RETRAINING_LEARNING_RATE = 0.001
RETRAINING_CHECKPOINT_INTERVAL = 100  # Retrain every N samples
RETRAINING_VAL_SPLIT = 0.2

# Metrics collection
PROMETHEUS_STEP_SECONDS = 30  # Prometheus scrape interval
MAX_MISSING_DATAPOINTS = 2  # Allow up to 2 missing timesteps

# Logging and output
PREDICTIONS_LOG_DIR = "data/predictions"  # Directory for prediction CSV logs
LOG_LEVEL = "INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR)


def validate_config():
    """
    Validate configuration at startup.
    
    Ensures all required paths exist and constants are sensible.
    Raises:
        ValueError if configuration is invalid
    """
    from pathlib import Path
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Validate time parameters
    if PREDICTION_WINDOW_SECONDS <= 0:
        raise ValueError(f"PREDICTION_WINDOW_SECONDS must be > 0, got {PREDICTION_WINDOW_SECONDS}")
    
    if SEQUENCE_LENGTH <= 0:
        raise ValueError(f"SEQUENCE_LENGTH must be > 0, got {SEQUENCE_LENGTH}")
    
    if HISTORICAL_WINDOW_SECONDS != PREDICTION_WINDOW_SECONDS * SEQUENCE_LENGTH:
        raise ValueError(
            f"HISTORICAL_WINDOW_SECONDS mismatch: "
            f"expected {PREDICTION_WINDOW_SECONDS * SEQUENCE_LENGTH}, "
            f"got {HISTORICAL_WINDOW_SECONDS}"
        )
    
    # Validate model paths
    model_path = Path(MODEL_PATH)
    if not model_path.exists():
        logger.warning(f"Model path {MODEL_PATH} does not exist (will be created on training)")
    
    scaler_path = Path(SCALER_PATH)
    if not scaler_path.exists():
        logger.warning(f"Scaler path {SCALER_PATH} does not exist (will be created on training)")
    
    # Validate thresholds
    load_levels = sorted(LOAD_LEVEL_THRESHOLDS.values())
    if load_levels != [30.0, 70.0, 100.0]:  # Expected for LOW, NORMAL, HIGH
        logger.warning(f"Unusual load level thresholds: {LOAD_LEVEL_THRESHOLDS}")
    
    # Validate pod parameters
    if MIN_PODS <= 0 or MAX_PODS <= 0:
        raise ValueError(f"Pod limits must be > 0: MIN={MIN_PODS}, MAX={MAX_PODS}")
    
    if MIN_PODS > MAX_PODS:
        raise ValueError(f"MIN_PODS ({MIN_PODS}) cannot exceed MAX_PODS ({MAX_PODS})")
    
    # Create predictions directory
    pred_dir = Path(PREDICTIONS_LOG_DIR)
    pred_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"[OK] Configuration validated successfully")
INTERPOLATION_METHOD = 'linear'  # 'linear', 'forward_fill', 'zero'

# Inference parameters
DEVICE = 'cuda'  # 'cuda' or 'cpu'
INFERENCE_BATCH_MODE = False  # Support batch predictions

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
