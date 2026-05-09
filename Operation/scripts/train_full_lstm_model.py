#!/usr/bin/env python3
"""
Train LSTM model on full preprocessed dataset.
- Load 1000 training systems, 250 test systems
- Build PyTorch LSTM architecture
- Train with DataLoader, validation on test set
- Save trained model
"""

import os
import sys
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pickle
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam
import matplotlib.pyplot as plt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = Path('data/preprocessed/full_dataset')
MODEL_DIR = Path('models/trained')
RESULTS_DIR = Path('data/results')

BATCH_SIZE = 32
EPOCHS = 50
LEARNING_RATE = 0.001
EARLY_STOPPING_PATIENCE = 5
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Create directories
MODEL_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class LSTMWorkloadPredictor(nn.Module):
    """LSTM model for workload prediction."""
    
    def __init__(self, input_size=2, hidden_size1=64, hidden_size2=32, 
                 dense_size=16, output_size=1, dropout=0.2):
        super().__init__()
        
        self.lstm1 = nn.LSTM(input_size, hidden_size1, batch_first=True, dropout=dropout)
        self.lstm2 = nn.LSTM(hidden_size1, hidden_size2, batch_first=True, dropout=dropout)
        self.dense = nn.Sequential(
            nn.Linear(hidden_size2, dense_size),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        self.output = nn.Linear(dense_size, output_size)
    
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        lstm1_out, _ = self.lstm1(x)
        lstm2_out, _ = self.lstm2(lstm1_out)
        
        # Use last timestep output
        last_output = lstm2_out[:, -1, :]  # (batch, hidden_size2)
        
        dense_out = self.dense(last_output)
        output = self.output(dense_out)
        
        return output


def load_data():
    """Load preprocessed data."""
    logger.info("-" * 80)
    logger.info("Loading preprocessed data...")
    logger.info("-" * 80)
    
    X_train = np.load(DATA_DIR / 'X_train.npy')
    y_train = np.load(DATA_DIR / 'y_train.npy')
    X_test = np.load(DATA_DIR / 'X_test.npy')
    y_test = np.load(DATA_DIR / 'y_test.npy')
    
    with open(DATA_DIR / 'scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    
    logger.info(f"X_train: {X_train.shape}")
    logger.info(f"y_train: {y_train.shape}")
    logger.info(f"X_test: {X_test.shape}")
    logger.info(f"y_test: {y_test.shape}")
    
    return X_train, y_train, X_test, y_test, scaler


def create_dataloaders(X_train, y_train, X_test, y_test):
    """Create PyTorch DataLoaders."""
    logger.info("-" * 80)
    logger.info("Creating DataLoaders...")
    logger.info("-" * 80)
    
    # Convert to tensors
    X_train_tensor = torch.from_numpy(X_train).float()
    y_train_tensor = torch.from_numpy(y_train).float().unsqueeze(1)
    X_test_tensor = torch.from_numpy(X_test).float()
    y_test_tensor = torch.from_numpy(y_test).float().unsqueeze(1)
    
    # Create datasets
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    test_dataset = TensorDataset(X_test_tensor, y_test_tensor)
    
    # Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    logger.info(f"Training batches: {len(train_loader)}")
    logger.info(f"Test batches: {len(test_loader)}")
    
    return train_loader, test_loader


def train_epoch(model, train_loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    
    for X_batch, y_batch in train_loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)
        
        optimizer.zero_grad()
        predictions = model(X_batch)
        loss = criterion(predictions, y_batch)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    avg_loss = total_loss / len(train_loader)
    return avg_loss


def evaluate(model, test_loader, criterion, device):
    """Evaluate on test set."""
    model.eval()
    total_loss = 0.0
    all_predictions = []
    all_targets = []
    
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            
            total_loss += loss.item()
            all_predictions.append(predictions.cpu().numpy())
            all_targets.append(y_batch.cpu().numpy())
    
    avg_loss = total_loss / len(test_loader)
    predictions = np.vstack(all_predictions)
    targets = np.vstack(all_targets)
    
    # Calculate metrics
    mae = np.mean(np.abs(predictions - targets))
    rmse = np.sqrt(np.mean((predictions - targets) ** 2))
    mape = np.mean(np.abs((predictions - targets) / (np.abs(targets) + 1e-8))) * 100
    
    # R² score
    ss_res = np.sum((predictions - targets) ** 2)
    ss_tot = np.sum((targets - np.mean(targets)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    
    return avg_loss, mae, rmse, mape, r2


def main():
    logger.info("=" * 80)
    logger.info("FULL LSTM MODEL TRAINING")
    logger.info("=" * 80)
    logger.info(f"Device: {DEVICE}")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info(f"Learning rate: {LEARNING_RATE}")
    logger.info(f"Epochs: {EPOCHS}")
    logger.info(f"Early stopping patience: {EARLY_STOPPING_PATIENCE}")
    
    # Load data
    X_train, y_train, X_test, y_test, scaler = load_data()
    
    # Create dataloaders
    train_loader, test_loader = create_dataloaders(X_train, y_train, X_test, y_test)
    
    # Initialize model
    logger.info("-" * 80)
    logger.info("Initializing model...")
    logger.info("-" * 80)
    
    model = LSTMWorkloadPredictor(
        input_size=2,
        hidden_size1=64,
        hidden_size2=32,
        dense_size=16,
        output_size=1,
        dropout=0.2
    ).to(DEVICE)
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Total parameters: {total_params:,}")
    logger.info(f"Trainable parameters: {trainable_params:,}")
    
    # Print architecture
    logger.info(f"Architecture:\n{model}")
    
    # Training setup
    criterion = nn.MSELoss()
    optimizer = Adam(model.parameters(), lr=LEARNING_RATE)
    
    # Training loop
    logger.info("-" * 80)
    logger.info("Starting training...")
    logger.info("-" * 80)
    
    history = {
        'train_loss': [],
        'test_loss': [],
        'test_mae': [],
        'test_rmse': [],
        'test_mape': [],
        'test_r2': []
    }
    
    best_test_loss = float('inf')
    patience_counter = 0
    best_epoch = 0
    
    for epoch in range(EPOCHS):
        # Train
        train_loss = train_epoch(model, train_loader, criterion, optimizer, DEVICE)
        
        # Evaluate
        test_loss, mae, rmse, mape, r2 = evaluate(model, test_loader, criterion, DEVICE)
        
        # Record
        history['train_loss'].append(train_loss)
        history['test_loss'].append(test_loss)
        history['test_mae'].append(mae)
        history['test_rmse'].append(rmse)
        history['test_mape'].append(mape)
        history['test_r2'].append(r2)
        
        # Logging
        logger.info(f"Epoch {epoch+1}/{EPOCHS} | "
                   f"Train Loss: {train_loss:.6f} | "
                   f"Test Loss: {test_loss:.6f} | "
                   f"MAE: {mae:.6f} | "
                   f"RMSE: {rmse:.6f} | "
                   f"MAPE: {mape:.2f}% | "
                   f"R²: {r2:.6f}")
        
        # Early stopping
        if test_loss < best_test_loss:
            best_test_loss = test_loss
            best_epoch = epoch + 1
            patience_counter = 0
            
            # Save best model
            best_model_path = MODEL_DIR / 'workload_predictor_v1.pt'
            torch.save(model.state_dict(), best_model_path)
            logger.info(f"✓ Best model saved at epoch {best_epoch}")
        else:
            patience_counter += 1
            if patience_counter >= EARLY_STOPPING_PATIENCE:
                logger.info(f"Early stopping triggered at epoch {epoch+1} "
                           f"(best: epoch {best_epoch} with loss {best_test_loss:.6f})")
                break
    
    # Save final model and history
    logger.info("-" * 80)
    logger.info("Saving results...")
    logger.info("-" * 80)
    
    final_model_path = MODEL_DIR / 'workload_predictor_v1.pt'
    torch.save(model.state_dict(), final_model_path)
    logger.info(f"Model saved to: {final_model_path}")
    logger.info(f"Model file size: {final_model_path.stat().st_size / 1e6:.2f} MB")
    
    # Save history
    with open(RESULTS_DIR / 'training_history.pkl', 'wb') as f:
        pickle.dump(history, f)
    
    # Plot training history
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    axes[0, 0].plot(history['train_loss'], label='Train Loss')
    axes[0, 0].plot(history['test_loss'], label='Test Loss')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss (MSE)')
    axes[0, 0].set_title('Training and Test Loss')
    axes[0, 0].legend()
    axes[0, 0].grid(True)
    
    axes[0, 1].plot(history['test_mae'])
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].set_ylabel('MAE')
    axes[0, 1].set_title('Mean Absolute Error')
    axes[0, 1].grid(True)
    
    axes[0, 2].plot(history['test_rmse'])
    axes[0, 2].set_xlabel('Epoch')
    axes[0, 2].set_ylabel('RMSE')
    axes[0, 2].set_title('Root Mean Squared Error')
    axes[0, 2].grid(True)
    
    axes[1, 0].plot(history['test_mape'])
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].set_ylabel('MAPE (%)')
    axes[1, 0].set_title('Mean Absolute Percentage Error')
    axes[1, 0].grid(True)
    
    axes[1, 1].plot(history['test_r2'])
    axes[1, 1].set_xlabel('Epoch')
    axes[1, 1].set_ylabel('R²')
    axes[1, 1].set_title('Coefficient of Determination')
    axes[1, 1].grid(True)
    axes[1, 1].set_ylim([0, 1])
    
    axes[1, 2].axis('off')
    summary_text = f"""
    TRAINING SUMMARY
    
    Total Epochs: {len(history['train_loss'])}
    Best Epoch: {best_epoch}
    
    Final Metrics:
    Train Loss: {history['train_loss'][-1]:.6f}
    Test Loss: {history['test_loss'][-1]:.6f}
    MAE: {history['test_mae'][-1]:.6f}
    RMSE: {history['test_rmse'][-1]:.6f}
    MAPE: {history['test_mape'][-1]:.2f}%
    R²: {history['test_r2'][-1]:.6f}
    
    Best Test Loss: {best_test_loss:.6f}
    """
    axes[1, 2].text(0.1, 0.5, summary_text, fontfamily='monospace', fontsize=10)
    
    plt.tight_layout()
    plot_path = RESULTS_DIR / 'training_history.png'
    plt.savefig(plot_path, dpi=100)
    logger.info(f"Training plot saved to: {plot_path}")
    plt.close()
    
    # Final summary
    logger.info("=" * 80)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Training samples: {X_train.shape[0]:,}")
    logger.info(f"Test samples: {X_test.shape[0]:,}")
    logger.info(f"Best epoch: {best_epoch}")
    logger.info(f"Best test loss: {best_test_loss:.6f}")
    logger.info(f"Final R² score: {history['test_r2'][-1]:.6f}")
    logger.info(f"Final MAPE: {history['test_mape'][-1]:.2f}%")
    logger.info(f"Trained model: {final_model_path}")
    logger.info(f"Results directory: {RESULTS_DIR.absolute()}")


if __name__ == '__main__':
    main()
