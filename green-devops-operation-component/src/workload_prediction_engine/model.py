"""
PyTorch LSTM model architecture for workload prediction.
Engine 1 - Workload Prediction Module.

This model matches exactly the trained model saved at:
models/trained/workload_predictor_v1.pt
"""

import torch
import torch.nn as nn
from typing import Tuple

try:
    from .config import (
        INPUT_FEATURES,
        LSTM_HIDDEN_SIZE_1,
        LSTM_HIDDEN_SIZE_2,
        DENSE_HIDDEN_SIZE,
        DROPOUT_RATE
    )
except ImportError:
    from config import (
        INPUT_FEATURES,
        LSTM_HIDDEN_SIZE_1,
        LSTM_HIDDEN_SIZE_2,
        DENSE_HIDDEN_SIZE,
        DROPOUT_RATE
    )


class LSTMWorkloadPredictor(nn.Module):
    """
    LSTM-based CPU workload predictor model.
    
    Architecture:
    - Input: (batch_size, 12 timesteps, 2 features)
    - LSTM Layer 1: 2 → 64 units with Dropout(0.2)
    - LSTM Layer 2: 64 → 32 units with Dropout(0.2)
    - Dense Layer: 32 → 16 units (ReLU)
    - Output Layer: 16 → 1 (CPU prediction)
    
    Task: Predict next 30-second CPU workload from 6 minutes of history.
    """
    
    def __init__(
        self,
        input_size: int = INPUT_FEATURES,
        hidden_size_1: int = LSTM_HIDDEN_SIZE_1,
        hidden_size_2: int = LSTM_HIDDEN_SIZE_2,
        dense_hidden_size: int = DENSE_HIDDEN_SIZE,
        dropout_rate: float = DROPOUT_RATE
    ):
        """
        Initialize LSTM model.
        
        Args:
            input_size: Number of input features (2: CPU, memory)
            hidden_size_1: First LSTM hidden size (64 units)
            hidden_size_2: Second LSTM hidden size (32 units)
            dense_hidden_size: Dense layer hidden size (16 units)
            dropout_rate: Dropout probability (0.2)
        """
        super(LSTMWorkloadPredictor, self).__init__()
        
        # First LSTM layer: input_size → hidden_size_1
        self.lstm1 = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size_1,
            batch_first=True,
            dropout=0.0  # No internal dropout in LSTM
        )
        self.dropout1 = nn.Dropout(dropout_rate)
        
        # Second LSTM layer: hidden_size_1 → hidden_size_2
        self.lstm2 = nn.LSTM(
            input_size=hidden_size_1,
            hidden_size=hidden_size_2,
            batch_first=True,
            dropout=0.0
        )
        self.dropout2 = nn.Dropout(dropout_rate)
        
        # Dense layers: hidden_size_2 → dense_hidden_size → 1
        self.dense = nn.Sequential(
            nn.Linear(hidden_size_2, dense_hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )
        self.output = nn.Linear(dense_hidden_size, 1)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the model.
        
        Args:
            x: Input tensor of shape (batch_size, 12, 2)
               - batch_size: Number of samples
               - 12: Number of timesteps (6 minutes of 30-second intervals)
               - 2: Features (CPU usage, memory usage)
        
        Returns:
            Output tensor of shape (batch_size, 1)
            - Predicted CPU workload for next 30 seconds (normalized 0-1)
        """
        # First LSTM layer with dropout
        x, (h1, c1) = self.lstm1(x)  # Output: (batch, 12, 64)
        x = self.dropout1(x)
        
        # Second LSTM layer with dropout - process all timesteps
        x, (h2, c2) = self.lstm2(x)  # Output: (batch, 12, 32)
        x = self.dropout2(x)
        
        # Take only the last timestep output
        x = x[:, -1, :]  # Shape: (batch, 32)
        
        # Dense layers with activation (already in Sequential)
        x = self.dense(x)  # Shape: (batch, 16), includes Linear + ReLU + Dropout
        
        # Output layer - single value prediction
        x = self.output(x)  # Shape: (batch, 1)
        
        return x
    
    def predict_single(self, x: torch.Tensor, device: torch.device) -> float:
        """
        Predict for a single input sequence.
        
        Args:
            x: Input tensor of shape (1, 12, 2) or (12, 2)
            device: torch.device for computation
        
        Returns:
            Single prediction value (float)
        """
        # Ensure correct dimensions
        if len(x.shape) == 2:
            x = x.unsqueeze(0)  # Add batch dimension
        
        x = x.to(device)
        
        with torch.no_grad():
            output = self.forward(x)
        
        return float(output[0, 0].cpu().numpy())
    
    @classmethod
    def create_model(cls, device: torch.device) -> 'LSTMWorkloadPredictor':
        """
        Factory method to create and place model on device.
        
        Args:
            device: torch.device (cuda or cpu)
        
        Returns:
            Initialized model on specified device
        """
        model = cls()
        model.to(device)
        return model
    
    def count_parameters(self) -> int:
        """Return total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_architecture_summary(self) -> str:
        """Return human-readable model architecture."""
        summary = "\nLSTM Workload Predictor Architecture:\n"
        summary += f"  Input: (batch_size, 12 timesteps, 2 features)\n"
        summary += f"  LSTM Layer 1: 2 -> {LSTM_HIDDEN_SIZE_1} (dropout={DROPOUT_RATE})\n"
        summary += f"  LSTM Layer 2: {LSTM_HIDDEN_SIZE_1} -> {LSTM_HIDDEN_SIZE_2} (dropout={DROPOUT_RATE})\n"
        summary += f"  Dense Layer: {LSTM_HIDDEN_SIZE_2} -> {DENSE_HIDDEN_SIZE} (ReLU)\n"
        summary += f"  Output Layer: {DENSE_HIDDEN_SIZE} -> 1\n"
        summary += f"  Total Parameters: {self.count_parameters():,}\n"
        return summary
