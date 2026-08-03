#!/usr/bin/env python3
"""
Verify all Engine 1 scripts and config files use consistent balanced model and dataset paths.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))

from config import (
    MODEL_PATH,
    SCALER_PATH,
    MODEL_VERSION,
    LOAD_LEVEL_THRESHOLDS,
    SEQUENCE_LENGTH,
    PREDICTION_WINDOW_SECONDS
)

print("\n" + "="*80)
print("ENGINE 1 CONFIGURATION VERIFICATION")
print("="*80)

print(f"\nModel Configuration:")
print(f"  MODEL_VERSION: {MODEL_VERSION}")
print(f"  MODEL_PATH: {MODEL_PATH}")
print(f"  SCALER_PATH: {SCALER_PATH}")

print(f"\nArchitecture Configuration:")
print(f"  SEQUENCE_LENGTH: {SEQUENCE_LENGTH}")
print(f"  PREDICTION_WINDOW_SECONDS: {PREDICTION_WINDOW_SECONDS}")
print(f"  LOAD_LEVEL_THRESHOLDS: {LOAD_LEVEL_THRESHOLDS}")

# Verify files exist
model_file = Path(MODEL_PATH)
scaler_file = Path(SCALER_PATH)

print(f"\nFile Verification:")
print(f"  Model exists: {model_file.exists()} ({MODEL_PATH})")
print(f"  Scaler exists: {scaler_file.exists()} ({SCALER_PATH})")

# Check for old paths
print(f"\nConsistency Check:")

# Check config.py
config_file = Path(__file__).parent.parent / 'src/workload_prediction_engine/config.py'
config_content = config_file.read_text()
has_v1_ref = 'workload_predictor_v1' in config_content
has_full_dataset_ref = 'full_dataset' in config_content
print(f"  config.py has v1 refs: {has_v1_ref}")
print(f"  config.py has full_dataset refs: {has_full_dataset_ref}")

# Check test_engine1.py
test_file = Path(__file__).parent / 'test_engine1.py'
test_content = test_file.read_text()
test_v1_ref = 'workload_predictor_v1' in test_content
test_full_dataset_ref = 'full_dataset' in test_content
print(f"  test_engine1.py has v1 refs: {test_v1_ref}")
print(f"  test_engine1.py has full_dataset refs: {test_full_dataset_ref}")

print(f"\nEngine 1 Status:")
if not has_v1_ref and not has_full_dataset_ref and not test_v1_ref and not test_full_dataset_ref:
    print(f"  ✓ All Engine 1 config files use balanced model/dataset consistently")
else:
    print(f"  ✗ Found old path references - needs update")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
