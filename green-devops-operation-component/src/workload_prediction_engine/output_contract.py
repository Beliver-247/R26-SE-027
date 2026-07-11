"""
Output contract/schema for Engine 1 - Workload Prediction.

This defines the structured output produced by Engine 1 that will be consumed by:
- Engine 2 (Carbon Emission Estimation)
- Engine 3 (Job Prioritization)
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class Engine1Output:
    """
    Structured output from Engine 1 workload prediction.
    
    This output is sent to the next engines for carbon emission estimation
    and job prioritization decisions.
    """
    
    # Identifiers and timing
    system_id: str
    timestamp: str  # ISO format: "2026-04-15T10:00:00Z"
    
    # Prediction window
    prediction_window_seconds: int  # Always 30 seconds
    
    # Predicted workload
    predicted_cpu: float  # CPU percentage (0-100)
    
    # Load classification
    predicted_load_level: str  # "LOW", "NORMAL", or "HIGH"
    
    # Pod recommendation
    recommended_pods: int  # Recommended number of pods for this workload
    
    # Data source and model info
    data_source: str  # "cold_start" or "runtime"
    model_version: str  # "v1", "v2", etc.
    
    # Optional metadata
    predicted_memory: Optional[float] = None  # Memory in KB or percentage
    confidence: Optional[float] = None  # Model confidence (0-1)
    model_input_source: Optional[str] = None  # "test_data", "prometheus", etc.
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        data = self.to_dict()
        return json.dumps(data, indent=2)
    
    def to_json_compact(self) -> str:
        """Convert to compact JSON (no indentation)."""
        data = self.to_dict()
        return json.dumps(data)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Engine1Output':
        """Create instance from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Engine1Output':
        """Create instance from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> bool:
        """
        Validate output data.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        if not self.system_id:
            raise ValueError("system_id cannot be empty")
        
        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")
        
        if self.prediction_window_seconds != 30:
            raise ValueError(f"prediction_window_seconds must be 30, got {self.prediction_window_seconds}")
        
        if not (0 <= self.predicted_cpu <= 100):
            raise ValueError(f"predicted_cpu must be 0-100, got {self.predicted_cpu}")
        
        if self.predicted_memory is not None and self.predicted_memory < 0:
            raise ValueError(f"predicted_memory cannot be negative, got {self.predicted_memory}")
        
        valid_levels = {"LOW", "NORMAL", "HIGH"}
        if self.predicted_load_level not in valid_levels:
            raise ValueError(f"predicted_load_level must be one of {valid_levels}, got {self.predicted_load_level}")
        
        if not (1 <= self.recommended_pods <= 20):
            raise ValueError(f"recommended_pods must be 1-20, got {self.recommended_pods}")
        
        if self.data_source not in {"cold_start", "runtime"}:
            raise ValueError(f"data_source must be 'cold_start' or 'runtime', got {self.data_source}")
        
        if self.confidence is not None and not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")
        
        return True
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Engine1Output(\n"
            f"  system_id={self.system_id}\n"
            f"  timestamp={self.timestamp}\n"
            f"  predicted_cpu={self.predicted_cpu:.2f}%\n"
            f"  predicted_load_level={self.predicted_load_level}\n"
            f"  recommended_pods={self.recommended_pods}\n"
            f"  data_source={self.data_source}\n"
            f"  model_version={self.model_version}\n"
            f")"
        )


@dataclass
class Engine1Request:
    """
    Request input for Engine 1 workload prediction.
    
    This can be filled with either:
    - Cold-start test data
    - Live runtime metrics from Prometheus
    """
    
    system_id: str
    timestamp: str
    
    # Latest workload sequence
    # Shape: (12, 2) - 12 timesteps of (CPU%, Memory)
    workload_sequence: list  # List of [cpu, memory] per timestep
    
    # Data source
    data_source: str  # "cold_start" or "runtime"
    
    # Optional metadata
    prometheus_job_name: Optional[str] = None
    pod_count_current: Optional[int] = None
    
    def validate(self) -> bool:
        """Validate input request."""
        if not self.system_id:
            raise ValueError("system_id cannot be empty")
        
        if len(self.workload_sequence) != 12:
            raise ValueError(f"workload_sequence must have 12 timesteps, got {len(self.workload_sequence)}")
        
        for i, sample in enumerate(self.workload_sequence):
            if len(sample) != 2:
                raise ValueError(f"timestep {i} must have 2 features, got {len(sample)}")
            cpu, mem = sample
            if not (0 <= cpu <= 100):
                raise ValueError(f"timestep {i} CPU must be 0-100, got {cpu}")
            if not (0 <= mem):
                raise ValueError(f"timestep {i} memory cannot be negative, got {mem}")
        
        if self.data_source not in {"cold_start", "runtime"}:
            raise ValueError(f"data_source must be 'cold_start' or 'runtime'")
        
        return True


def create_engine1_output(
    system_id: str,
    predicted_cpu: float,
    predicted_load_level: str,
    recommended_pods: int,
    data_source: str,
    model_version: str = "v1",
    predicted_memory: Optional[float] = None,
    confidence: Optional[float] = None,
    model_input_source: Optional[str] = None
) -> Engine1Output:
    """
    Factory function to create Engine1Output with proper validation.
    
    Args:
        system_id: System identifier
        predicted_cpu: Predicted CPU percentage (0-100)
        predicted_load_level: Load classification ("LOW", "NORMAL", "HIGH")
        recommended_pods: Number of pods recommended
        data_source: "cold_start" or "runtime"
        model_version: Model version tag
        predicted_memory: Optional predicted memory
        confidence: Optional confidence score (0-1)
        model_input_source: Optional source of input data
    
    Returns:
        Engine1Output instance (validated)
    """
    output = Engine1Output(
        system_id=system_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        prediction_window_seconds=30,
        predicted_cpu=predicted_cpu,
        predicted_memory=predicted_memory,
        predicted_load_level=predicted_load_level,
        recommended_pods=recommended_pods,
        data_source=data_source,
        model_version=model_version,
        confidence=confidence,
        model_input_source=model_input_source
    )
    
    output.validate()
    return output
