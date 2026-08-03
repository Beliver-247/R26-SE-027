"""
Decision Layer Configuration

Defines final policy thresholds, rules, and decision parameters
for the Green DevOps Operation Phase system.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LoadThresholds:
    """Load level thresholds for decision rules."""
    high_load_cpu_threshold: float = 70.0  # CPU % threshold for HIGH load
    normal_load_cpu_threshold: float = 40.0  # CPU % threshold for NORMAL load
    low_load_cpu_threshold: float = 0.0  # Anything below normal is LOW


@dataclass
class HighLoadPolicy:
    """
    Policy rules for HIGH LOAD scenarios.
    
    During HIGH load:
    - SLA protection is MANDATORY (parent priority)
    - Pod reduction is NOT allowed
    - Job delay is OPTIONAL (secondary after SLA via pods is guaranteed)
    - Carbon optimization via pod reduction is NOT applied
    """
    allow_delayed_jobs: bool = True  # Can delay jobs, but ONLY after SLA via pods guaranteed
    allow_hybrid: bool = False  # Don't use hybrid (no pod reduction in HIGH)
    allow_scale_down: bool = False  # Never scale down during HIGH load
    min_pod_safe_level: int = None  # Use raw_required_pods as minimum (SLA guarantee)
    sla_preservation_priority: bool = True  # SLA is non-negotiable
    reason_prefix: str = "HIGH load detected"


@dataclass
class NormalLoadPolicy:
    """
    Policy rules for NORMAL LOAD scenarios.
    
    During NORMAL load:
    - Balance between SLA and carbon efficiency
    - Job delay is ENCOURAGED via hybrid approach  
    - Pod optimization is allowed if SLA permits
    - Hybrid strategy combines pod scaling with job delay
    """
    allow_delayed_jobs: bool = True  # Can delay jobs (encouraged)
    allow_hybrid: bool = True  # Prefer hybrid (scale + optimize)
    allow_scale_down: bool = True  # Scale down allowed with safeguards
    allow_scale_up: bool = True  # Scale up if needed
    min_pod_safe_level: int = 1  # Can go to minimum with optimization
    prefer_optimization: bool = True  # Prefer carbon optimization when available
    reason_prefix: str = "NORMAL load"


@dataclass
class LowLoadPolicy:
    """
    Policy rules for LOW LOAD scenarios.
    
    During LOW load:
    - Prioritize carbon efficiency
    - Job delay is MAXIMIZED for workload optimization
    - Aggressive pod scaling down encouraged
    - SLA is preserved but not the primary concern
    """
    allow_delayed_jobs: bool = True  # Can delay jobs (maximized)
    allow_hybrid: bool = True  # Use hybrid (scale down + delay jobs)
    allow_scale_down: bool = True  # Aggressive scale down
    allow_scale_up: bool = False  # Don't scale up for low load
    min_pod_safe_level: int = 1  # Minimum pods for low load
    prefer_optimization: bool = True  # Prioritize carbon optimization
    aggressive_optimization: bool = True  # Use strongest optimization available
    reason_prefix: str = "LOW load"


class DecisionLayerConfig:
    """Final policy configuration for Decision Layer."""
    
    # Load thresholds
    LOAD_THRESHOLDS = LoadThresholds(
        high_load_cpu_threshold=70.0,
        normal_load_cpu_threshold=40.0
    )
    
    # Load-specific policies
    HIGH_LOAD_POLICY = HighLoadPolicy(
        allow_delayed_jobs=True,
        allow_hybrid=False,
        allow_scale_down=False,
        sla_preservation_priority=True
    )
    
    NORMAL_LOAD_POLICY = NormalLoadPolicy(
        allow_delayed_jobs=True,
        allow_hybrid=True,
        allow_scale_down=True,
        allow_scale_up=True,
        prefer_optimization=True
    )
    
    LOW_LOAD_POLICY = LowLoadPolicy(
        allow_delayed_jobs=True,
        allow_hybrid=True,
        allow_scale_down=True,
        prefer_optimization=True,
        aggressive_optimization=True
    )
    
    # Global safety rules
    MINIMUM_PODS: int = 1  # Absolute minimum pod count
    MAXIMUM_PODS: int = 100  # Absolute maximum pod count
    
    # Decision actions
    VALID_ACTIONS: List[str] = [
        "scale_up",
        "scale_down",
        "hybrid",
        "delay_jobs",
        "no_action"
    ]
    
    # SLA protection rules
    SLA_CPU_THRESHOLD: float = 75.0  # CPU % threshold for SLA priority
    SLA_LOAD_LEVELS: List[str] = ["HIGH"]  # Load levels requiring SLA protection
    
    # Optimization thresholds
    MIN_CARBON_SAVING_FOR_ACTION: float = 0.5  # Minimum g CO2 saving to consider
    MIN_POD_REDUCTION_FOR_HYBRID: int = 1  # Minimum pod reduction to use hybrid
    
    # Job delay rules
    DELAY_JOBS_ALLOWED_LOADS: List[str] = ["HIGH", "NORMAL", "LOW"]
    MAX_JOBS_TO_DELAY: int = 1000  # Safety cap
    
    @classmethod
    def get_policy_for_load(cls, load_level: str):
        """Get policy rules for a specific load level."""
        if load_level == "HIGH":
            return cls.HIGH_LOAD_POLICY
        elif load_level == "NORMAL":
            return cls.NORMAL_LOAD_POLICY
        elif load_level == "LOW":
            return cls.LOW_LOAD_POLICY
        else:
            raise ValueError(f"Unknown load level: {load_level}")
    
    @classmethod
    def validate_pod_count(cls, pods: int) -> int:
        """Validate and clamp pod count to safe range."""
        if pods < cls.MINIMUM_PODS:
            return cls.MINIMUM_PODS
        if pods > cls.MAXIMUM_PODS:
            return cls.MAXIMUM_PODS
        return pods
