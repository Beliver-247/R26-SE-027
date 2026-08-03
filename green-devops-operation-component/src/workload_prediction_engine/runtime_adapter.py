"""
Runtime data adapter for Engine 1.

Converts live Prometheus metrics and historical data into model-ready LSTM sequences.
Supports both cold-start test data and runtime operational data.

20-second alignment and resampling to 30-second intervals.
"""

import numpy as np
import logging
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd

try:
    from .config import (
        SEQUENCE_LENGTH,
        PREDICTION_WINDOW_SECONDS,
        PROMETHEUS_STEP_SECONDS,
        MAX_MISSING_DATAPOINTS,
        INTERPOLATION_METHOD
    )
except ImportError:
    from config import (
        SEQUENCE_LENGTH,
        PREDICTION_WINDOW_SECONDS,
        PROMETHEUS_STEP_SECONDS,
        MAX_MISSING_DATAPOINTS,
        INTERPOLATION_METHOD
    )

logger = logging.getLogger(__name__)


class RuntimeAdapter:
    """
    Convert runtime metrics into model-ready LSTM input sequences.
    
    Responsibilities:
    - Ingest Prometheus time-series data or simulation data
    - Align data to 30-second intervals
    - Resample irregular intervals to 30-second windows
    - Handle missing data with interpolation
    - Build 12-timestep sequences for model inference
    """
    
    def __init__(self, prediction_window_seconds: int = PREDICTION_WINDOW_SECONDS):
        """
        Initialize adapter.
        
        Args:
            prediction_window_seconds: Target window size (30 seconds)
        """
        self.prediction_window_seconds = prediction_window_seconds
        self.logger = logging.getLogger(__name__)
    
    def prepare_sequence_from_history(
        self,
        timestamps: List[float],
        cpu_values: List[float],
        memory_values: List[float],
        normalize: bool = False,
        scaler_cpu: Optional[object] = None,
        scaler_memory: Optional[object] = None
    ) -> np.ndarray:
        """
        Prepare 12-timestep sequence from historical data.
        
        Args:
            timestamps: Unix timestamps (seconds)
            cpu_values: CPU usage percentages
            memory_values: Memory usage (KB or %)
            normalize: Whether to apply scalers
            scaler_cpu: Fitted scaler for CPU (from training)
            scaler_memory: Fitted scaler for memory
        
        Returns:
            Sequence array of shape (12, 2)
        """
        self.logger.info(f"Preparing sequence from {len(timestamps)} data points")
        
        if len(timestamps) < SEQUENCE_LENGTH:
            self.logger.warning(
                f"Insufficient data: {len(timestamps)} points, need {SEQUENCE_LENGTH}"
            )
        
        # Validate input lengths
        if not (len(timestamps) == len(cpu_values) == len(memory_values)):
            raise ValueError("Mismatched array lengths")
        
        # Create DataFrame for easier manipulation
        df = pd.DataFrame({
            'timestamp': timestamps,
            'cpu': cpu_values,
            'memory': memory_values
        })
        
        # Resample to 30-second intervals
        df = self._resample_to_window(df)
        
        # Take last 12 timesteps
        if len(df) > SEQUENCE_LENGTH:
            df = df.iloc[-SEQUENCE_LENGTH:]
        elif len(df) < SEQUENCE_LENGTH:
            # Pad with forward fill if needed
            self.logger.warning(f"Padding sequence to {SEQUENCE_LENGTH} timesteps")
            df = self._pad_sequence(df)
        
        # Build sequence
        sequence = np.column_stack([
            df['cpu'].values,
            df['memory'].values
        ]).astype(np.float32)
        
        # Normalize if scalers provided
        if normalize and scaler_cpu is not None:
            sequence = self._normalize_sequence(
                sequence,
                scaler_cpu,
                scaler_memory
            )
        
        self.logger.info(f"Sequence prepared with shape: {sequence.shape}")
        return sequence
    
    def prepare_sequence_from_prometheus(
        self,
        prometheus_data: List[dict],
        system_id: str,
        normalize: bool = False,
        scaler_cpu: Optional[object] = None
    ) -> Tuple[np.ndarray, datetime]:
        """
        Prepare sequence from Prometheus metrics API response.
        
        Expected prometheus_data format (from /api/v1/query_range):
        [
            {
                'metric': {'__name__': 'workload_cpu_usage', ...},
                'values': [[timestamp, value], ...]
            },
            {
                'metric': {'__name__': 'workload_memory_usage', ...},
                'values': [[timestamp, value], ...]
            }
        ]
        
        Args:
            prometheus_data: Raw response from Prometheus API
            system_id: Target system identifier
            normalize: Whether to normalize using scaler
            scaler_cpu: Fitted CPU scaler from training
        
        Returns:
            Tuple of (sequence array (12, 2), latest timestamp)
        """
        self.logger.info(f"Preparing sequence from Prometheus for system: {system_id}")
        
        # Extract CPU and memory time-series
        cpu_series = None
        memory_series = None
        
        for item in prometheus_data:
            metric_name = item.get('metric', {}).get('__name__', '')
            if 'cpu' in metric_name.lower():
                cpu_series = item.get('values', [])
            elif 'memory' in metric_name.lower():
                memory_series = item.get('values', [])
        
        if cpu_series is None:
            raise ValueError("CPU metrics not found in Prometheus data")
        
        # Handle missing memory metrics
        if memory_series is None:
            self.logger.warning("Memory metrics not found, using zeros")
            memory_series = [[ts, 0] for ts, _ in cpu_series]
        
        # Convert to arrays
        timestamps = np.array([float(ts) for ts, _ in cpu_series])
        cpu_values = np.array([float(val) for _, val in cpu_series])
        memory_values = np.array([float(val) for _, val in memory_series])
        
        # Prepare sequence
        sequence = self.prepare_sequence_from_history(
            timestamps,
            cpu_values,
            memory_values,
            normalize=normalize,
            scaler_cpu=scaler_cpu
        )
        
        latest_timestamp = datetime.fromtimestamp(timestamps[-1])
        return sequence, latest_timestamp
    
    def prepare_sequence_from_csv(
        self,
        csv_file_path: str,
        system_id: str,
        normalize: bool = False,
        scaler_cpu: Optional[object] = None
    ) -> np.ndarray:
        """
        Prepare sequence from historical CSV file.
        
        Expected CSV format:
        timestamp,cpu,memory
        1629216000,45.2,2048
        1629216030,46.1,2100
        ...
        
        Args:
            csv_file_path: Path to CSV file
            system_id: System identifier
            normalize: Whether to normalize
            scaler_cpu: CPU scaler
        
        Returns:
            Sequence array of shape (12, 2)
        """
        self.logger.info(f"Loading sequence from CSV: {csv_file_path}")
        
        df = pd.read_csv(csv_file_path)
        
        # Extract columns (handle various naming conventions)
        timestamp_col = [c for c in df.columns if 'time' in c.lower()][0]
        cpu_col = [c for c in df.columns if 'cpu' in c.lower()][0]
        memory_col = [c for c in df.columns if 'memory' in c.lower()][0]
        
        return self.prepare_sequence_from_history(
            df[timestamp_col].values,
            df[cpu_col].values,
            df[memory_col].values,
            normalize=normalize,
            scaler_cpu=scaler_cpu
        )
    
    def _resample_to_window(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Resample data to 30-second intervals.
        
        If data comes at irregular intervals (e.g., from Prometheus),
        resample to uniform 30-second windows.
        
        Args:
            df: DataFrame with timestamp, cpu, memory columns
        
        Returns:
            Resampled DataFrame with 30-second intervals
        """
        # Convert timestamp to datetime if unix timestamp
        if df['timestamp'].dtype != 'datetime64[ns]':
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            except:
                pass
        
        # Set timestamp as index
        df = df.set_index('timestamp')
        df = df.sort_index()
        
        # Resample to 30-second intervals
        df_resampled = df.resample(f'{self.prediction_window_seconds}s').mean()
        
        # Forward fill to handle missing values
        df_resampled = df_resampled.ffill()
        df_resampled = df_resampled.bfill()
        
        # Reset index
        df_resampled = df_resampled.reset_index()
        
        self.logger.debug(
            f"Resampled data from {len(df)} to {len(df_resampled)} points"
        )
        
        return df_resampled
    
    def _pad_sequence(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Pad sequence to SEQUENCE_LENGTH timesteps.
        
        Uses forward fill then backward fill for missing values.
        
        Args:
            df: Incomplete DataFrame
        
        Returns:
            Padded DataFrame with SEQUENCE_LENGTH rows
        """
        needed = SEQUENCE_LENGTH - len(df)
        
        if needed <= 0:
            return df
        
        self.logger.warning(f"Padding {needed} timesteps using forward/backfill")
        
        # Duplicate last row
        last_row = df.iloc[[-1]]
        padding = pd.concat([last_row] * needed, ignore_index=True)
        
        df_padded = pd.concat([df, padding], ignore_index=True)
        
        return df_padded
    
    def _normalize_sequence(
        self,
        sequence: np.ndarray,
        scaler_cpu: object,
        scaler_memory: Optional[object] = None
    ) -> np.ndarray:
        """
        Normalize sequence using fitted scalers.
        
        Args:
            sequence: Array of shape (12, 2)
            scaler_cpu: Fitted MinMaxScaler for CPU
            scaler_memory: Fitted scaler for memory
        
        Returns:
            Normalized sequence
        """
        sequence_norm = sequence.copy()
        
        # Normalize CPU (column 0)
        try:
            sequence_norm[:, 0] = scaler_cpu.transform(sequence[:, [0]]).flatten()
        except Exception as e:
            self.logger.error(f"CPU normalization failed: {e}")
        
        # Normalize memory (column 1)
        if scaler_memory is not None:
            try:
                sequence_norm[:, 1] = scaler_memory.transform(sequence[:, [1]]).flatten()
            except Exception as e:
                self.logger.error(f"Memory normalization failed: {e}")
        
        self.logger.debug(f"Sequence normalized to range [0,1]")
        
        return sequence_norm.astype(np.float32)
    
    def create_test_sequence(self) -> np.ndarray:
        """
        Create realistic test sequence for cold-start scenarios.
        
        Generates 12 timesteps of synthetic CPU/memory data showing
        a gradual increase in load (realistic for many applications).
        
        Returns:
            Test sequence of shape (12, 2)
        """
        self.logger.info("Creating synthetic test sequence")
        
        # Simulate increasing workload pattern
        cpu_pattern = np.linspace(20, 60, SEQUENCE_LENGTH)
        memory_pattern = np.linspace(1024, 3072, SEQUENCE_LENGTH)
        
        # Add realistic noise
        cpu_noise = np.random.normal(0, 2, SEQUENCE_LENGTH)
        memory_noise = np.random.normal(0, 100, SEQUENCE_LENGTH)
        
        cpu_values = np.clip(cpu_pattern + cpu_noise, 0, 100)
        memory_values = np.clip(memory_pattern + memory_noise, 0, 10000)
        
        sequence = np.column_stack([cpu_values, memory_values]).astype(np.float32)
        
        self.logger.debug(f"Test sequence created: shape={sequence.shape}")
        return sequence
    
    def validate_sequence(self, sequence: np.ndarray) -> bool:
        """
        Validate sequence shape and values.
        
        Args:
            sequence: Sequence to validate
        
        Returns:
            True if valid
        
        Raises:
            ValueError if invalid
        """
        if sequence.shape != (SEQUENCE_LENGTH, 2):
            raise ValueError(
                f"Invalid sequence shape: {sequence.shape}, "
                f"expected ({SEQUENCE_LENGTH}, 2)"
            )
        
        if not np.isfinite(sequence).all():
            raise ValueError("Sequence contains NaN or infinite values")
        
        # Check CPU range
        if not (0 <= sequence[:, 0].min() and sequence[:, 0].max() <= 100):
            self.logger.warning(
                f"CPU values out of expected range: "
                f"[{sequence[:, 0].min():.2f}, {sequence[:, 0].max():.2f}]"
            )
        
        return True
    
    def get_sequence_summary(self, sequence: np.ndarray) -> dict:
        """
        Get statistical summary of sequence.
        
        Args:
            sequence: Input sequence
        
        Returns:
            Dictionary with stats
        """
        return {
            'cpu_min': float(sequence[:, 0].min()),
            'cpu_max': float(sequence[:, 0].max()),
            'cpu_mean': float(sequence[:, 0].mean()),
            'cpu_std': float(sequence[:, 0].std()),
            'memory_min': float(sequence[:, 1].min()),
            'memory_max': float(sequence[:, 1].max()),
            'memory_mean': float(sequence[:, 1].mean()),
            'memory_std': float(sequence[:, 1].std()),
            'shape': sequence.shape,
            'dtype': str(sequence.dtype),
            'has_nans': np.isnan(sequence).any(),
            'is_finite': np.isfinite(sequence).all()
        }
