#!/usr/bin/env python3
"""
Prepare full dataset from 1250 CSV files for LSTM training.
Simplified approach without strict resampling - uses raw data with optional downsampling.
"""

import os
import sys
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import MinMaxScaler
from concurrent.futures import ProcessPoolExecutor, as_completed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATASET_DIR = Path('data/public_datasets/fastStorage/2013-8')
OUTPUT_DIR = Path('data/preprocessed/full_dataset')
SEQUENCE_LENGTH = 12
TRAIN_FILE_COUNT = 1000
TEST_FILE_COUNT = 250
NUM_WORKERS = 8
MIN_ROWS = 50

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def process_csv_file(file_path, system_id):
    """Process single CSV file and create sequences."""
    try:
        # Try multiple delimiters
        delimiters = [',', ';', '\t', '|']
        df = None
        for delim in delimiters:
            try:
                df = pd.read_csv(file_path, delimiter=delim, on_bad_lines='skip')
                if len(df) > 0 and len(df.columns) >= 3:
                    break
            except:
                continue
        
        if df is None or df.empty or len(df) < MIN_ROWS:
            return None
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Find and identify key columns
        cpu_col, mem_col = None, None
        df_lower = {c: i for i, c in enumerate(df.columns.str.lower())}
        
        # Look for cpu column
        for key in ['cpu', 'usage', 'percent', '%cpu', 'cpu_util']:
            for col_name in df_lower:
                if key in col_name:
                    cpu_col = df.columns[df_lower[col_name]]
                    break
            if cpu_col:
                break
        
        # Look for memory column
        for key in ['mem', 'memory', 'ram', '%mem', 'mem_util']:
            for col_name in df_lower:
                if key in col_name:
                    mem_col = df.columns[df_lower[col_name]]
                    break
            if mem_col:
                break
        
        # Fallback: use last two numeric columns
        if not cpu_col or not mem_col:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) >= 2:
                cpu_col = numeric_cols[-2]
                mem_col = numeric_cols[-1]
            else:
                return None
        
        # Extract and convert to numeric
        cpu = pd.to_numeric(df[cpu_col], errors='coerce')
        mem = pd.to_numeric(df[mem_col], errors='coerce')
        
        # Check for NaNs and clean
        data = np.column_stack([cpu, mem]).astype(np.float32)
        data = data[~np.isnan(data).any(axis=1)]
        
        if len(data) < MIN_ROWS:
            return None
        
        # Downsample if too large (target 100-300 samples)
        if len(data) > 500:
            step = len(data) // 250
            data = data[::step]
        
        # Skip if insufficient
        if len(data) < SEQUENCE_LENGTH + 1:
            return None
        
        # Create sequences
        sequences, targets = [], []
        for i in range(len(data) - SEQUENCE_LENGTH):
            sequences.append(data[i:i + SEQUENCE_LENGTH])
            targets.append(data[i + SEQUENCE_LENGTH, 0])
        
        if len(sequences) == 0:
            return None
        
        return np.array(sequences, dtype=np.float32), np.array(targets, dtype=np.float32)
        
    except Exception as e:
        return None


def main():
    logger.info("="*80)
    logger.info("FULL DATASET PREPARATION")
    logger.info("="*80)
    
    # Discover CSV files
    if not DATASET_DIR.exists():
        logger.error(f"Dataset directory not found: {DATASET_DIR}")
        return
    
    csv_files = sorted(list(DATASET_DIR.glob('*.csv')))
    logger.info(f"Found {len(csv_files)} CSV files")
    
    if len(csv_files) < TRAIN_FILE_COUNT + TEST_FILE_COUNT:
        logger.error(f"Need {TRAIN_FILE_COUNT + TEST_FILE_COUNT} files, found {len(csv_files)}")
        return
    
    # Split
    train_files = csv_files[:TRAIN_FILE_COUNT]
    test_files = csv_files[TRAIN_FILE_COUNT:TRAIN_FILE_COUNT + TEST_FILE_COUNT]
    
    logger.info(f"Processing {len(train_files)} training + {len(test_files)} test files")
    
    # Process training files
    logger.info("-"*80)
    logger.info("Processing training files...")
    train_sequences, train_targets = [], []
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(process_csv_file, f, i) for i, f in enumerate(train_files)]
        
        for completed, future in enumerate(as_completed(futures)):
            result = future.result()
            if result is not None:
                seq, targets = result
                train_sequences.append(seq)
                train_targets.append(targets)
            
            if (completed + 1) % 200 == 0:
                logger.info(f"Train: {completed + 1}/{len(train_files)} done")
    
    if not train_sequences:
        logger.error("No training sequences generated!")
        return
    
    X_train = np.vstack(train_sequences)
    y_train = np.concatenate(train_targets)
    logger.info(f"Training: {X_train.shape[0]} sequences from {len(train_sequences)} files")
    
    # Process test files
    logger.info("-"*80)
    logger.info("Processing test files...")
    test_sequences, test_targets = [], []
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(process_csv_file, f, TRAIN_FILE_COUNT + i) for i, f in enumerate(test_files)]
        
        for completed, future in enumerate(as_completed(futures)):
            result = future.result()
            if result is not None:
                seq, targets = result
                test_sequences.append(seq)
                test_targets.append(targets)
            
            if (completed + 1) % 50 == 0:
                logger.info(f"Test: {completed + 1}/{len(test_files)} done")
    
    if not test_sequences:
        logger.error("No test sequences generated!")
        return
    
    X_test = np.vstack(test_sequences)
    y_test = np.concatenate(test_targets)
    logger.info(f"Test: {X_test.shape[0]} sequences from {len(test_sequences)} files")
    
    # Fit and apply scaler
    logger.info("-"*80)
    logger.info("Fitting scaler...")
    
    X_train_flat = X_train.reshape(-1, 2)
    scaler = MinMaxScaler()
    scaler.fit(X_train_flat)
    
    X_train_scaled = scaler.transform(X_train_flat).reshape(X_train.shape)
    X_test_flat = X_test.reshape(-1, 2)
    X_test_scaled = scaler.transform(X_test_flat).reshape(X_test.shape)
    
    # Scale targets using only the first feature (CPU) dimension of the scaler
    y_train_scaled = (y_train - scaler.data_min_[0]) / (scaler.data_max_[0] - scaler.data_min_[0])
    y_test_scaled = (y_test - scaler.data_min_[0]) / (scaler.data_max_[0] - scaler.data_min_[0])
    
    # Save
    logger.info("-"*80)
    logger.info("Saving data...")
    
    np.save(OUTPUT_DIR / 'X_train.npy', X_train_scaled)
    np.save(OUTPUT_DIR / 'y_train.npy', y_train_scaled)
    np.save(OUTPUT_DIR / 'X_test.npy', X_test_scaled)
    np.save(OUTPUT_DIR / 'y_test.npy', y_test_scaled)
    
    with open(OUTPUT_DIR / 'scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    
    logger.info(f"X_train: {(OUTPUT_DIR / 'X_train.npy').stat().st_size / 1e6:.2f} MB")
    logger.info(f"y_train: {(OUTPUT_DIR / 'y_train.npy').stat().st_size / 1e6:.2f} MB")
    logger.info(f"X_test: {(OUTPUT_DIR / 'X_test.npy').stat().st_size / 1e6:.2f} MB")
    logger.info(f"y_test: {(OUTPUT_DIR / 'y_test.npy').stat().st_size / 1e6:.2f} MB")
    
    logger.info("="*80)
    logger.info("DONE")
    logger.info("="*80)
    logger.info(f"Training: {X_train.shape}")
    logger.info(f"Test: {X_test.shape}")


if __name__ == '__main__':
    main()
