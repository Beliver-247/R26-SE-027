"""
Train LSTM model for CPU workload prediction using PyTorch.
Part of Green DevOps Operation Phase system.
"""

import os
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Dict
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set device
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logger.info(f"Using device: {DEVICE}")


def load_preprocessed_data(data_dir: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Load preprocessed LSTM sequences from .npy files.
    
    Args:
        data_dir: Directory containing X_train.npy, X_test.npy, y_train.npy, y_test.npy
        
    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    data_path = Path(data_dir)
    
    if not data_path.exists():
        logger.error(f"Data directory not found: {data_dir}")
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    logger.info(f"Loading preprocessed data from: {data_dir}")
    
    try:
        X_train = np.load(data_path / 'X_train.npy')
        X_test = np.load(data_path / 'X_test.npy')
        y_train = np.load(data_path / 'y_train.npy')
        y_test = np.load(data_path / 'y_test.npy')
        
        logger.info("Data loaded successfully")
        
        return X_train, X_test, y_train, y_test
        
    except FileNotFoundError as e:
        logger.error(f"Error loading data files: {e}")
        raise


def print_data_shapes(X_train: np.ndarray, X_test: np.ndarray, 
                      y_train: np.ndarray, y_test: np.ndarray) -> None:
    """
    Print data shapes and summary.
    
    Args:
        X_train: Training features
        X_test: Test features
        y_train: Training targets
        y_test: Test targets
    """
    logger.info("="*80)
    logger.info("DATA SHAPES AND SUMMARY")
    logger.info("="*80)
    logger.info(f"X_train shape: {X_train.shape} (samples, timesteps, features)")
    logger.info(f"X_test shape:  {X_test.shape}")
    logger.info(f"y_train shape: {y_train.shape} (samples,)")
    logger.info(f"y_test shape:  {y_test.shape}")
    
    logger.info(f"\nData statistics:")
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Test samples: {len(X_test)}")
    logger.info(f"Timesteps per sample: {X_train.shape[1]}")
    logger.info(f"Features per timestep: {X_train.shape[2]}")
    
    logger.info(f"\nTarget (y) statistics:")
    logger.info(f"y_train - Min: {y_train.min():.4f}, Max: {y_train.max():.4f}, Mean: {y_train.mean():.4f}")
    logger.info(f"y_test  - Min: {y_test.min():.4f}, Max: {y_test.max():.4f}, Mean: {y_test.mean():.4f}")
    logger.info("="*80 + "\n")


class LSTMWorkloadPredictor(nn.Module):
    """LSTM model for CPU workload prediction."""
    
    def __init__(self, input_size: int, hidden_size_1: int = 64, hidden_size_2: int = 32):
        """
        Initialize LSTM model.
        
        Args:
            input_size: Number of input features (2: CPU, memory)
            hidden_size_1: First LSTM layer hidden size (64)
            hidden_size_2: Second LSTM layer hidden size (32)
        """
        super(LSTMWorkloadPredictor, self).__init__()
        
        self.lstm1 = nn.LSTM(input_size, hidden_size_1, batch_first=True)
        self.dropout1 = nn.Dropout(0.2)
        
        self.lstm2 = nn.LSTM(hidden_size_1, hidden_size_2, batch_first=True)
        self.dropout2 = nn.Dropout(0.2)
        
        self.dense = nn.Linear(hidden_size_2, 16)
        self.relu = nn.ReLU()
        
        self.output = nn.Linear(16, 1)
    
    def forward(self, x):
        """Forward pass through model."""
        # First LSTM layer
        x, _ = self.lstm1(x)
        x = self.dropout1(x)
        
        # Second LSTM layer - take only last output
        x, _ = self.lstm2(x)
        x = self.dropout2(x)
        x = x[:, -1, :]  # Take last timestep
        
        # Dense layers
        x = self.dense(x)
        x = self.relu(x)
        
        # Output layer
        x = self.output(x)
        
        return x


def build_model(input_size: int) -> nn.Module:
    """
    Build and return LSTM model.
    
    Args:
        input_size: Number of input features
        
    Returns:
        Initialized LSTM model
    """
    logger.info("Building LSTM model...")
    
    model = LSTMWorkloadPredictor(input_size=input_size)
    model.to(DEVICE)
    
    logger.info("Model architecture:")
    logger.info(f"  - LSTM Layer 1: {input_size} → 64 units")
    logger.info(f"  - Dropout: 0.2")
    logger.info(f"  - LSTM Layer 2: 64 → 32 units")
    logger.info(f"  - Dropout: 0.2")
    logger.info(f"  - Dense Layer: 32 → 16 units (ReLU)")
    logger.info(f"  - Output Layer: 16 → 1 unit")
    logger.info(f"  - Device: {DEVICE}\n")
    
    return model


def train_model(model: nn.Module, train_loader: DataLoader, test_loader: DataLoader,
                epochs: int = 50, learning_rate: float = 0.001) -> Dict:
    """
    Train LSTM model.
    
    Args:
        model: PyTorch model to train
        train_loader: Training data loader
        test_loader: Test data loader
        epochs: Number of training epochs
        learning_rate: Learning rate for optimizer
        
    Returns:
        History dictionary with training metrics
    """
    logger.info("="*80)
    logger.info("TRAINING MODEL")
    logger.info("="*80)
    logger.info(f"Epochs: {epochs}")
    logger.info(f"Learning rate: {learning_rate}")
    logger.info(f"Training batches: {len(train_loader)}")
    logger.info(f"Test batches: {len(test_loader)}\n")
    
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    history = {
        'train_loss': [],
        'val_loss': [],
        'train_mae': [],
        'val_mae': []
    }
    
    best_val_loss = float('inf')
    patience = 5
    patience_counter = 0
    
    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_mae = 0.0
        train_batches = 0
        
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(DEVICE)
            y_batch = y_batch.to(DEVICE).unsqueeze(1)
            
            optimizer.zero_grad()
            y_pred = model(X_batch)
            
            loss = criterion(y_pred, y_batch)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            train_mae += torch.abs(y_pred - y_batch).mean().item()
            train_batches += 1
        
        train_loss /= train_batches
        train_mae /= train_batches
        history['train_loss'].append(train_loss)
        history['train_mae'].append(train_mae)
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        val_mae = 0.0
        val_batches = 0
        
        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                X_batch = X_batch.to(DEVICE)
                y_batch = y_batch.to(DEVICE).unsqueeze(1)
                
                y_pred = model(X_batch)
                loss = criterion(y_pred, y_batch)
                
                val_loss += loss.item()
                val_mae += torch.abs(y_pred - y_batch).mean().item()
                val_batches += 1
        
        val_loss /= val_batches
        val_mae /= val_batches
        history['val_loss'].append(val_loss)
        history['val_mae'].append(val_mae)
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info(f"Epoch {epoch+1}/{epochs} - "
                       f"Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}, "
                       f"MAE: {train_mae:.6f}, Val MAE: {val_mae:.6f}")
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break
    
    logger.info("\n" + "="*80)
    logger.info("TRAINING COMPLETE")
    logger.info("="*80 + "\n")
    
    return history


def evaluate_model(model: nn.Module, test_loader: DataLoader, 
                   y_test: np.ndarray) -> Dict[str, float]:
    """
    Evaluate model on test set.
    
    Args:
        model: Trained model
        test_loader: Test data loader
        y_test: Test targets (for statistics)
        
    Returns:
        Dictionary with evaluation metrics
    """
    logger.info("="*80)
    logger.info("MODEL EVALUATION")
    logger.info("="*80)
    
    model.eval()
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(DEVICE)
            y_batch = y_batch.to(DEVICE)
            
            y_pred = model(X_batch)
            
            all_preds.append(y_pred.cpu().numpy())
            all_targets.append(y_batch.cpu().numpy())
    
    y_pred_all = np.concatenate(all_preds).flatten()
    y_targets_all = np.concatenate(all_targets).flatten()
    
    # Calculate metrics
    mse = np.mean((y_targets_all - y_pred_all) ** 2)
    mae = np.mean(np.abs(y_targets_all - y_pred_all))
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((y_targets_all - y_pred_all) / y_targets_all)) * 100
    
    ss_res = np.sum((y_targets_all - y_pred_all) ** 2)
    ss_tot = np.sum((y_targets_all - np.mean(y_targets_all)) ** 2)
    r2_score = 1 - (ss_res / ss_tot)
    
    logger.info(f"Test MSE: {mse:.6f}")
    logger.info(f"Test MAE: {mae:.6f}")
    logger.info(f"Test RMSE: {rmse:.6f}")
    logger.info(f"Test MAPE: {mape:.2f}%")
    logger.info(f"Test R² Score: {r2_score:.6f}")
    logger.info("="*80 + "\n")
    
    metrics = {
        'test_mse': mse,
        'test_mae': mae,
        'test_rmse': rmse,
        'test_mape': mape,
        'test_r2': r2_score
    }
    
    return metrics


def save_model(model: nn.Module, output_path: str) -> None:
    """
    Save trained model.
    
    Args:
        model: Trained model
        output_path: Path to save model
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving model to: {output_path}")
    
    torch.save(model.state_dict(), output_path)
    
    logger.info(f"Model saved successfully")
    logger.info(f"File size: {output_file.stat().st_size / (1024*1024):.2f} MB\n")


def plot_training_history(history: Dict, output_dir: str) -> None:
    """
    Plot and save training history.
    
    Args:
        history: Training history dictionary
        output_dir: Directory to save plots
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Generating training plots...")
    
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history['train_loss'], label='Training Loss (MSE)', linewidth=2)
    plt.plot(history['val_loss'], label='Validation Loss (MSE)', linewidth=2)
    plt.title('Model Loss Over Epochs', fontsize=12, fontweight='bold')
    plt.xlabel('Epoch', fontsize=10)
    plt.ylabel('Loss (MSE)', fontsize=10)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(history['train_mae'], label='Training MAE', linewidth=2)
    plt.plot(history['val_mae'], label='Validation MAE', linewidth=2)
    plt.title('Model MAE Over Epochs', fontsize=12, fontweight='bold')
    plt.xlabel('Epoch', fontsize=10)
    plt.ylabel('MAE', fontsize=10)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = output_path / 'training_history.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    logger.info(f"Plot saved to: {plot_file}")
    
    plt.close()


def main():
    """Main execution block."""
    
    # Configuration
    DATA_DIR = r"D:\Research\Operation\green-devops-operation-component\data\preprocessed\global"
    MODEL_OUTPUT_PATH = r"D:\Research\Operation\green-devops-operation-component\models\trained\workload_predictor_v1.pt"
    PLOTS_OUTPUT_DIR = r"D:\Research\Operation\green-devops-operation-component\data\results"
    
    EPOCHS = 50
    BATCH_SIZE = 32
    LEARNING_RATE = 0.001
    
    try:
        logger.info("="*80)
        logger.info("LSTM WORKLOAD PREDICTION MODEL TRAINING")
        logger.info("="*80 + "\n")
        
        # Load data
        X_train, X_test, y_train, y_test = load_preprocessed_data(DATA_DIR)
        
        # Print data shapes
        print_data_shapes(X_train, X_test, y_train, y_test)
        
        # Convert to PyTorch tensors
        X_train_tensor = torch.from_numpy(X_train).float()
        X_test_tensor = torch.from_numpy(X_test).float()
        y_train_tensor = torch.from_numpy(y_train).float()
        y_test_tensor = torch.from_numpy(y_test).float()
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        test_dataset = TensorDataset(X_test_tensor, y_test_tensor)
        
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
        
        # Build model
        input_size = X_train.shape[2]
        model = build_model(input_size)
        
        # Train model
        history = train_model(
            model, train_loader, test_loader,
            epochs=EPOCHS,
            learning_rate=LEARNING_RATE
        )
        
        # Evaluate model
        metrics = evaluate_model(model, test_loader, y_test)
        
        # Save model
        save_model(model, MODEL_OUTPUT_PATH)
        
        # Plot training history
        plot_training_history(history, PLOTS_OUTPUT_DIR)
        
        logger.info("="*80)
        logger.info("TRAINING PIPELINE COMPLETE")
        logger.info("="*80)
        logger.info(f"Model saved to: {MODEL_OUTPUT_PATH}")
        logger.info(f"Plots saved to: {PLOTS_OUTPUT_DIR}")
        logger.info("="*80)
        
        return model, history, metrics
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    model, history, metrics = main()



def load_preprocessed_data(data_dir: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Load preprocessed LSTM sequences from .npy files.
    
    Args:
        data_dir: Directory containing X_train.npy, X_test.npy, y_train.npy, y_test.npy
        
    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    data_path = Path(data_dir)
    
    if not data_path.exists():
        logger.error(f"Data directory not found: {data_dir}")
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    logger.info(f"Loading preprocessed data from: {data_dir}")
    
    try:
        X_train = np.load(data_path / 'X_train.npy')
        X_test = np.load(data_path / 'X_test.npy')
        y_train = np.load(data_path / 'y_train.npy')
        y_test = np.load(data_path / 'y_test.npy')
        
        logger.info("Data loaded successfully")
        
        return X_train, X_test, y_train, y_test
        
    except FileNotFoundError as e:
        logger.error(f"Error loading data files: {e}")
        raise


def print_data_shapes(X_train: np.ndarray, X_test: np.ndarray, 
                      y_train: np.ndarray, y_test: np.ndarray) -> None:
    """
    Print data shapes and summary.
    
    Args:
        X_train: Training features
        X_test: Test features
        y_train: Training targets
        y_test: Test targets
    """
    logger.info("="*80)
    logger.info("DATA SHAPES AND SUMMARY")
    logger.info("="*80)
    logger.info(f"X_train shape: {X_train.shape} (samples, timesteps, features)")
    logger.info(f"X_test shape:  {X_test.shape}")
    logger.info(f"y_train shape: {y_train.shape} (samples,)")
    logger.info(f"y_test shape:  {y_test.shape}")
    
    logger.info(f"\nData statistics:")
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Test samples: {len(X_test)}")
    logger.info(f"Timesteps per sample: {X_train.shape[1]}")
    logger.info(f"Features per timestep: {X_train.shape[2]}")
    
    logger.info(f"\nTarget (y) statistics:")
    logger.info(f"y_train - Min: {y_train.min():.4f}, Max: {y_train.max():.4f}, Mean: {y_train.mean():.4f}")
    logger.info(f"y_test  - Min: {y_test.min():.4f}, Max: {y_test.max():.4f}, Mean: {y_test.mean():.4f}")
    logger.info("="*80 + "\n")


def build_lstm_model(input_shape: Tuple[int, int]) -> models.Model:
    """
    Build LSTM model for workload prediction.
    
    Args:
        input_shape: Tuple of (timesteps, features)
        
    Returns:
        Compiled Keras model
    """
    logger.info("Building LSTM model...")
    
    model = models.Sequential([
        # First LSTM layer with 64 units
        layers.LSTM(64, activation='relu', return_sequences=True, input_shape=input_shape),
        layers.Dropout(0.2),
        
        # Second LSTM layer with 32 units
        layers.LSTM(32, activation='relu', return_sequences=False),
        layers.Dropout(0.2),
        
        # Dense layer with 16 units
        layers.Dense(16, activation='relu'),
        
        # Output layer for CPU prediction
        layers.Dense(1)
    ])
    
    logger.info("Model architecture:")
    model.summary(print_fn=lambda x: logger.info(x))
    
    return model


def compile_model(model: models.Model) -> None:
    """
    Compile model with specified loss and optimizer.
    
    Args:
        model: Keras model to compile
    """
    logger.info("Compiling model...")
    
    model.compile(
        loss='mse',
        optimizer=Adam(learning_rate=0.001),
        metrics=['mae']
    )
    
    logger.info("Model compiled with:")
    logger.info("  Loss: Mean Squared Error (MSE)")
    logger.info("  Optimizer: Adam (lr=0.001)")
    logger.info("  Metrics: Mean Absolute Error (MAE)\n")


def train_model(model: models.Model, X_train: np.ndarray, y_train: np.ndarray,
                X_test: np.ndarray, y_test: np.ndarray, 
                epochs: int = 50, batch_size: int = 32) -> keras.callbacks.History:
    """
    Train LSTM model with early stopping.
    
    Args:
        model: Compiled Keras model
        X_train: Training features
        y_train: Training targets
        X_test: Test features
        y_test: Test targets
        epochs: Maximum number of epochs
        batch_size: Batch size for training
        
    Returns:
        Training history object
    """
    logger.info("="*80)
    logger.info("TRAINING MODEL")
    logger.info("="*80)
    logger.info(f"Epochs: {epochs}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Validation samples: {len(X_test)}\n")
    
    # Define callbacks
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True
    )
    
    # Train model
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_test, y_test),
        callbacks=[early_stop],
        verbose=1
    )
    
    logger.info("\n" + "="*80)
    logger.info("TRAINING COMPLETE")
    logger.info("="*80 + "\n")
    
    return history


def evaluate_model(model: models.Model, X_test: np.ndarray, 
                   y_test: np.ndarray) -> Dict[str, float]:
    """
    Evaluate model on test set and calculate metrics.
    
    Args:
        model: Trained Keras model
        X_test: Test features
        y_test: Test targets
        
    Returns:
        Dictionary with evaluation metrics
    """
    logger.info("="*80)
    logger.info("MODEL EVALUATION")
    logger.info("="*80)
    
    # Evaluate on test set
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    
    logger.info(f"Test Loss (MSE): {test_loss:.6f}")
    logger.info(f"Test MAE: {test_mae:.6f}")
    
    # Make predictions
    y_pred = model.predict(X_test, verbose=0)
    y_pred = y_pred.flatten()
    
    # Calculate RMSE
    rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
    logger.info(f"Test RMSE: {rmse:.6f}")
    
    # Calculate additional metrics
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    logger.info(f"Test MAPE: {mape:.2f}%")
    
    # Calculate R² score
    ss_res = np.sum((y_test - y_pred) ** 2)
    ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
    r2_score = 1 - (ss_res / ss_tot)
    logger.info(f"Test R² Score: {r2_score:.6f}")
    
    logger.info("="*80 + "\n")
    
    metrics = {
        'test_loss': test_loss,
        'test_mae': test_mae,
        'test_rmse': rmse,
        'test_mape': mape,
        'test_r2': r2_score
    }
    
    return metrics


def save_model(model: models.Model, output_path: str) -> None:
    """
    Save trained model to file.
    
    Args:
        model: Trained Keras model
        output_path: Path to save model
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving model to: {output_path}")
    
    model.save(output_path)
    
    logger.info(f"Model saved successfully")
    logger.info(f"File size: {output_file.stat().st_size / (1024*1024):.2f} MB\n")


def plot_training_history(history: keras.callbacks.History, output_dir: str) -> None:
    """
    Plot and save training history.
    
    Args:
        history: Training history object
        output_dir: Directory to save plots
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Generating training plots...")
    
    # Plot loss
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Training Loss (MSE)', linewidth=2)
    plt.plot(history.history['val_loss'], label='Validation Loss (MSE)', linewidth=2)
    plt.title('Model Loss Over Epochs', fontsize=12, fontweight='bold')
    plt.xlabel('Epoch', fontsize=10)
    plt.ylabel('Loss (MSE)', fontsize=10)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    # Plot MAE
    plt.subplot(1, 2, 2)
    plt.plot(history.history['mae'], label='Training MAE', linewidth=2)
    plt.plot(history.history['val_mae'], label='Validation MAE', linewidth=2)
    plt.title('Model MAE Over Epochs', fontsize=12, fontweight='bold')
    plt.xlabel('Epoch', fontsize=10)
    plt.ylabel('MAE', fontsize=10)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = output_path / 'training_history.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    logger.info(f"Plot saved to: {plot_file}")
    
    plt.close()


def main():
    """Main execution block."""
    
    # Configuration
    DATA_DIR = r"D:\Research\Operation\green-devops-operation-component\data\preprocessed\global"
    MODEL_OUTPUT_PATH = r"D:\Research\Operation\green-devops-operation-component\models\trained\workload_predictor_v1.h5"
    PLOTS_OUTPUT_DIR = r"D:\Research\Operation\green-devops-operation-component\data\results"
    
    EPOCHS = 50
    BATCH_SIZE = 32
    
    try:
        logger.info("="*80)
        logger.info("LSTM WORKLOAD PREDICTION MODEL TRAINING")
        logger.info("="*80 + "\n")
        
        # Load data
        X_train, X_test, y_train, y_test = load_preprocessed_data(DATA_DIR)
        
        # Print data shapes
        print_data_shapes(X_train, X_test, y_train, y_test)
        
        # Build model
        input_shape = (X_train.shape[1], X_train.shape[2])
        model = build_lstm_model(input_shape)
        
        # Compile model
        compile_model(model)
        
        # Train model
        history = train_model(
            model, X_train, y_train, X_test, y_test,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE
        )
        
        # Evaluate model
        metrics = evaluate_model(model, X_test, y_test)
        
        # Save model
        save_model(model, MODEL_OUTPUT_PATH)
        
        # Plot training history
        plot_training_history(history, PLOTS_OUTPUT_DIR)
        
        logger.info("="*80)
        logger.info("TRAINING PIPELINE COMPLETE")
        logger.info("="*80)
        logger.info(f"Model saved to: {MODEL_OUTPUT_PATH}")
        logger.info(f"Plots saved to: {PLOTS_OUTPUT_DIR}")
        logger.info("="*80)
        
        return model, history, metrics
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    model, history, metrics = main()
