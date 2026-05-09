"""
Main Engine 2 orchestrator - Carbon Emission Engine.

Integrates energy, carbon, scenario, and decision components.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from carbon_engine.energy_model import EnergyModel
from carbon_engine.carbon_calculator import CarbonCalculator
from carbon_engine.scenario_simulator import ScenarioSimulator
from carbon_engine.decision_engine import DecisionEngine
from carbon_engine.config import LOG_LEVEL, ENABLE_DETAILED_LOGGING

logger = logging.getLogger(__name__)


class CarbonEmissionEngine:
    """
    Main Engine 2 orchestrator for carbon analysis.
    
    Workflow:
    1. Accept prediction from Engine 1
    2. Create energy/carbon scenarios
    3. Evaluate options
    4. Return decision recommendation
    """
    
    def __init__(self):
        """Initialize Engine 2 components."""
        self.energy_model = EnergyModel()
        self.carbon_calculator = CarbonCalculator()
        self.scenario_simulator = ScenarioSimulator(
            energy_model=self.energy_model,
            carbon_calculator=self.carbon_calculator
        )
        self.decision_engine = DecisionEngine(
            carbon_calculator=self.carbon_calculator
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("CarbonEmissionEngine initialized")
    
    def evaluate(
        self,
        predicted_cpu: float,
        load_level: str,
        raw_required_pods: int,
        current_pods: int,
        prediction_window_seconds: int = 30,
        delayable_jobs: Optional[int] = None,
        workload_reduction_percent: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform complete carbon analysis and return recommendation.
        
        Args:
            predicted_cpu: Predicted CPU percentage (0-100) from Engine 1
            load_level: Predicted load level (LOW/NORMAL/HIGH) from Engine 1
            raw_required_pods: Recommended pods from Engine 1
            current_pods: Current pod count in system
            prediction_window_seconds: Time window for prediction (default 30sec)
            delayable_jobs: Optional count of jobs that can be delayed (from Engine 3)
            workload_reduction_percent: Optional percentage workload reduction (from Engine 3)
        
        Returns:
            Structured decision output with scenarios and recommendation
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Input validation
        if not 0 <= predicted_cpu <= 100:
            raise ValueError(f"predicted_cpu must be 0-100, got {predicted_cpu}")
        
        if load_level not in ("LOW", "NORMAL", "HIGH"):
            raise ValueError(f"load_level must be LOW/NORMAL/HIGH, got {load_level}")
        
        if raw_required_pods < 1:
            raise ValueError(f"raw_required_pods must be >= 1, got {raw_required_pods}")
        
        if current_pods < 1:
            raise ValueError(f"current_pods must be >= 1, got {current_pods}")
        
        if prediction_window_seconds <= 0:
            raise ValueError(
                f"prediction_window_seconds must be > 0, got {prediction_window_seconds}"
            )
        
        # Validate Engine 3 inputs if provided
        if workload_reduction_percent is not None:
            if not 0 <= workload_reduction_percent <= 1.0:
                raise ValueError(
                    f"workload_reduction_percent must be 0-1 float, got {workload_reduction_percent}"
                )
            if delayable_jobs is not None and delayable_jobs < 0:
                raise ValueError(f"delayable_jobs must be >= 0, got {delayable_jobs}")
        
        self.logger.info(
            f"Engine 2 evaluation starting: "
            f"CPU={predicted_cpu}%, load={load_level}, pods={raw_required_pods}"
        )
        if workload_reduction_percent is not None:
            self.logger.info(
                f"Engine 3 support: {workload_reduction_percent:.1%} workload reduction, "
                f"{delayable_jobs} delayable jobs"
            )
        
        # Step 1: Create scenarios
        scenarios = self.scenario_simulator.create_scenarios(
            predicted_cpu=predicted_cpu,
            raw_required_pods=raw_required_pods,
            current_pods=current_pods,
            prediction_window_seconds=prediction_window_seconds,
            workload_reduction_percent=workload_reduction_percent,
            delayable_jobs=delayable_jobs
        )
        
        # Step 2: Get decision recommendation
        baseline = next(
            (s for s in scenarios if s.name == "raw_scale"),
            scenarios[0]
        )
        optimized = next(
            (s for s in scenarios if s.name == "optimized_scale"),
            None
        )
        decision = self.decision_engine.recommend_action(
            scenarios=scenarios,
            current_pods=current_pods,
            predicted_cpu=predicted_cpu,
            load_level=load_level
        )
        
        # Step 3: Build explicit raw vs optimized scenario comparison
        raw_scenario_dict = {
            "required_pods": baseline.required_pods,
            "estimated_energy_kwh": round(baseline.estimated_energy_kwh, 6),
            "estimated_carbon_gco2": round(baseline.estimated_carbon_gco2, 2)
        }
        
        optimized_scenario_dict = None
        if optimized:
            optimized_scenario_dict = {
                "required_pods": optimized.required_pods,
                "estimated_energy_kwh": round(optimized.estimated_energy_kwh, 6),
                "estimated_carbon_gco2": round(optimized.estimated_carbon_gco2, 2),
                "delayable_jobs": delayable_jobs,
                "workload_reduction_percent": round(workload_reduction_percent, 3) if workload_reduction_percent else None
            }
        
        # Step 4: Build output with explicit raw vs optimized scenarios
        output = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "engine_version": "2.1",
            "input": {
                "predicted_cpu": predicted_cpu,
                "load_level": load_level,
                "raw_required_pods": raw_required_pods,
                "current_pods": current_pods,
                "prediction_window_seconds": prediction_window_seconds,
                "has_engine3_data": delayable_jobs is not None or workload_reduction_percent is not None
            },
            "raw_scenario": raw_scenario_dict,
            "optimized_scenario": optimized_scenario_dict,
            "recommended_action": decision["recommended_action"],
            "optimized_required_pods": decision["optimized_required_pods"],
            "carbon_saving_gco2": decision["carbon_saving_gco2"],
            "carbon_saving_percent": decision["carbon_saving_percent"],
            "reason": decision["reason"],
            "scenarios": self.scenario_simulator.scenarios_to_dict(scenarios),
            "metadata": {
                "energy_model": self.energy_model.get_model_info(),
                "carbon_calculator": self.carbon_calculator.get_calculator_info(),
                "sla_protected": self._check_sla_protection(predicted_cpu, load_level, baseline, decision)
            }
        }
        
        self.logger.info(
            f"Engine 2 evaluation complete: "
            f"Recommending {decision['recommended_action']} "
            f"({decision['carbon_saving_percent']:.1f}% carbon saving)"
        )
        
        if ENABLE_DETAILED_LOGGING:
            self.logger.debug(f"Full output: {output}")
        
        return output
    
    def _check_sla_protection(
        self,
        predicted_cpu: float,
        load_level: str,
        baseline_scenario,
        decision: Dict[str, Any]
    ) -> bool:
        """
        Check if SLA protection was applied during decision.
        
        Returns True if HIGH LOAD was detected and SLA constraints were enforced.
        """
        is_high_load = predicted_cpu >= 70.0 or load_level == "HIGH"
        pods_maintained = decision["optimized_required_pods"] >= baseline_scenario.required_pods
        
        return is_high_load and pods_maintained


# ============================================================================
# INTEGRATION FUNCTION FOR API/DASHBOARD
# ============================================================================

def run_carbon_engine(
    engine1_prediction: Dict[str, Any],
    engine3_output: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    High-level integration function for Engine 2.
    
    Accepts output directly from Engine 1, optionally from Engine 3,
    and returns carbon analysis.
    
    Args:
        engine1_prediction: Prediction output from Engine 1 containing:
            - predicted_cpu (float)
            - predicted_load_level (str)
            - recommended_pods (int)
        engine3_output: Optional output from Engine 3 containing:
            - delayable_jobs (int)
            - workload_reduction_percent (float)
    
    Returns:
        Engine 2 decision output (see CarbonEmissionEngine.evaluate())
    
    Example:
        >>> # From Engine 1
        >>> e1_output = {
        ...     "predicted_cpu": 75.5,
        ...     "predicted_load_level": "HIGH",
        ...     "recommended_pods": 5
        ... }
        >>>
        >>> # From Engine 3 (optional)
        >>> e3_output = {
        ...     "delayable_jobs": 15,
        ...     "workload_reduction_percent": 20.0
        ... }
        >>>
        >>> # Run Engine 2
        >>> result = run_carbon_engine(e1_output, e3_output)
        >>> print(result["decision"]["recommended_action"])
        "delay_jobs"
    """
    # Extract Engine 1 inputs
    predicted_cpu = engine1_prediction.get("predicted_cpu", 50.0)
    load_level = engine1_prediction.get("predicted_load_level", "NORMAL")
    raw_required_pods = engine1_prediction.get("recommended_pods", 2)
    current_pods = engine1_prediction.get("current_pods", raw_required_pods)
    prediction_window = engine1_prediction.get("prediction_window_seconds", 30)
    
    # Extract Engine 3 inputs (optional)
    delayable_jobs = None
    workload_reduction_percent = None
    
    if engine3_output:
        delayable_jobs = engine3_output.get("delayable_jobs")
        workload_reduction_percent = engine3_output.get("workload_reduction_percent")
    
    # Run Engine 2
    engine2 = CarbonEmissionEngine()
    
    try:
        result = engine2.evaluate(
            predicted_cpu=predicted_cpu,
            load_level=load_level,
            raw_required_pods=raw_required_pods,
            current_pods=current_pods,
            prediction_window_seconds=prediction_window,
            delayable_jobs=delayable_jobs,
            workload_reduction_percent=workload_reduction_percent
        )
        return result
    
    except ValueError as e:
        logger.error(f"Engine 2 evaluation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Engine 2: {e}")
        raise
