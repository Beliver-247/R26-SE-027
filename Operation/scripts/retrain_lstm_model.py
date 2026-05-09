#!/usr/bin/env python3
"""
Retrain LSTM model on balanced dataset
"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))
from model import LSTMWorkloadPredictor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

logger.info("="*80)
logger.info("RETRAINING LSTM MODEL ON BALANCED DATASET")
logger.info("="*80)

# Load balanced dataset
logger.info("\nLoading balanced dataset...")
X_train_full = np.load('data/preprocessed/balanced_dataset/X_train.npy')
y_train_full = np.load('data/preprocessed/balanced_dataset/y_train.npy')
X_test_full = np.load('data/preprocessed/balanced_dataset/X_test.npy')
y_test_full = np.load('data/preprocessed/balanced_dataset/y_test.npy')

logger.info(f"Full dataset shape:")
logger.info(f"  X_train: {X_train_full.shape}, y_train: {y_train_full.shape}")
logger.info(f"  X_test: {X_test_full.shape}, y_test: {y_test_full.shape}")

# Use stratified sampling for faster training
logger.info("\nSampling stratified subset for faster training...")
# Sample 5% for training (faster iteration while keeping balance)
sample_fraction = 0.05
n_train_samples = int(len(X_train_full) * sample_fraction)
n_test_samples = int(len(X_test_full) * sample_fraction)

# Stratify by target value to maintain distribution
train_indices = np.argsort(y_train_full)
test_indices = np.argsort(y_test_full)

# Take every nth sample to maintain stratification
train_step = max(1, len(train_indices) // n_train_samples)
test_step = max(1, len(test_indices) // n_test_samples)

train_indices = train_indices[::train_step][:n_train_samples]
test_indices = test_indices[::test_step][:n_test_samples]

X_train = X_train_full[train_indices]
y_train = y_train_full[train_indices]
X_test = X_test_full[test_indices]
y_test = y_test_full[test_indices]

logger.info(f"Sampled subset ({sample_fraction*100:.0f}%):")
logger.info(f"  X_train: {X_train.shape}, y_train: {y_train.shape}")
logger.info(f"  X_test: {X_test.shape}, y_test: {y_test.shape}")

# Convert to PyTorch
X_train_tensor = torch.from_numpy(X_train).float()
y_train_tensor = torch.from_numpy(y_train).float().unsqueeze(1)
X_test_tensor = torch.from_numpy(X_test).float()
y_test_tensor = torch.from_numpy(y_test).float().unsqueeze(1)

# Create DataLoaders
batch_size = 128
train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_dataset = TensorDataset(X_test_tensor, y_test_tensor)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

logger.info(f"\nDataLoader setup:")
logger.info(f"  Batch size: {batch_size}")
logger.info(f"  Train batches: {len(train_loader)}")
logger.info(f"  Test batches: {len(test_loader)}")

# Initialize model
device = torch.device('cpu')
model = LSTMWorkloadPredictor(
    input_size=2,
    hidden_size_1=64,
    hidden_size_2=32,
    dense_hidden_size=16,
    dropout_rate=0.2
).to(device)

logger.info(f"\nModel initialized on {device}")

# Training setup
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()
epochs = 20
patience = 5
best_loss = float('inf')
patience_counter = 0

logger.info(f"\nTraining configuration:")
logger.info(f"  Optimizer: Adam (lr=0.001)")
logger.info(f"  Loss: MSELoss")
logger.info(f"  Epochs: {epochs}")
logger.info(f"  Early stopping patience: {patience}")

# Training loop
train_losses = []
test_losses = []

logger.info("\n" + "="*80)
logger.info("TRAINING")
logger.info("="*80)

for epoch in range(epochs):
    # Train
    model.train()
    train_loss = 0.0
    for X_batch, y_batch in train_loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)
        
        optimizer.zero_grad()
        y_pred = model(X_batch)
        loss = criterion(y_pred, y_batch)
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item() * len(X_batch)
    
    train_loss /= len(X_train)
    train_losses.append(train_loss)
    
    # Test
    model.eval()
    test_loss = 0.0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            
            y_pred = model(X_batch)
            loss = criterion(y_pred, y_batch)
            test_loss += loss.item() * len(X_batch)
    
    test_loss /= len(X_test)
    test_losses.append(test_loss)
    
    logger.info(f"Epoch {epoch+1:2d}/{epochs} | Train Loss: {train_loss:.6f} | Test Loss: {test_loss:.6f}")
    
    # Early stopping
    if test_loss < best_loss:
        best_loss = test_loss
        patience_counter = 0
        # Save best model
        torch.save(model.state_dict(), 'models/trained/workload_predictor_balanced.pt')
        logger.info(f"             → Model saved (test loss: {test_loss:.6f})")
    else:
        patience_counter += 1
        if patience_counter >= patience:
            logger.info(f"\nEarly stopping at epoch {epoch+1}: no improvement for {patience} epochs")
            break

logger.info("\n" + "="*80)
logger.info("TRAINING COMPLETE")
logger.info("="*80)

# Evaluate on test set
model.eval()
with torch.no_grad():
    y_pred_all = []
    y_test_all = []
    
    for X_batch, y_batch in test_loader:
        X_batch = X_batch.to(device)
        y_pred = model(X_batch).cpu().numpy()
        y_pred_all.append(y_pred)
        y_test_all.append(y_batch.numpy())
    
    y_pred_all = np.concatenate(y_pred_all)
    y_test_all = np.concatenate(y_test_all)

# Metrics
mae = np.abs(y_pred_all - y_test_all).mean()
rmse = np.sqrt(((y_pred_all - y_test_all)**2).mean())
mape = np.mean(np.abs((y_test_all - y_pred_all) / (y_test_all + 1e-8))) * 100

logger.info(f"\nFinal test metrics:")
logger.info(f"  MAE: {mae:.6f}")
logger.info(f"  RMSE: {rmse:.6f}")
logger.info(f"  MAPE: {mape:.2f}%")

# Check prediction distribution
logger.info(f"\nPrediction statistics:")
logger.info(f"  Min: {y_pred_all.min():.6f}")
logger.info(f"  Max: {y_pred_all.max():.6f}")
logger.info(f"  Mean: {y_pred_all.mean():.6f}")
logger.info(f"  Std: {y_pred_all.std():.6f}")

# Target statistics
logger.info(f"\nTarget statistics:")
logger.info(f"  Min: {y_test_all.min():.6f}")
logger.info(f"  Max: {y_test_all.max():.6f}")
logger.info(f"  Mean: {y_test_all.mean():.6f}")
logger.info(f"  Std: {y_test_all.std():.6f}")

logger.info(f"\nModel saved: models/trained/workload_predictor_balanced.pt")
logger.info("="*80)
