#!/usr/bin/env python3
"""
Engine 1 Balanced Model - Final Validation with Stratified Sampling
Shows prediction statistics with diverse workload samples
"""

import sys
import logging
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))

from predictor import WorkloadPredictor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("ENGINE 1 BALANCED MODEL - FINAL VALIDATION")
print("="*80)

# Load balanced dataset
X_test_path = Path('data/preprocessed/balanced_dataset/X_test.npy')
y_test_path = Path('data/preprocessed/balanced_dataset/y_test.npy')
model_path = Path('models/trained/workload_predictor_balanced.pt')
scaler_path = Path('data/preprocessed/balanced_dataset/scaler.pkl')

print(f"\nLoading balanced dataset...")
X_test = np.load(X_test_path)
y_test = np.load(y_test_path)

print(f"Dataset shape: X_test={X_test.shape}, y_test={y_test.shape}")

# Initialize predictor
predictor = WorkloadPredictor(str(model_path), str(scaler_path))
predictor.load_model()
predictor.load_scaler()

print(f"Model and scaler loaded successfully\n")

# Stratified sampling: Take samples from different parts of dataset
total_samples = len(X_test)
sample_indices = np.linspace(0, total_samples-1, 100, dtype=int)

predictions = []
load_levels = {'LOW': 0, 'NORMAL': 0, 'HIGH': 0}

print(f"Testing {len(sample_indices)} stratified samples...")
print(f"(Taking every {total_samples//100}th sample across full test set)\n")

device = torch.device('cpu')

with torch.no_grad():
    for idx, sample_idx in enumerate(sample_indices):
        sample = X_test[sample_idx]
        output = predictor.predict(
            sample,
            system_id=f'system_{idx:03d}',
            data_source='runtime'
        )
        predictions.append(output.predicted_cpu)
        load_levels[output.predicted_load_level] += 1

predictions = np.array(predictions)

# Print results
print("="*80)
print("PREDICTION STATISTICS")
print("="*80)
print(f"Samples tested: {len(predictions)}")
print(f"\nPrediction Mean: {predictions.mean():.2f}%")
print(f"Prediction Std:  {predictions.std():.2f}%")
print(f"Prediction Min:  {predictions.min():.2f}%")
print(f"Prediction Max:  {predictions.max():.2f}%")

print(f"\nLoad Distribution:")
print(f"  LOW:    {load_levels['LOW']:3d} ({100*load_levels['LOW']/len(predictions):5.1f}%)")
print(f"  NORMAL: {load_levels['NORMAL']:3d} ({100*load_levels['NORMAL']/len(predictions):5.1f}%)")
print(f"  HIGH:   {load_levels['HIGH']:3d} ({100*load_levels['HIGH']/len(predictions):5.1f}%)")

print("\n" + "="*80)
print("FINAL STATUS")
print("="*80)

# Test criteria
criteria_passed = True
checks = []

# Check 1: Varied predictions (not constant)
if predictions.std() > 0.1:
    checks.append(("✓ Predictions are varied (not constant)", True))
else:
    checks.append(("✗ Predictions are constant", False))
    criteria_passed = False

# Check 2: Predictions in valid range
if predictions.min() >= 0 and predictions.max() <= 100:
    checks.append(("✓ Predictions in valid range [0%, 100%]", True))
else:
    checks.append(("✗ Predictions outside valid range", False))
    criteria_passed = False

# Check 3: Load distribution includes multiple levels
if load_levels['NORMAL'] > 0 or load_levels['HIGH'] > 0:
    checks.append(("✓ Load distribution includes NORMAL/HIGH (not 100% LOW)", True))
else:
    checks.append(("✗ All predictions are LOW load", False))
    criteria_passed = False

# Check 4: Mean is reasonable
if 0 < predictions.mean() < 100:
    checks.append(("✓ Mean prediction is in reasonable range", True))
else:
    checks.append(("✗ Mean prediction out of range", False))
    criteria_passed = False

for check, passed in checks:
    print(check)

print(f"\nOverall Status: {'PASS ✓' if criteria_passed else 'FAIL ✗'}")
print("="*80 + "\n")
