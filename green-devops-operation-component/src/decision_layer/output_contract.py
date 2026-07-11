"""
Decision Layer Output Contract

Defines structured output models for the final decision produced by the
Decision Layer orchestrator.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


@dataclass
class DecisionOutput:
    """
    Final decision output from the Decision Layer.
    
    This represents the final, merged decision combining Engine 1, Engine 2, and Engine 3
    into a single executable action.
    """
    
    # Decision metadata
    timestamp: str  # ISO format timestamp
    decision_id: str  # Unique decision identifier
    
    # Final action
    final_action: str  # scale_up | scale_down | hybrid | delay_jobs | no_action
    
    # Pod requirements
    raw_required_pods: int  # Raw requirement from Engine 1
    optimized_required_pods: Optional[int] = None  # Optimized requirement from Engine 2
    final_required_pods: int = None  # Final pod count (set by policy)
    
    # Job decisions
    jobs_to_delay: List[str] = field(default_factory=list)  # Job IDs to delay
    delay_job_count: int = 0  # Count of jobs to delay
    
    # Carbon impact
    carbon_saving_gco2: float = 0.0  # Carbon saved (g CO2)
    carbon_saving_percent: float = 0.0  # Percentage carbon saved
    
    # Safety/SLA status
    sla_preserved: bool = True  # Whether SLA requirements met
    safety_notes: List[str] = field(default_factory=list)  # Safety warnings/notes
    
    # Reasoning
    reason: str = ""  # Clear explanation of the decision
    policy_applied: str = ""  # Which policy rule was applied
    
    # Input echo
    input_load_level: str = ""  # Echo of input load level
    input_predicted_cpu: float = 0.0  # Echo of predicted CPU
    input_current_pods: int = 0  # Echo of current pods
    
    # Engine data
    had_engine3_data: bool = False  # Whether Engine 3 data was provided
    delayable_jobs_available: int = 0  # Total delayable jobs detected by Engine 3
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string with indentation."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_json_compact(self) -> str:
        """Convert to compact JSON."""
        return json.dumps(self.to_dict(), separators=(',', ':'))
    
    def to_response_dict(self) -> Dict[str, Any]:
        """
        Convert to API response dictionary format.
        
        This includes additional fields for API clarity.
        """
        return {
            "status": "success",
            "timestamp": self.timestamp,
            "decision": {
                "final_action": self.final_action,
                "final_required_pods": self.final_required_pods,
                "jobs_to_delay": self.jobs_to_delay,
                "carbon_saving_gco2": self.carbon_saving_gco2,
                "carbon_saving_percent": self.carbon_saving_percent,
                "sla_preserved": self.sla_preserved
            },
            "reasoning": {
                "reason": self.reason,
                "policy_applied": self.policy_applied,
                "safety_notes": self.safety_notes
            },
            "input_echo": {
                "load_level": self.input_load_level,
                "predicted_cpu": self.input_predicted_cpu,
                "current_pods": self.input_current_pods,
                "raw_required_pods": self.raw_required_pods,
                "optimized_required_pods": self.optimized_required_pods,
                "had_engine3_data": self.had_engine3_data,
                "delayable_jobs_available": self.delayable_jobs_available
            },
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        """
        Validate decision output integrity.
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        # Validate action
        valid_actions = ["scale_up", "scale_down", "hybrid", "delay_jobs", "no_action"]
        if self.final_action not in valid_actions:
            raise ValueError(f"Invalid action: {self.final_action}")
        
        # Validate pod counts
        if self.raw_required_pods < 1:
            raise ValueError(f"raw_required_pods must be >= 1, got {self.raw_required_pods}")
        
        if self.final_required_pods is None:
            raise ValueError("final_required_pods must be set")
        
        if self.final_required_pods < 1:
            raise ValueError(f"final_required_pods must be >= 1, got {self.final_required_pods}")
        
        # Validate carbon values
        if self.carbon_saving_gco2 < 0:
            raise ValueError(f"carbon_saving_gco2 must be >= 0, got {self.carbon_saving_gco2}")
        
        if not (0 <= self.carbon_saving_percent <= 100):
            raise ValueError(
                f"carbon_saving_percent must be 0-100, got {self.carbon_saving_percent}"
            )
        
        # Validate load level
        valid_loads = ["HIGH", "NORMAL", "LOW"]
        if self.input_load_level not in valid_loads:
            raise ValueError(f"Invalid load level: {self.input_load_level}")
        
        # Validate CPU
        if not (0 <= self.input_predicted_cpu <= 100):
            raise ValueError(f"Invalid predicted CPU: {self.input_predicted_cpu}")
        
        return True


@dataclass
class DecisionContext:
    """
    Merged context combining all engine outputs for decision making.
    
    This is an internal structure used by the decision orchestrator
    to hold all engine outputs before making the final decision.
    """
    
    # Engine 1 data (required)
    engine1_predicted_cpu: float
    engine1_load_level: str
    engine1_recommended_pods: int
    # Engine 2 data (required)
    engine2_raw_required_pods: int
    
    # Engine 1 data (optional)
    engine1_confidence: Optional[float] = None
    
    # Engine 2 data (optional)
    engine2_optimized_required_pods: Optional[int] = None
    engine2_recommended_action: Optional[str] = None
    engine2_carbon_saving_gco2: float = 0.0
    engine2_carbon_saving_percent: float = 0.0
    engine2_sla_protected: bool = False
    engine2_reason: str = ""
    
    # Engine 3 data (optional)
    engine3_delayable_jobs: int = 0
    engine3_delayable_job_ids: List[str] = field(default_factory=list)
    engine3_workload_reduction_percent: float = 0.0
    engine3_reason: str = ""
    
    # System state
    current_pods: int = 1
    current_cpu: float = 0.0
    
    def has_engine3_data(self) -> bool:
        """Check if Engine 3 data is available."""
        return self.engine3_delayable_jobs > 0 or self.engine3_workload_reduction_percent > 0
    
    def get_summary(self) -> str:
        """Get human-readable summary of the context."""
        lines = [
            f"Engine 1: CPU={self.engine1_predicted_cpu:.1f}%, Load={self.engine1_load_level}, Pods={self.engine1_recommended_pods}",
            f"Engine 2: Raw={self.engine2_raw_required_pods} pods, Optimized={self.engine2_optimized_required_pods} pods",
            f"Engine 2: Carbon savings={self.engine2_carbon_saving_gco2:.2f}g ({self.engine2_carbon_saving_percent:.1f}%), SLA={self.engine2_sla_protected}",
        ]
        
        if self.has_engine3_data():
            lines.append(
                f"Engine 3: {self.engine3_delayable_jobs} delayable jobs, "
                f"reduction={self.engine3_workload_reduction_percent:.1%}"
            )
        
        return "\n".join(lines)
