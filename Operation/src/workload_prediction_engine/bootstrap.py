"""
Bootstrap strategies for Engine 1 cold-start mode.

When Engine 1 starts, there's no runtime history yet.
Bootstrap handles creating a valid prediction input from partial data.
"""

import numpy as np
import logging
from typing import List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class BootstrapStrategy:
    """Base class for bootstrap strategies."""
    
    def bootstrap_sequence(
        self,
        partial_metrics: List[Dict],
        target_length: int = 12
    ) -> np.ndarray:
        """
        Create a valid LSTM input sequence from partial runtime data.
        
        Args:
            partial_metrics: Available runtime metrics (< 12 points)
                Dicts with keys: timestamp, cpu, memory
            target_length: Desired sequence length (default 12)
        
        Returns:
            np.ndarray of shape (target_length, 2) with CPU and memory normalized
        """
        raise NotImplementedError


class ForwardFillBootstrap(BootstrapStrategy):
    """
    Bootstrap by repeating the first available value forward.
    
    If we have 3 real points, pad with copies of the first until we have 12.
    
    Rationale: Assumes system starts in recent historical state.
    """
    
    def bootstrap_sequence(
        self,
        partial_metrics: List[Dict],
        target_length: int = 12
    ) -> np.ndarray:
        """Forward-fill bootstrap."""
        if not partial_metrics:
            # No data at all, return middle-range values
            return self._create_neutral_sequence(target_length)
        
        if len(partial_metrics) >= target_length:
            # Already have enough
            metrics = partial_metrics[-target_length:]
        else:
            # Pad with copies of first value
            metrics = partial_metrics.copy()
            first_metric = partial_metrics[0]
            
            while len(metrics) < target_length:
                metrics.insert(0, first_metric)
        
        # Convert to array
        sequence = np.array([
            [m['cpu'], m['memory']] for m in metrics
        ], dtype=np.float32)
        
        # Normalize (assuming CPU 0-100%, memory 0-1000MB roughly)
        sequence[:, 0] = sequence[:, 0] / 100.0  # CPU to [0, 1]
        sequence[:, 1] = sequence[:, 1] / 1000.0  # Memory to [0, 1]
        
        logger.debug(
            f"Bootstrap: {len(partial_metrics)} → {target_length} points "
            f"(forward-fill)"
        )
        
        return sequence
    
    def _create_neutral_sequence(self, length: int) -> np.ndarray:
        """Create neutral middle-range values."""
        # CPU=25%, Memory=400MB
        return np.tile([0.25, 0.4], (length, 1)).astype(np.float32)


class LinearInterpolationBootstrap(BootstrapStrategy):
    """
    Bootstrap by linearly interpolating between first and last values.
    
    If we have 3 points, interpolate to 12 points.
    
    Rationale: Assumes smooth transition from initial to current state.
    """
    
    def bootstrap_sequence(
        self,
        partial_metrics: List[Dict],
        target_length: int = 12
    ) -> np.ndarray:
        """Linear interpolation bootstrap."""
        if not partial_metrics:
            return self._create_neutral_sequence(target_length)
        
        if len(partial_metrics) >= target_length:
            metrics = partial_metrics[-target_length:]
        else:
            # Interpolate
            first_cpu = partial_metrics[0]['cpu']
            last_cpu = partial_metrics[-1]['cpu']
            first_mem = partial_metrics[0]['memory']
            last_mem = partial_metrics[-1]['memory']
            
            interpolated = []
            for i in range(target_length):
                ratio = i / (target_length - 1) if target_length > 1 else 0
                cpu = first_cpu + ratio * (last_cpu - first_cpu)
                mem = first_mem + ratio * (last_mem - first_mem)
                interpolated.append({
                    'cpu': cpu,
                    'memory': mem,
                    'timestamp': 0  # Not used
                })
            
            metrics = interpolated
        
        sequence = np.array([
            [m['cpu'], m['memory']] for m in metrics
        ], dtype=np.float32)
        
        sequence[:, 0] = sequence[:, 0] / 100.0
        sequence[:, 1] = sequence[:, 1] / 1000.0
        
        logger.debug(
            f"Bootstrap: {len(partial_metrics)} → {target_length} points "
            f"(linear interpolation)"
        )
        
        return sequence
    
    def _create_neutral_sequence(self, length: int) -> np.ndarray:
        """Create neutral values."""
        return np.tile([0.25, 0.4], (length, 1)).astype(np.float32)


class StatisticalBootstrap(BootstrapStrategy):
    """
    Bootstrap using statistical distribution of observed data.
    
    Creates realistic padding based on mean/variance of available points.
    
    Rationale: Preserves uncertainty about initial state.
    """
    
    def bootstrap_sequence(
        self,
        partial_metrics: List[Dict],
        target_length: int = 12
    ) -> np.ndarray:
        """Statistical bootstrap."""
        if not partial_metrics:
            return self._create_neutral_sequence(target_length)
        
        if len(partial_metrics) >= target_length:
            metrics = partial_metrics[-target_length:]
        else:
            # Compute statistics from available data
            cpus = np.array([m['cpu'] for m in partial_metrics])
            mems = np.array([m['memory'] for m in partial_metrics])
            
            cpu_mean, cpu_std = cpus.mean(), cpus.std()
            mem_mean, mem_std = mems.mean(), mems.std()
            
            # Generate padding with same distribution
            np.random.seed(42)  # For reproducibility
            pad_count = target_length - len(partial_metrics)
            
            padding = []
            for _ in range(pad_count):
                cpu = max(0, min(100, np.random.normal(cpu_mean, cpu_std)))
                mem = max(0, np.random.normal(mem_mean, mem_std))
                padding.append({
                    'cpu': cpu,
                    'memory': mem,
                    'timestamp': 0
                })
            
            metrics = padding + partial_metrics
        
        sequence = np.array([
            [m['cpu'], m['memory']] for m in metrics
        ], dtype=np.float32)
        
        sequence[:, 0] = sequence[:, 0] / 100.0
        sequence[:, 1] = sequence[:, 1] / 1000.0
        
        logger.debug(
            f"Bootstrap: {len(partial_metrics)} → {target_length} points "
            f"(statistical)"
        )
        
        return sequence
    
    def _create_neutral_sequence(self, length: int) -> np.ndarray:
        """Create neutral values."""
        return np.tile([0.25, 0.4], (length, 1)).astype(np.float32)


class BootstrapFactory:
    """Factory for creating bootstrap strategies."""
    
    STRATEGIES = {
        'forward_fill': ForwardFillBootstrap,
        'linear': LinearInterpolationBootstrap,
        'statistical': StatisticalBootstrap,
    }
    
    @staticmethod
    def create(strategy: str = 'forward_fill') -> BootstrapStrategy:
        """
        Create a bootstrap strategy.
        
        Args:
            strategy: Strategy name ('forward_fill', 'linear', 'statistical')
        
        Returns:
            BootstrapStrategy instance
        
        Raises:
            ValueError: If strategy unknown
        """
        if strategy not in BootstrapFactory.STRATEGIES:
            raise ValueError(
                f"Unknown strategy: {strategy}. "
                f"Choose from: {list(BootstrapFactory.STRATEGIES.keys())}"
            )
        
        return BootstrapFactory.STRATEGIES[strategy]()
    
    @staticmethod
    def get_available_strategies() -> List[str]:
        """Get list of available strategies."""
        return list(BootstrapFactory.STRATEGIES.keys())
