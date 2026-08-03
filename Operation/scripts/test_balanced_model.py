#!/usr/bin/env python3
"""
Test balanced model for varied predictions (not constant)
"""
import numpy as np
import torch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))
from predictor import WorkloadPredictor
from output_contract import Engine1Output

print("="*80)
print("TESTING BALANCED MODEL FOR PREDICTION VARIANCE")
print("="*80)

# Load test data
X_test = np.load('data/preprocessed/balanced_dataset/X_test.npy')
y_test = np.load('data/preprocessed/balanced_dataset/y_test.npy')

print(f"\nTest dataset:")
print(f"  Samples: {len(y_test)}")

# Load scaler
import pickle
with open('data/preprocessed/balanced_dataset/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# Denormalize targets
y_test_original = (y_test * scaler.data_range_[0]) + scaler.data_min_[0]

print(f"  Target range: [{y_test_original.min():.2f}, {y_test_original.max():.2f}]%")
print(f"  Target mean: {y_test_original.mean():.2f}%")
print(f"  Target std: {y_test_original.std():.2f}%")

# Load model
print(f"\nLoading model...")
model_path = Path('models/trained/workload_predictor_balanced.pt')
scaler_path = Path('data/preprocessed/balanced_dataset/scaler.pkl')

if not model_path.exists():
    print(f"  ❌ Model not found: {model_path}")
    sys.exit(1)

predictor = WorkloadPredictor(str(model_path), str(scaler_path))
try:
    predictor.load_model()
    predictor.load_scaler()
    print(f"  ✓ Model loaded")
except Exception as e:
    print(f"  ❌ Failed to load model: {e}")
    sys.exit(1)

# Test on sample
print(f"\nTesting predictions on 100 samples...")

# Take stratified samples
indices = np.linspace(0, len(X_test)-1, 100, dtype=int)
predictions = []
actuals = []

for idx in indices:
    try:
        output = predictor.predict(
            X_test[idx],
            system_id=f'test_{idx}',
            data_source='runtime'
        )
        predictions.append(output.predicted_cpu)
        actuals.append(y_test_original[idx])
    except Exception as e:
        print(f"  Error on sample {idx}: {e}")
        continue

predictions = np.array(predictions)
actuals = np.array(actuals)

print(f"\nPrediction statistics:")
print(f"  Min: {predictions.min():.2f}%")
print(f"  Max: {predictions.max():.2f}%")
print(f"  Mean: {predictions.mean():.2f}%")
print(f"  Std: {predictions.std():.2f}%")
print(f"  Range: {predictions.max() - predictions.min():.2f}%")

print(f"\nActual statistics:")
print(f"  Min: {actuals.min():.2f}%")
print(f"  Max: {actuals.max():.2f}%")
print(f"  Mean: {actuals.mean():.2f}%")
print(f"  Std: {actuals.std():.2f}%")

# Check improvement
old_pred_std = 0.0  # From previous constant predictions
improvement = predictions.std() - old_pred_std

print(f"\n" + "="*80)
if predictions.std() > 0.5:
    print(f"✓ IMPROVED: Predictions now have variance (std={predictions.std():.2f}%)")
    print(f"  Previously: std=0.00% (constant 2.07%)")
    print(f"  Now: std={predictions.std():.2f}%")
else:
    print(f"⚠ WARNING: Predictions still have low variance (std={predictions.std():.2f}%)")

# Load distribution
low_count = (predictions < 30).sum()
normal_count = ((predictions >= 30) & (predictions < 70)).sum()
high_count = (predictions >= 70).sum()

print(f"\nPrediction load distribution:")
print(f"  LOW (<30%): {low_count}/100 ({low_count}%)")
print(f"  NORMAL (30-70%): {normal_count}/100 ({normal_count}%)")
print(f"  HIGH (>70%): {high_count}/100 ({high_count}%)")

if low_count < 95 or (normal_count + high_count) > 5:
    print(f"✓ GOOD: Load distribution is varied")
else:
    print(f"⚠ WARNING: Still mostly LOW load")

print("="*80)
