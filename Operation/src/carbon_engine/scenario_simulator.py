"""
Scenario simulator for Engine 2.

Creates and evaluates different scaling scenarios based on Engine 1 predictions.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from carbon_engine.energy_model import EnergyModel
from carbon_engine.carbon_calculator import CarbonCalculator
from carbon_engine.config import (
    MIN_REQUIRED_PODS,
    MAX_PODS,
    MAX_ALLOWED_REDUCTION_PERCENT,
    MIN_MEANINGFUL_REDUCTION_PERCENT
)

logger = logging.getLogger(__name__)


@dataclass
class Scenario:
    """Single scaling scenario with energy and carbon metrics."""
    
    name: str
    description: str
    required_pods: int
    estimated_energy_kwh: float
    estimated_carbon_gco2: float
    workload_reduction_percent: float = 0.0
    performance_impact: str = "none"


class ScenarioSimulator:
    """
    Create and simulate different scaling scenarios.
    
    Scenarios:
    1. Raw scaling: Use Engine 1 recommendation as-is
    2. Optimized scaling: Apply workload reduction (delay jobs)
    3. Hybrid: Partial pod reduction + partial delay
    4. Conservative: Minimal scaling for reliability
    """
    
    def __init__(
        self,
        energy_model: Optional[EnergyModel] = None,
        carbon_calculator: Optional[CarbonCalculator] = None
    ):
        """
        Initialize scenario simulator.
        
        Args:
            energy_model: EnergyModel instance (creates default if None)
            carbon_calculator: CarbonCalculator instance (creates default if None)
        """
        self.energy_model = energy_model or EnergyModel()
        self.carbon_calculator = carbon_calculator or CarbonCalculator()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("ScenarioSimulator initialized")
    
    def create_scenarios(
        self,
        predicted_cpu: float,
        raw_required_pods: int,
        current_pods: int,
        prediction_window_seconds: int,
        workload_reduction_percent: Optional[float] = None,
        delayable_jobs: Optional[int] = None
    ) -> List[Scenario]:
        """
        Create all applicable scenarios.
        
        Args:
            predicted_cpu: Predicted CPU percentage (0-100)
            raw_required_pods: Recommended pods from Engine 1
            current_pods: Current pod count
            prediction_window_seconds: Time window for prediction
            workload_reduction_percent: Optional reduction from job delay
            delayable_jobs: Optional count of delayable jobs (for logging)
        
        Returns:
            List of Scenario objects
        """
        scenarios = []
        
        # Scenario 1: Raw scaling (Engine 1 recommendation)
        raw_scenario = self._create_raw_scenario(
            raw_required_pods,
            prediction_window_seconds
        )
        scenarios.append(raw_scenario)
        
        # Scenario 2: Optimized scaling (with workload reduction if available)
        if workload_reduction_percent is not None and workload_reduction_percent > 0:
            optimized_scenario = self._create_optimized_scenario(
                raw_required_pods,
                workload_reduction_percent,
                prediction_window_seconds
            )
            scenarios.append(optimized_scenario)
        
        # Scenario 3: Conservative (minimum viable)
        conservative_scenario = self._create_conservative_scenario(
            prediction_window_seconds
        )
        scenarios.append(conservative_scenario)
        
        self.logger.info(f"Created {len(scenarios)} scenarios")
        for scenario in scenarios:
            self.logger.debug(
                f"  {scenario.name}: {scenario.required_pods} pods, "
                f"{scenario.estimated_carbon_gco2:.0f} g CO2"
            )
        
        return scenarios
    
    def _create_raw_scenario(
        self,
        required_pods: int,
        time_window_seconds: int
    ) -> Scenario:
        """Create raw scaling scenario from Engine 1 prediction."""
        # Constrain pods
        constrained_pods = max(MIN_REQUIRED_PODS, min(required_pods, MAX_PODS))
        
        # Calculate energy and carbon
        energy = self.energy_model.calculate_energy(constrained_pods, time_window_seconds)
        carbon = self.carbon_calculator.calculate_carbon(energy)
        
        return Scenario(
            name="raw_scale",
            description="Direct scaling from Engine 1 prediction",
            required_pods=constrained_pods,
            estimated_energy_kwh=energy,
            estimated_carbon_gco2=carbon,
            workload_reduction_percent=0.0,
            performance_impact="none"
        )
    
    def _create_optimized_scenario(
        self,
        required_pods: int,
        workload_reduction_percent: float,
        time_window_seconds: int
    ) -> Scenario:
        """Create optimized scenario with workload reduction.
        
        Engine 3 Integration:
        workload_reduction_percent is a float 0-1 representing fraction of workload
        that can be delayed. E.g., 0.4 means 40% of workload can be deferred.
        
        Formula: optimized_pods = ceil(raw_pods * (1 - reduction))
        Example: 5 pods with 0.4 reduction = ceil(5 * 0.6) = 3 pods
        """
        # Validate reduction percentage (0-1 float)
        if workload_reduction_percent < 0 or workload_reduction_percent > 1.0:
            self.logger.warning(
                f"Workload reduction {workload_reduction_percent} out of range [0, 1.0], clamping"
            )
            workload_reduction_percent = min(1.0, max(0, workload_reduction_percent))
        
        # Calculate effective pods after workload reduction
        # Using float to float calculation (not percentage)
        import math
        adjusted_workload = 1.0 - workload_reduction_percent
        effective_pods_float = required_pods * adjusted_workload
        effective_pods = max(MIN_REQUIRED_PODS, math.ceil(effective_pods_float))
        
        self.logger.info(
            f"Optimized scenario: {required_pods} raw pods * "
            f"{adjusted_workload:.1%} adjusted workload = {effective_pods_float:.1f} -> "
            f"{effective_pods} pods (reduction: {workload_reduction_percent:.1%})"
        )
        
        # Calculate energy and carbon
        energy = self.energy_model.calculate_energy(effective_pods, time_window_seconds)
        carbon = self.carbon_calculator.calculate_carbon(energy)
        
        return Scenario(
            name="optimized_scale",
            description=f"Scaling with {workload_reduction_percent:.1%} workload delay (Engine 3 support)",
            required_pods=effective_pods,
            estimated_energy_kwh=energy,
            estimated_carbon_gco2=carbon,
            workload_reduction_percent=workload_reduction_percent,
            performance_impact="minor_delay"
        )
    
    def _create_conservative_scenario(
        self,
        time_window_seconds: int
    ) -> Scenario:
        """Create conservative (minimum viable) scenario."""
        pods = MIN_REQUIRED_PODS
        
        energy = self.energy_model.calculate_energy(pods, time_window_seconds)
        carbon = self.carbon_calculator.calculate_carbon(energy)
        
        return Scenario(
            name="conservative",
            description="Minimum viable: baseline operation only",
            required_pods=pods,
            estimated_energy_kwh=energy,
            estimated_carbon_gco2=carbon,
            workload_reduction_percent=0.0,
            performance_impact="potential_degradation"
        )
    
    def scenarios_to_dict(self, scenarios: List[Scenario]) -> List[Dict[str, Any]]:
        """Convert scenarios to dictionaries for JSON output."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "required_pods": s.required_pods,
                "estimated_energy_kwh": round(s.estimated_energy_kwh, 6),
                "estimated_carbon_gco2": round(s.estimated_carbon_gco2, 2),
                "workload_reduction_percent": round(s.workload_reduction_percent, 3),
                "performance_impact": s.performance_impact
            }
            for s in scenarios
        ]
    
    def compare_scenarios(
        self,
        baseline: Scenario,
        alternatives: List[Scenario]
    ) -> Dict[str, Any]:
        """
        Compare scenarios and calculate savings.
        
        Args:
            baseline: Baseline scenario (usually raw_scale)
            alternatives: Scenarios to compare against baseline
        
        Returns:
            Dict with comparison metrics
        """
        comparison = {}
        
        for alt in alternatives:
            if alt.name == baseline.name:
                continue
            
            carbon_saved = baseline.estimated_carbon_gco2 - alt.estimated_carbon_gco2
            carbon_percent = self.carbon_calculator.calculate_carbon_saving_percent(
                alt.estimated_carbon_gco2,
                baseline.estimated_carbon_gco2
            )
            energy_saved = baseline.estimated_energy_kwh - alt.estimated_energy_kwh
            
            comparison[alt.name] = {
                "carbon_saved_gco2": round(carbon_saved, 2),
                "carbon_saving_percent": carbon_percent,
                "energy_saved_kwh": round(energy_saved, 6),
                "pod_reduction": baseline.required_pods - alt.required_pods
            }
        
        self.logger.debug(f"Scenario comparison: {comparison}")
        
        return comparison
    
    def scenarios_to_dict(self, scenarios: List[Scenario]) -> List[Dict[str, Any]]:
        """Convert Scenario dataclass to JSON-serializable dict."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "required_pods": s.required_pods,
                "estimated_energy_kwh": s.estimated_energy_kwh,
                "estimated_carbon_gco2": s.estimated_carbon_gco2,
                "workload_reduction_percent": s.workload_reduction_percent,
                "performance_impact": s.performance_impact
            }
            for s in scenarios
        ]
