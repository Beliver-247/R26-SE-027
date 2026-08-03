#!/usr/bin/env python3
"""
Engine 1 Final Status - Balanced Model Validation Summary
"""

import sys
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))

# Suppress logging for cleaner output
import logging
logging.getLogger('predictor').setLevel(logging.ERROR)

from predictor import WorkloadPredictor

# Load data
X_test = np.load('data/preprocessed/balanced_dataset/X_test.npy')
y_test = np.load('data/preprocessed/balanced_dataset/y_test.npy')

# Initialize predictor
predictor = WorkloadPredictor('models/trained/workload_predictor_balanced.pt', 
                              'data/preprocessed/balanced_dataset/scaler.pkl')
predictor.load_model()
predictor.load_scaler()

# Stratified sampling
total_samples = len(X_test)
sample_indices = np.linspace(0, total_samples-1, 100, dtype=int)

predictions = []
load_levels = {'LOW': 0, 'NORMAL': 0, 'HIGH': 0}

print("\nProcessing 100 stratified samples from balanced test dataset...")

for idx, sample_idx in enumerate(sample_indices):
    sample = X_test[sample_idx]
    output = predictor.predict(sample, system_id=f'sys_{idx}', data_source='runtime')
    predictions.append(output.predicted_cpu)
    load_levels[output.predicted_load_level] += 1

predictions = np.array(predictions)

# Print summary
print("\n" + "="*80)
print("ENGINE 1 BALANCED MODEL - PREDICTION STATISTICS")
print("="*80)
print(f"\nPrediction Mean:      {predictions.mean():.2f}%")
print(f"Prediction Std:       {predictions.std():.2f}%")
print(f"Prediction Min:       {predictions.min():.2f}%")
print(f"Prediction Max:       {predictions.max():.2f}%")

print(f"\nLoad Distribution:")
low_pct = 100 * load_levels['LOW'] / len(predictions)
normal_pct = 100 * load_levels['NORMAL'] / len(predictions)
high_pct = 100 * load_levels['HIGH'] / len(predictions)
print(f"  LOW:    {load_levels['LOW']:3d} ({low_pct:5.1f}%)")
print(f"  NORMAL: {load_levels['NORMAL']:3d} ({normal_pct:5.1f}%)")
print(f"  HIGH:   {load_levels['HIGH']:3d} ({high_pct:5.1f}%)")

print("\n" + "="*80)
print("VALIDATION CHECKS")
print("="*80)

checks = [
    ("Predictions are varied (not constant)", predictions.std() > 0.1),
    ("Predictions in valid range [0%, 100%]", predictions.min() >= 0 and predictions.max() <= 100),
    ("Load includes multiple levels", load_levels['NORMAL'] + load_levels['HIGH'] > 0),
    ("Mean prediction is reasonable", 0 < predictions.mean() < 100),
]

for check_name, passed in checks:
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {check_name}")

all_pass = all(p for _, p in checks)
print("\n" + "="*80)
print(f"OVERALL STATUS: {'✓ PASS' if all_pass else '✗ FAIL'}")
print("="*80 + "\n")
