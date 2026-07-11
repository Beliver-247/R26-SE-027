"""
Engine 2 - Carbon Emission Engine

Calculates carbon footprint of workload predictions and recommends
optimal scaling strategies that minimize environmental impact.

Example:
    >>> from carbon_engine import run_carbon_engine
    >>> 
    >>> # Output from Engine 1
    >>> e1_output = {
    ...     "predicted_cpu": 65.0,
    ...     "predicted_load_level": "NORMAL",
    ...     "recommended_pods": 4,
    ...     "current_pods": 3
    ... }
    >>> 
    >>> # Run carbon analysis
    >>> result = run_carbon_engine(e1_output)
    >>> print(result["decision"]["recommended_action"])
    "scale_up"
"""

from carbon_engine.carbon_engine import CarbonEmissionEngine, run_carbon_engine
from carbon_engine.energy_model import EnergyModel
from carbon_engine.carbon_calculator import CarbonCalculator
from carbon_engine.scenario_simulator import ScenarioSimulator, Scenario
from carbon_engine.decision_engine import DecisionEngine

__all__ = [
    "CarbonEmissionEngine",
    "run_carbon_engine",
    "EnergyModel",
    "CarbonCalculator",
    "ScenarioSimulator",
    "Scenario",
    "DecisionEngine"
]

__version__ = "2.0"
__author__ = "Green DevOps Team"
