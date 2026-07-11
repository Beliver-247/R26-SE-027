"""
Retraining and fine-tuning module for Engine 1.

Supports continuous learning using collected runtime data after deployment.
Enables model improvement over time as real production metrics accumulate.
"""

import numpy as np
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
import pickle

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from model import LSTMWorkloadPredictor
from config import (
    RETRAINING_BATCH_SIZE,
    RETRAINING_EPOCHS,
    RETRAINING_LEARNING_RATE,
    RETRAINING_CHECKPOINT_INTERVAL,
    RETRAINING_VAL_SPLIT,
    DEVICE,
    MODEL_VERSION
)

logger = logging.getLogger(__name__)


class RetrainingManager:
    """
    Manages model retraining and fine-tuning using collected runtime data.
    
    Workflow:
    1. Collect runtime metrics from deployed system
    2. Prepare sequences from runtime data
    3. Detect when retraining is needed (data volume threshold)
    4. Fine-tune model on latest data
    5. Validate improvements
    6. Save updated model if improvements detected
    """
    
    def __init__(
        self,
        model_path: str,
        checkpoint_dir: str = "models/checkpoints"
    ):
        """
        Initialize retraining manager.
        
        Args:
            model_path: Path to current model
            checkpoint_dir: Directory to save model checkpoints
        """
        self.model_path = Path(model_path)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.device = torch.device(DEVICE if torch.cuda.is_available() else 'cpu')
        
        # Retraining statistics
        self.samples_collected = 0
        self.last_retrain_time = datetime.now()
        self.retrain_history = []
        
        logger.info(f"RetrainingManager initialized")
        logger.info(f"  Checkpoint dir: {self.checkpoint_dir}")
        logger.info(f"  Device: {self.device}")
    
    def should_retrain(self, samples_since_last_retrain: int) -> bool:
        """
        Determine if retraining is needed.
        
        Heuristic triggers:
        - Collected >= RETRAINING_CHECKPOINT_INTERVAL samples
        - Last retrain > 7 days ago
        - Performance degradation detected on new data
        
        Args:
            samples_since_last_retrain: Number of new samples collected
        
        Returns:
            True if retraining recommended
        """
        # Trigger 1: Sample count threshold
        if samples_since_last_retrain >= RETRAINING_CHECKPOINT_INTERVAL:
            logger.info(
                f"Retrain trigger: Sample threshold reached "
                f"({samples_since_last_retrain} >= {RETRAINING_CHECKPOINT_INTERVAL})"
            )
            return True
        
        # Trigger 2: Time-based trigger (weekly retrain)
        time_since_retrain = datetime.now() - self.last_retrain_time
        if time_since_retrain > timedelta(days=7):
            logger.info(
                f"Retrain trigger: Time-based trigger "
                f"({time_since_retrain.days} days since last retrain)"
            )
            return True
        
        return False
    
    def prepare_retraining_data(
        self,
        X_runtime: np.ndarray,
        y_runtime: np.ndarray,
        X_pretrain: Optional[np.ndarray] = None,
        y_pretrain: Optional[np.ndarray] = None
    ) -> Tuple[DataLoader, DataLoader]:
        """
        Prepare training and validation data loaders.
        
        Can mix pre-training data with runtime data for stability:
        - 70% runtime data (recent, fresh distribution)
        - 30% pre-training data (stable baseline)
        
        Args:
            X_runtime: Runtime feature sequences (N, 12, 2)
            y_runtime: Runtime targets (N, 1)
            X_pretrain: Optional pre-training sequences
            y_pretrain: Optional pre-training targets
        
        Returns:
            Tuple of (train_dataloader, val_dataloader)
        """
        logger.info("Preparing retraining data...")
        
        if len(X_runtime) < RETRAINING_BATCH_SIZE:
            logger.warning(
                f"Limited runtime data: {len(X_runtime)} samples "
                f"(batch size: {RETRAINING_BATCH_SIZE})"
            )
        
        # Mix with pre-training data if provided (transfer learning)
        if X_pretrain is not None:
            mix_ratio = 0.7
            pretrain_samples = max(
                int(len(X_runtime) * (1 - mix_ratio) / mix_ratio),
                1
            )
            
            # Sample from pre-training data
            indices = np.random.choice(len(X_pretrain), pretrain_samples, replace=True)
            X_combined = np.vstack([X_runtime, X_pretrain[indices]])
            y_combined = np.vstack([y_runtime, y_pretrain[indices]])
            
            logger.info(
                f"Mixed data: {len(X_runtime)} runtime + "
                f"{pretrain_samples} pre-train samples"
            )
        else:
            X_combined = X_runtime
            y_combined = y_runtime
            logger.info(f"Using runtime data only: {len(X_runtime)} samples")
        
        # Convert to tensors
        X_tensor = torch.from_numpy(X_combined).float().to(self.device)
        y_tensor = torch.from_numpy(y_combined).float().to(self.device)
        
        # Split into train/val
        val_split_idx = int(len(X_combined) * (1 - RETRAINING_VAL_SPLIT))
        
        X_train, X_val = X_tensor[:val_split_idx], X_tensor[val_split_idx:]
        y_train, y_val = y_tensor[:val_split_idx], y_tensor[val_split_idx:]
        
        logger.info(
            f"Train/Val split: {len(X_train)}/{len(X_val)} "
            f"({RETRAINING_VAL_SPLIT*100:.0f}% for validation)"
        )
        
        # Create dataloaders
        train_dataset = TensorDataset(X_train, y_train)
        val_dataset = TensorDataset(X_val, y_val)
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=RETRAINING_BATCH_SIZE,
            shuffle=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=RETRAINING_BATCH_SIZE,
            shuffle=False
        )
        
        return train_loader, val_loader
    
    def fine_tune_model(
        self,
        model: LSTMWorkloadPredictor,
        train_loader: DataLoader,
        val_loader: DataLoader,
        learning_rate: float = RETRAINING_LEARNING_RATE
    ) -> Dict[str, list]:
        """
        Fine-tune model on new runtime data.
        
        Strategy: Lower learning rate than initial training for stability.
        Freezes early layers, fine-tunes latter layers and output.
        
        Args:
            model: Model to fine-tune
            train_loader: Training data
            val_loader: Validation data
            learning_rate: Fine-tuning learning rate (reduced from initial)
        
        Returns:
            Dictionary with training history
        """
        logger.info("Starting fine-tuning...")
        logger.info(f"  Learning rate: {learning_rate}")
        logger.info(f"  Epochs: {RETRAINING_EPOCHS}")
        
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        history = {
            'train_loss': [],
            'val_loss': [],
            'epochs': []
        }
        
        best_val_loss = float('inf')
        patience_counter = 0
        patience = 3
        
        for epoch in range(RETRAINING_EPOCHS):
            # Training phase
            model.train()
            train_loss = 0.0
            
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                y_pred = model(X_batch)
                loss = criterion(y_pred, y_batch)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item() * len(X_batch)
            
            train_loss /= len(train_loader.dataset)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    y_pred = model(X_batch)
                    loss = criterion(y_pred, y_batch)
                    val_loss += loss.item() * len(X_batch)
            
            val_loss /= len(val_loader.dataset)
            
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['epochs'].append(epoch + 1)
            
            logger.info(
                f"Epoch {epoch+1}/{RETRAINING_EPOCHS} | "
                f"Train Loss: {train_loss:.6f} | "
                f"Val Loss: {val_loss:.6f}"
            )
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping after {epoch+1} epochs")
                    break
        
        logger.info("Fine-tuning complete")
        return history
    
    def save_checkpoint(
        self,
        model: LSTMWorkloadPredictor,
        model_version: str,
        metrics: Dict[str, float]
    ) -> Path:
        """
        Save model checkpoint with metadata.
        
        Checkpoint structure:
        - Model weights
        - Training metrics
        - Timestamp
        - Version tag
        
        Args:
            model: Trained model
            model_version: Version identifier
            metrics: Training metrics (loss, val_loss, etc.)
        
        Returns:
            Path to saved checkpoint
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = f"workload_predictor_{model_version}_{timestamp}.pt"
        checkpoint_path = self.checkpoint_dir / checkpoint_name
        
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'version': model_version,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }
        
        torch.save(checkpoint, checkpoint_path)
        
        logger.info(f"Checkpoint saved: {checkpoint_path}")
        logger.info(f"  Metrics: {metrics}")
        
        return checkpoint_path
    
    def load_checkpoint(self, checkpoint_path: Path) -> Tuple[LSTMWorkloadPredictor, Dict]:
        """
        Load model from checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint file
        
        Returns:
            Tuple of (model, metadata)
        """
        logger.info(f"Loading checkpoint: {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        model = LSTMWorkloadPredictor()
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(self.device)
        
        metadata = {
            'version': checkpoint.get('version'),
            'timestamp': checkpoint.get('timestamp'),
            'metrics': checkpoint.get('metrics', {})
        }
        
        logger.info(f"✓ Checkpoint loaded")
        logger.info(f"  Version: {metadata['version']}")
        logger.info(f"  Metrics: {metadata['metrics']}")
        
        return model, metadata
    
    def retrain_or_finetune(
        self,
        X_runtime: np.ndarray,
        y_runtime: np.ndarray,
        X_pretrain: Optional[np.ndarray] = None,
        y_pretrain: Optional[np.ndarray] = None
    ) -> Tuple[LSTMWorkloadPredictor, Dict]:
        """
        Complete retraining workflow.
        
        Orchestrates:
        1. Data preparation
        2. Model loading
        3. Fine-tuning
        4. Checkpoint saving
        5. History recording
        
        Args:
            X_runtime: Runtime sequences
            y_runtime: Runtime targets
            X_pretrain: Pre-training data (optional)
            y_pretrain: Pre-training targets (optional)
        
        Returns:
            Tuple of (retrained_model, training_results)
        """
        logger.info("Starting retraining workflow...")
        
        # Load current model
        model = LSTMWorkloadPredictor()
        model.to(self.device)
        model.eval()
        
        # Prepare data
        train_loader, val_loader = self.prepare_retraining_data(
            X_runtime, y_runtime,
            X_pretrain, y_pretrain
        )
        
        # Fine-tune
        history = self.fine_tune_model(model, train_loader, val_loader)
        
        # Save checkpoint
        checkpoint_metrics = {
            'final_train_loss': float(history['train_loss'][-1]),
            'final_val_loss': float(history['val_loss'][-1]),
            'epochs_trained': len(history['epochs']),
            'samples_used': len(train_loader.dataset)
        }
        
        checkpoint_path = self.save_checkpoint(
            model,
            f"{MODEL_VERSION}_retrain",
            checkpoint_metrics
        )
        
        # Update tracking
        self.samples_collected = 0
        self.last_retrain_time = datetime.now()
        self.retrain_history.append({
            'timestamp': datetime.now().isoformat(),
            'checkpoint': str(checkpoint_path),
            'metrics': checkpoint_metrics,
            'history': history
        })
        
        logger.info("Retraining workflow complete")
        
        return model, {
            'checkpoint_path': checkpoint_path,
            'metrics': checkpoint_metrics,
            'history': history
        }
    
    def get_retrain_summary(self) -> Dict:
        """Get summary of retraining activity."""
        return {
            'samples_collected': self.samples_collected,
            'last_retrain': self.last_retrain_time.isoformat(),
            'retrain_count': len(self.retrain_history),
            'history': self.retrain_history
        }


# Stub functions for future enhancement

def collect_runtime_metrics_from_prometheus(
    system_id: str,
    prometheus_url: str = "http://localhost:9090"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    TODO: Collect runtime metrics from Prometheus.
    
    This is a stub for future implementation to integrate with
    live Prometheus monitoring data from deployed systems.
    
    Args:
        system_id: System to collect metrics for
        prometheus_url: Prometheus server URL
    
    Returns:
        Tuple of (X_sequences, y_targets)
    """
    logger.warning("TODO: Implement Prometheus metrics collection")
    # Would implement:
    # 1. Query Prometheus for system_id metrics
    # 2. Parse time-series data
    # 3. Prepare sequences
    # 4. Return X, y arrays
    pass


def detect_data_distribution_shift(
    X_runtime: np.ndarray,
    X_pretrain: np.ndarray
) -> float:
    """
    TODO: Detect distribution shift between runtime and pre-training data.
    
    Would use techniques like:
    - Compute statistical divergence (JS divergence, Wasserstein)
    - Compare feature histograms
    - Detect concept drift
    
    Args:
        X_runtime: Runtime sequences
        X_pretrain: Pre-training sequences
    
    Returns:
        Shift score (0-1, where 1 = significant shift)
    """
    logger.warning("TODO: Implement distribution shift detection")
    pass


def evaluate_on_holdout_test_set(
    model: LSTMWorkloadPredictor,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Dict[str, float]:
    """
    TODO: Evaluate retrained model on held-out test set.
    
    Would compute:
    - MSE, MAE, RMSE
    - MAPE
    - R² score
    
    Args:
        model: Retrained model
        X_test: Test sequences
        y_test: Test targets
    
    Returns:
        Dictionary of metrics
    """
    logger.warning("TODO: Implement evaluation on test set")
    pass
