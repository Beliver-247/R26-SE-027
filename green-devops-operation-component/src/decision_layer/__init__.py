"""
Decision Layer for Green DevOps Operation Phase

The Decision Layer is the final orchestrator that:
1. Accepts outputs from Engine 1 (Workload Prediction)
2. Accepts outputs from Engine 2 (Carbon Emission Analysis)  
3. Accepts outputs from Engine 3 (Job Prioritization)
4. Merges them into one decision context
5. Applies policy rules based on load level
6. Returns one final executable action

This module provides:
- DecisionOrchestrator: Main orchestrator
- DecisionOutput: Final decision output structure
- DecisionContext: Internal context structure
- PolicyRules: Policy rule implementation
- DecisionLayerConfig: Configuration and thresholds
"""

from .config import DecisionLayerConfig
from .output_contract import DecisionOutput, DecisionContext
from .policy_rules import PolicyRules
from .decision_orchestrator import DecisionOrchestrator

__version__ = "1.0"
__all__ = [
    "DecisionLayerConfig",
    "DecisionOutput",
    "DecisionContext",
    "PolicyRules",
    "DecisionOrchestrator"
]
