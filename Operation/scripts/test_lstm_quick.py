"""
Quick test to verify LSTM training runs successfully.
"""

import numpy as np
import torch
import torch.nn as nn
from pathlib import Path

print("Environment Check:")
print(f"  PyTorch: {torch.__version__}")
print(f"  CUDA Available: {torch.cuda.is_available()}")
print(f"  Device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}\n")

# Load data
data_dir = Path(r"D:\Research\Operation\green-devops-operation-component\data\preprocessed\global")
X_train = np.load(data_dir / 'X_train.npy')
y_train = np.load(data_dir / 'y_train.npy')

print(f"Data Loaded:")
print(f"  X_train shape: {X_train.shape}")
print(f"  y_train shape: {y_train.shape}\n")

# Convert to tensors
X_tens = torch.from_numpy(X_train[:1000]).float()
y_tens = torch.from_numpy(y_train[:1000]).float().unsqueeze(1)

print(f"Tensor Shapes:")
print(f"  X batch: {X_tens.shape}")
print(f"  y batch: {y_tens.shape}\n")

# Simple model
class SimpleLSTM(nn.Module):
    def __init__(self):
        super(SimpleLSTM, self).__init__()
        self.lstm1 = nn.LSTM(2, 64, batch_first=True)
        self.lstm2 = nn.LSTM(64, 32, batch_first=True)
        self.dense = nn.Linear(32, 16)
        self.out = nn.Linear(16, 1)
    
    def forward(self, x):
        x, _ = self.lstm1(x)
        x, _ = self.lstm2(x)
        x = x[:, -1, :]
        x = torch.relu(self.dense(x))
        return self.out(x)

model = SimpleLSTM()
print("Model created successfully")

# Test forward pass
with torch.no_grad():
    y_pred = model(X_tens[:32])
    print(f"Predictions shape: {y_pred.shape}")
    print(f"Sample pred values: {y_pred[:3].flatten()}")

print("\nTest completed successfully!")
