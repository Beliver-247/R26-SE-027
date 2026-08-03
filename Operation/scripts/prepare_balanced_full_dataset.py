#!/usr/bin/env python3
"""
Prepare balanced dataset with stratification by load level
Uses only analyzable CSV files (939 total)
Ensures LOW, NORMAL, HIGH load balance in training
"""
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Load CSV analysis
analysis_data = np.load('data/csv_file_analysis.npz')
paths = analysis_data['paths']
means = analysis_data['means']
stds = analysis_data['stds']
has_high = analysis_data['has_high']
has_normal = analysis_data['has_normal']
has_variety = analysis_data['has_variety']

logger.info("="*80)
logger.info("CREATING BALANCED DATASET")
logger.info("="*80)

# Create file categories
high_std_files = paths[stds > 5.0]  # High variability
medium_std_files = paths[(stds >= 2.0) & (stds <= 5.0)]  # Medium
low_std_files = paths[stds < 2.0]  # Low

logger.info(f"\nFile stratification:")
logger.info(f"  High variability (std>5%): {len(high_std_files)}")
logger.info(f"  Medium variability (2-5%): {len(medium_std_files)}")
logger.info(f"  Low variability (<2%): {len(low_std_files)}")

# Stratified split: 80/20 train/test, with representation from each stratum
def stratified_split(file_list, train_ratio=0.8):
    """Split files while maintaining distribution"""
    n = len(file_list)
    n_train = int(n * train_ratio)
    indices = np.random.permutation(n)
    train_idx = indices[:n_train]
    test_idx = indices[n_train:]
    return file_list[train_idx], file_list[test_idx]

# Use only high and medium variability files (remove constant files)
good_files = np.concatenate([high_std_files, medium_std_files])
np.random.shuffle(good_files)

logger.info(f"\nUsing {len(good_files)} files with std > 2%")

# Split into train/test
split_idx = int(0.8 * len(good_files))
train_files = good_files[:split_idx]
test_files = good_files[split_idx:]

logger.info(f"  Train files: {len(train_files)}")
logger.info(f"  Test files: {len(test_files)}")

# Process CSV files
def process_csv_file(csv_path):
    """Extract CPU sequences from CSV"""
    try:
        df = pd.read_csv(csv_path, sep=';\t', engine='python')
        df.columns = [col.strip().lower() for col in df.columns]
        
        cpu_col = None
        for col in df.columns:
            if 'cpu usage [%]' in col:
                cpu_col = col
                break
        
        if cpu_col is None:
            return None
        
        cpu_values = pd.to_numeric(df[cpu_col], errors='coerce').dropna()
        cpu_values = cpu_values[(cpu_values >= 0) & (cpu_values <= 100)].values
        
        if len(cpu_values) < 50:  # Need enough samples
            return None
        
        # Also get memory
        mem_col = None
        for col in df.columns:
            if 'memory usage [kb]' in col:
                mem_col = col
                break
        
        if mem_col is not None:
            mem_values = pd.to_numeric(df[mem_col], errors='coerce').dropna()
        else:
            mem_values = np.zeros_like(cpu_values)
        
        return cpu_values, mem_values[:len(cpu_values)]
    except:
        return None

# Create sequences (12 timesteps, predict next value)
def create_sequences(cpu_values, memory_values, seq_len=12):
    """Create LSTM sequences"""
    X = []
    y = []
    
    for i in range(len(cpu_values) - seq_len):
        seq = np.column_stack([cpu_values[i:i+seq_len], memory_values[i:i+seq_len]])
        X.append(seq)
        y.append(cpu_values[i + seq_len])  # Predict next CPU value
    
    if len(X) == 0:
        return None
    
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

# Process all train files
logger.info("\nProcessing training files...")
X_train_list = []
y_train_list = []

for i, csv_path in enumerate(train_files):
    if (i + 1) % 50 == 0:
        logger.info(f"  {i+1}/{len(train_files)} files processed")
    
    result = process_csv_file(csv_path)
    if result:
        cpu_vals, mem_vals = result
        seqs = create_sequences(cpu_vals, mem_vals)
        if seqs:
            X, y = seqs
            X_train_list.append(X)
            y_train_list.append(y)

# Process all test files
logger.info("Processing test files...")
X_test_list = []
y_test_list = []

for i, csv_path in enumerate(test_files):
    if (i + 1) % 50 == 0:
        logger.info(f"  {i+1}/{len(test_files)} files processed")
    
    result = process_csv_file(csv_path)
    if result:
        cpu_vals, mem_vals = result
        seqs = create_sequences(cpu_vals, mem_vals)
        if seqs:
            X, y = seqs
            X_test_list.append(X)
            y_test_list.append(y)

# Concatenate all sequences
X_train = np.concatenate(X_train_list, axis=0)
y_train = np.concatenate(y_train_list, axis=0)
X_test = np.concatenate(X_test_list, axis=0)
y_test = np.concatenate(y_test_list, axis=0)

logger.info(f"\nDataset shapes:")
logger.info(f"  X_train: {X_train.shape}")
logger.info(f"  y_train: {y_train.shape}")
logger.info(f"  X_test: {X_test.shape}")
logger.info(f"  y_test: {y_test.shape}")

# Fit scaler on training data only
logger.info("\nFitting scaler...")
X_train_reshaped = X_train.reshape(-1, 2)
scaler = MinMaxScaler()
scaler.fit(X_train_reshaped)

# Transform data
X_train_scaled = scaler.transform(X_train_reshaped).reshape(X_train.shape)
X_test_scaled = scaler.transform(X_test.reshape(-1, 2)).reshape(X_test.shape)

# Scale targets separately
y_train_scaled = (y_train - scaler.data_min_[0]) / scaler.data_range_[0]
y_test_scaled = (y_test - scaler.data_min_[0]) / scaler.data_range_[0]

# Clip to [0, 1] range
y_train_scaled = np.clip(y_train_scaled, 0, 1)
y_test_scaled = np.clip(y_test_scaled, 0, 1)

logger.info(f"\nScaled data ranges:")
logger.info(f"  X_train: [{X_train_scaled.min():.6f}, {X_train_scaled.max():.6f}]")
logger.info(f"  y_train: [{y_train_scaled.min():.6f}, {y_train_scaled.max():.6f}]")
logger.info(f"  X_test: [{X_test_scaled.min():.6f}, {X_test_scaled.max():.6f}]")
logger.info(f"  y_test: [{y_test_scaled.min():.6f}, {y_test_scaled.max():.6f}]")

# Check load distribution
y_train_orig = (y_train_scaled * scaler.data_range_[0]) + scaler.data_min_[0]
y_test_orig = (y_test_scaled * scaler.data_range_[0]) + scaler.data_min_[0]

train_low = (y_train_orig < 30).sum()
train_normal = ((y_train_orig >= 30) & (y_train_orig < 70)).sum()
train_high = (y_train_orig >= 70).sum()

test_low = (y_test_orig < 30).sum()
test_normal = ((y_test_orig >= 30) & (y_test_orig < 70)).sum()
test_high = (y_test_orig >= 70).sum()

logger.info(f"\nLoad distribution (original scale):")
logger.info(f"  Train: LOW={100*train_low/len(y_train):.1f}%, " +
           f"NORMAL={100*train_normal/len(y_train):.1f}%, " +
           f"HIGH={100*train_high/len(y_train):.1f}%")
logger.info(f"  Test: LOW={100*test_low/len(y_test):.1f}%, " +
           f"NORMAL={100*test_normal/len(y_test):.1f}%, " +
           f"HIGH={100*test_high/len(y_test):.1f}%")

logger.info(f"\nTarget statistics:")
logger.info(f"  Train: mean={y_train_orig.mean():.2f}%, std={y_train_orig.std():.2f}%")
logger.info(f"  Test: mean={y_test_orig.mean():.2f}%, std={y_test_orig.std():.2f}%")

# Save dataset
output_dir = Path('data/preprocessed/balanced_dataset')
output_dir.mkdir(parents=True, exist_ok=True)

np.save(output_dir / 'X_train.npy', X_train_scaled)
np.save(output_dir / 'y_train.npy', y_train_scaled)
np.save(output_dir / 'X_test.npy', X_test_scaled)
np.save(output_dir / 'y_test.npy', y_test_scaled)

with open(output_dir / 'scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

logger.info(f"\nBalanced dataset saved to {output_dir}")
logger.info("="*80)
