"""
Decision engine for Engine 2.

Evaluates scenarios and recommends optimal action based on carbon emissions.
"""

import logging
from typing import Dict, Any, List, Optional
from carbon_engine.carbon_calculator import CarbonCalculator
from carbon_engine.scenario_simulator import Scenario
from carbon_engine.config import (
    CARBON_SAVING_THRESHOLD_PERCENT,
    DECISION_SCALE_UP,
    DECISION_DELAY_JOBS,
    DECISION_HYBRID,
    DECISION_NO_ACTION
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Make optimal decisions based on carbon scenarios.
    
    Decision criteria:
    1. Minimize carbon emissions
    2. Acceptable performance impact
    3. Meaningful carbon savings threshold
    """
    
    def __init__(self, carbon_calculator: Optional[CarbonCalculator] = None):
        """
        Initialize decision engine.
        
        Args:
            carbon_calculator: CarbonCalculator instance (creates default if None)
        """
        self.carbon_calculator = carbon_calculator or CarbonCalculator()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("DecisionEngine initialized")
    
    def recommend_action(
        self,
        scenarios: List[Scenario],
        current_pods: int,
        predicted_cpu: float,
        load_level: str
    ) -> Dict[str, Any]:
        """
        Recommend optimal action based on scenarios.
        
        SLA-aware recommendation that considers both carbon and performance safety.
        High load scenarios prioritize maintaining pod capacity over carbon reduction.
        
        Args:
            scenarios: List of Scenario objects
            current_pods: Current pod count
            predicted_cpu: Predicted CPU percentage
            load_level: Predicted load level (LOW/NORMAL/HIGH)
        
        Returns:
            Dict with recommendation and reasoning
        """
        if not scenarios:
            self.logger.warning("No scenarios to evaluate")
            return self._no_action_response("No scenarios available")
        
        baseline_scenario = next(
            (s for s in scenarios if s.name == "raw_scale"),
            scenarios[0]
        )
        
        # SLA-AWARE FILTERING: During HIGH load, only consider safe scenarios
        # HIGH load = load_level is HIGH or predicted_cpu >= 70%
        is_high_load = load_level == "HIGH" or predicted_cpu >= 70.0
        
        if is_high_load:
            # During high load, only consider scenarios that maintain or exceed raw capacity
            safe_scenarios = [
                s for s in scenarios 
                if s.required_pods >= baseline_scenario.required_pods
            ]
            
            if safe_scenarios:
                # Use the best safe scenario for carbon optimization within safety bounds
                best_scenario = min(safe_scenarios, key=lambda s: s.estimated_carbon_gco2)
                self.logger.info(
                    f"HIGH LOAD: Filtering to safe scenarios. "
                    f"Selected {best_scenario.name} with {best_scenario.required_pods} pods "
                    f"(minimum {baseline_scenario.required_pods} required)"
                )
            else:
                # No safe scenario found, use baseline
                best_scenario = baseline_scenario
                self.logger.warning(
                    f"HIGH LOAD: No safe scenario found below baseline. Using raw_scale."
                )
        else:
            # For LOW/MEDIUM load, use lowest carbon scenario
            best_scenario = min(scenarios, key=lambda s: s.estimated_carbon_gco2)
        
        # Calculate carbon savings
        carbon_saved = baseline_scenario.estimated_carbon_gco2 - best_scenario.estimated_carbon_gco2
        carbon_percent_saved = self.carbon_calculator.calculate_carbon_saving_percent(
            best_scenario.estimated_carbon_gco2,
            baseline_scenario.estimated_carbon_gco2
        )
        
        self.logger.info(
            f"Decision: {best_scenario.name} recommended "
            f"({carbon_percent_saved:.1f}% carbon saving)"
        )
        
        # Decide action type
        action, reason = self._determine_action(
            best_scenario,
            baseline_scenario,
            current_pods,
            carbon_percent_saved,
            load_level,
            is_high_load
        )
        
        return {
            "recommended_action": action,
            "reason": reason,
            "optimized_required_pods": best_scenario.required_pods,
            "carbon_saving_gco2": round(carbon_saved, 2),
            "carbon_saving_percent": carbon_percent_saved,
            "workload_reduction_percent": best_scenario.workload_reduction_percent,
            "performance_impact": best_scenario.performance_impact,
            "current_pods": current_pods,
            "baseline_carbon_gco2": round(baseline_scenario.estimated_carbon_gco2, 2),
            "optimized_carbon_gco2": round(best_scenario.estimated_carbon_gco2, 2)
        }
    
    def _determine_action(
        self,
        best_scenario: Scenario,
        baseline_scenario: Scenario,
        current_pods: int,
        carbon_percent_saved: float,
        load_level: str,
        is_high_load: bool = False
    ) -> tuple:
        """
        Determine action type and reasoning.
        
        SLA-aware reasoning that explains high-load protections.
        
        Returns:
            Tuple of (action_type, reason_string)
        """
        # If best scenario is baseline, no action needed
        if best_scenario.name == baseline_scenario.name:
            if best_scenario.required_pods <= current_pods:
                if is_high_load:
                    reason = f"High load detected ({best_scenario.required_pods} pods required); maintaining raw pod requirement to preserve performance."
                else:
                    reason = f"Current capacity sufficient; load_level={load_level}"
                return DECISION_NO_ACTION, reason
            else:
                reason = f"Scale up to {best_scenario.required_pods} pods for {load_level} load"
                return DECISION_SCALE_UP, reason
        
        # HIGH LOAD PROTECTION: Never allow unsafe pod reduction
        if is_high_load and best_scenario.required_pods < baseline_scenario.required_pods:
            # During high load, recommend baseline instead of risky reduction
            reason = f"High load detected; maintaining {baseline_scenario.required_pods} pods to preserve performance and SLA."
            return DECISION_SCALE_UP if baseline_scenario.required_pods > current_pods else DECISION_NO_ACTION, reason
        
        # Check carbon savings threshold
        if carbon_percent_saved < CARBON_SAVING_THRESHOLD_PERCENT:
            reason = (
                f"Carbon savings {carbon_percent_saved:.1f}% below threshold "
                f"({CARBON_SAVING_THRESHOLD_PERCENT}%); prefer stable scaling"
            )
            action = DECISION_SCALE_UP if best_scenario.required_pods > current_pods else DECISION_NO_ACTION
            return action, reason
        
        # Recommend based on scenario type
        if "optimized" in best_scenario.name or "delay" in best_scenario.description.lower():
            # SAFE HYBRID LOGIC: Only allow if still safe
            if is_high_load:
                reason = (
                    f"High load allows hybrid decision with job delay. "
                    f"Delay {best_scenario.workload_reduction_percent:.0f}% of workload "
                    f"to reduce pods to {best_scenario.required_pods} "
                    f"(from {baseline_scenario.required_pods}) while saving "
                    f"{carbon_percent_saved:.1f}% carbon."
                )
            else:
                reason = (
                    f"Delay {best_scenario.workload_reduction_percent:.0f}% of jobs to "
                    f"reduce pods from {baseline_scenario.required_pods} to "
                    f"{best_scenario.required_pods} and save "
                    f"{carbon_percent_saved:.1f}% carbon"
                )
            return DECISION_DELAY_JOBS, reason
        
        # Pod reduction scenario (but not during high load - this is protected above)
        if best_scenario.required_pods < baseline_scenario.required_pods:
            reason = (
                f"Scale down from {baseline_scenario.required_pods} to "
                f"{best_scenario.required_pods} pods, saving "
                f"{carbon_percent_saved:.1f}% carbon (safe for {load_level} load)"
            )
            return DECISION_HYBRID, reason
        
        reason = f"Scale to {best_scenario.required_pods} pods for efficiency"
        return DECISION_SCALE_UP, reason
    
    def _no_action_response(self, reason: str) -> Dict[str, Any]:
        """Return a no-action response."""
        return {
            "recommended_action": DECISION_NO_ACTION,
            "reason": reason,
            "optimized_required_pods": 0,
            "carbon_saving_gco2": 0.0,
            "carbon_saving_percent": 0.0,
            "workload_reduction_percent": 0.0,
            "performance_impact": "none"
        }
    
    def get_decision_justification(self, decision: Dict[str, Any]) -> str:
        """
        Generate human-readable justification for decision.
        
        Args:
            decision: Decision dict from recommend_action()
        
        Returns:
            Formatted justification string
        """
        parts = [
            f"Decision: {decision['recommended_action'].replace('_', ' ').title()}",
            f"Pod adjustment: {decision.get('optimized_required_pods', 'N/A')} pods",
            f"Carbon saved: {decision['carbon_saving_gco2']:.0f}g CO2 "
            f"({decision['carbon_saving_percent']:.1f}%)"
        ]
        
        if decision.get('workload_reduction_percent', 0) > 0:
            parts.append(
                f"Delay workload: {decision['workload_reduction_percent']:.0f}%"
            )
        
        parts.append(f"Reason: {decision['reason']}")
        
        return " | ".join(parts)
