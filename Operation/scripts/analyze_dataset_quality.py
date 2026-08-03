#!/usr/bin/env python3
"""
Analyze dataset quality to diagnose constant-prediction issue
"""
import numpy as np
import pickle
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Load preprocessed data
X_train = np.load('data/preprocessed/full_dataset/X_train.npy')
y_train = np.load('data/preprocessed/full_dataset/y_train.npy')
X_test = np.load('data/preprocessed/full_dataset/X_test.npy')
y_test = np.load('data/preprocessed/full_dataset/y_test.npy')

with open('data/preprocessed/full_dataset/scaler.pkl', 'rb') as f:
    scaler_data = pickle.load(f)

logger.info("=" * 80)
logger.info("DATASET QUALITY ANALYSIS")
logger.info("=" * 80)

# 1. Training set distribution
logger.info("\n1. TRAINING SET DISTRIBUTION (NORMALIZED)")
logger.info(f"  Shape: {y_train.shape}")
logger.info(f"  Min: {y_train.min():.6f}")
logger.info(f"  Max: {y_train.max():.6f}")
logger.info(f"  Mean: {y_train.mean():.6f}")
logger.info(f"  Std: {y_train.std():.6f}")
logger.info(f"  Median: {np.median(y_train):.6f}")
logger.info(f"  Q1: {np.percentile(y_train, 25):.6f}")
logger.info(f"  Q3: {np.percentile(y_train, 75):.6f}")

# 2. Test set distribution
logger.info("\n2. TEST SET DISTRIBUTION (NORMALIZED)")
logger.info(f"  Shape: {y_test.shape}")
logger.info(f"  Min: {y_test.min():.6f}")
logger.info(f"  Max: {y_test.max():.6f}")
logger.info(f"  Mean: {y_test.mean():.6f}")
logger.info(f"  Std: {y_test.std():.6f}")
logger.info(f"  Median: {np.median(y_test):.6f}")
logger.info(f"  Q1: {np.percentile(y_test, 25):.6f}")
logger.info(f"  Q3: {np.percentile(y_test, 75):.6f}")

# 3. Denormalize and check original scale
logger.info("\n3. SCALER METADATA")
if isinstance(scaler_data, dict):
    scaler = scaler_data.get('global_cpu', scaler_data)
else:
    scaler = scaler_data
    
logger.info(f"  Type: {type(scaler)}")
logger.info(f"  Data min: {scaler.data_min_}")
logger.info(f"  Data max: {scaler.data_max_}")
logger.info(f"  Data range: {scaler.data_range_}")

# Denormalize using only CPU feature (index 0)
cpu_min = scaler.data_min_[0]
cpu_max = scaler.data_max_[0]
cpu_range = scaler.data_range_[0]

y_train_original = (y_train * cpu_range) + cpu_min
y_test_original = (y_test * cpu_range) + cpu_min

logger.info("\n4. TRAINING SET DISTRIBUTION (ORIGINAL SCALE %)")
logger.info(f"  Min: {y_train_original.min():.2f}%")
logger.info(f"  Max: {y_train_original.max():.2f}%")
logger.info(f"  Mean: {y_train_original.mean():.2f}%")
logger.info(f"  Std: {y_train_original.std():.2f}%")
logger.info(f"  Median: {np.median(y_train_original):.2f}%")

logger.info("\n5. TEST SET DISTRIBUTION (ORIGINAL SCALE %)")
logger.info(f"  Min: {y_test_original.min():.2f}%")
logger.info(f"  Max: {y_test_original.max():.2f}%")
logger.info(f"  Mean: {y_test_original.mean():.2f}%")
logger.info(f"  Std: {y_test_original.std():.2f}%")
logger.info(f"  Median: {np.median(y_test_original):.2f}%")

# 6. Load level distribution (thresholds: LOW=0-30, NORMAL=30-70, HIGH=70-100)
logger.info("\n6. LOAD LEVEL DISTRIBUTION")
train_low = (y_train_original < 30).sum()
train_normal = ((y_train_original >= 30) & (y_train_original < 70)).sum()
train_high = (y_train_original >= 70).sum()

test_low = (y_test_original < 30).sum()
test_normal = ((y_test_original >= 30) & (y_test_original < 70)).sum()
test_high = (y_test_original >= 70).sum()

logger.info(f"  Training: LOW={train_low} ({100*train_low/len(y_train):.1f}%), " +
           f"NORMAL={train_normal} ({100*train_normal/len(y_train):.1f}%), " +
           f"HIGH={train_high} ({100*train_high/len(y_train):.1f}%)")
logger.info(f"  Test: LOW={test_low} ({100*test_low/len(y_test):.1f}%), " +
           f"NORMAL={test_normal} ({100*test_normal/len(y_test):.1f}%), " +
           f"HIGH={test_high} ({100*test_high/len(y_test):.1f}%)")

# 7. Feature range (input sequences)
logger.info("\n7. INPUT FEATURE RANGE (CPU + MEMORY)")
X_train_flat = X_train.reshape(-1, 2)
X_test_flat = X_test.reshape(-1, 2)

logger.info(f"  Train CPU: [{X_train_flat[:, 0].min():.6f}, {X_train_flat[:, 0].max():.6f}]")
logger.info(f"  Train Memory: [{X_train_flat[:, 1].min():.6f}, {X_train_flat[:, 1].max():.6f}]")
logger.info(f"  Test CPU: [{X_test_flat[:, 0].min():.6f}, {X_test_flat[:, 0].max():.6f}]")
logger.info(f"  Test Memory: [{X_test_flat[:, 1].min():.6f}, {X_test_flat[:, 1].max():.6f}]")

# 8. Data variance analysis
logger.info("\n8. VARIANCE BY SEQUENCE")
train_var = np.var(X_train, axis=(1, 2))
test_var = np.var(X_test, axis=(1, 2))

logger.info(f"  Train variance: min={train_var.min():.6f}, max={train_var.max():.6f}, " +
           f"mean={train_var.mean():.6f}, std={train_var.std():.6f}")
logger.info(f"  Test variance: min={test_var.min():.6f}, max={test_var.max():.6f}, " +
           f"mean={test_var.mean():.6f}, std={test_var.std():.6f}")

# Sequences with very low variance
low_var_threshold = train_var.mean() * 0.1
low_var_count = (train_var < low_var_threshold).sum()
logger.info(f"  Sequences with very low variance (<10% of mean): {low_var_count}/{len(train_var)}")

# 9. Target-input correlation
logger.info("\n9. TARGET-INPUT CORRELATION")
input_means = X_train.mean(axis=1)  # Mean across timesteps for each sequence
correlation_cpu = np.corrcoef(input_means[:, 0], y_train)[0, 1]
correlation_mem = np.corrcoef(input_means[:, 1], y_train)[0, 1]
logger.info(f"  Correlation CPU input -> CPU target: {correlation_cpu:.4f}")
logger.info(f"  Correlation Memory input -> CPU target: {correlation_mem:.4f}")

# 10. Value distribution histogram
logger.info("\n10. VALUE DISTRIBUTION HISTOGRAM")
bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
hist, _ = np.histogram(y_train_original, bins=bins)
logger.info("  Training distribution by CPU % ranges:")
for i in range(len(bins)-1):
    pct = 100 * hist[i] / len(y_train)
    bar = '█' * int(pct / 2)
    logger.info(f"    {bins[i]:3d}-{bins[i+1]:3d}%: {hist[i]:6d} ({pct:5.1f}%) {bar}")

hist, _ = np.histogram(y_test_original, bins=bins)
logger.info("  Test distribution by CPU % ranges:")
for i in range(len(bins)-1):
    pct = 100 * hist[i] / len(y_test)
    bar = '█' * int(pct / 2)
    logger.info(f"    {bins[i]:3d}-{bins[i+1]:3d}%: {hist[i]:6d} ({pct:5.1f}%) {bar}")

logger.info("\n" + "=" * 80)
logger.info("DIAGNOSIS")
logger.info("=" * 80)
if y_train_original.std() < 5:
    logger.info("❌ PROBLEM: Target variance is very low (<5%)")
    logger.info("   Model will collapse to predicting near-constant mean")
else:
    logger.info("✓ Target variance is reasonable")

if train_normal + train_high < len(y_train) * 0.1:
    logger.info("❌ PROBLEM: <10% of training data is NORMAL or HIGH load")
    logger.info("   Dataset is heavily skewed toward LOW load")
else:
    logger.info("✓ Reasonable distribution of load levels")

if train_low > len(y_train) * 0.95:
    logger.info("❌ PROBLEM: >95% of training data is LOW load")
    logger.info("   Model has no examples of high-load behavior")
else:
    logger.info("✓ Adequate representation of different load levels")

logger.info("=" * 80)
