"""
Decision Layer Orchestrator

Main orchestrator that merges Engine 1, Engine 2, and Engine 3 outputs
and applies policy rules to produce the final decision.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .config import DecisionLayerConfig
from .output_contract import DecisionContext, DecisionOutput
from .policy_rules import PolicyRules


logger = logging.getLogger(__name__)


class DecisionOrchestrator:
    """
    Main orchestrator for the Decision Layer.
    
    Responsibilities:
    - Accept Engine 1, 2, and 3 outputs
    - Build merged decision context
    - Apply policy rules
    - Validate and return final decision
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.config = DecisionLayerConfig()
        self.policy_rules = PolicyRules()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def evaluate(
        self,
        engine1_output: Dict[str, Any],
        engine2_output: Dict[str, Any],
        engine3_output: Optional[Dict[str, Any]] = None,
        current_pods: int = 1
    ) -> DecisionOutput:
        """
        Produce final decision by merging all engine outputs.
        
        Args:
            engine1_output: Output from Engine 1 (workload prediction)
            engine2_output: Output from Engine 2 (carbon analysis)
            engine3_output: Optional output from Engine 3 (job prioritization)
            current_pods: Current pod count in the system
        
        Returns:
            Final DecisionOutput with merged decision
        
        Raises:
            ValueError: If inputs are invalid or incomplete
            KeyError: If required fields are missing
        """
        try:
            # Extract and validate Engine 1 data
            engine1_data = self._extract_engine1_data(engine1_output)
            
            # Extract and validate Engine 2 data
            engine2_data = self._extract_engine2_data(engine2_output)
            
            # Extract Engine 3 data (optional)
            engine3_data = self._extract_engine3_data(engine3_output) if engine3_output else {}
            
            # Build merged context
            context = self._build_decision_context(
                engine1_data=engine1_data,
                engine2_data=engine2_data,
                engine3_data=engine3_data,
                current_pods=current_pods
            )
            
            # Log the merged context for debugging
            self.logger.info("Decision context built:")
            self.logger.info(context.get_summary())
            
            # Apply policy rules
            decision = self.policy_rules.apply_policy(context)
            
            # Validate decision
            decision.validate()
            
            # Log final decision
            self.logger.info(
                f"Final decision: action={decision.final_action}, "
                f"pods={decision.final_required_pods}, "
                f"carbon_saving={decision.carbon_saving_gco2:.2f}g"
            )
            
            return decision
        
        except Exception as e:
            self.logger.error(f"Decision evaluation failed: {e}")
            raise
    
    def _extract_engine1_data(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and validate Engine 1 output data.
        
        Args:
            output: Engine 1 output dictionary
        
        Returns:
            Validated Engine 1 data
        
        Raises:
            ValueError: If required fields missing or invalid
        """
        # Handle both wrapped (with "prediction" key) and unwrapped responses
        if "prediction" in output:
            data = output["prediction"]
        else:
            data = output
        
        # Extract required fields
        try:
            predicted_cpu = float(data.get("predicted_cpu"))
            load_level = str(data.get("predicted_load_level", "NORMAL"))
            recommended_pods = int(data.get("recommended_pods", 1))
            confidence = float(data.get("confidence", 0.0))
        except (ValueError, TypeError, KeyError) as e:
            raise ValueError(f"Invalid Engine 1 data: {e}")
        
        # Validate ranges
        if not (0 <= predicted_cpu <= 100):
            raise ValueError(f"predicted_cpu out of range: {predicted_cpu}")
        
        if load_level not in ["LOW", "NORMAL", "HIGH"]:
            raise ValueError(f"Invalid load_level: {load_level}")
        
        if recommended_pods < 1:
            raise ValueError(f"recommended_pods must be >= 1: {recommended_pods}")
        
        return {
            "predicted_cpu": predicted_cpu,
            "load_level": load_level,
            "recommended_pods": recommended_pods,
            "confidence": confidence
        }
    
    def _extract_engine2_data(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and validate Engine 2 output data.
        
        Args:
            output: Engine 2 output dictionary
        
        Returns:
            Validated Engine 2 data
        
        Raises:
            ValueError: If required fields missing or invalid
        """
        try:
            # Extract raw scenario
            raw_scenario = output.get("raw_scenario", {})
            raw_pods = int(raw_scenario.get("required_pods", 1))
            
            # Extract optimized scenario (optional)
            optimized_scenario = output.get("optimized_scenario")
            optimized_pods = None
            if optimized_scenario:
                optimized_pods = int(optimized_scenario.get("required_pods"))
            
            # Extract carbon metrics
            carbon_saving_gco2 = float(output.get("carbon_saving_gco2", 0.0))
            carbon_saving_percent = float(output.get("carbon_saving_percent", 0.0))
            
            # Extract metadata
            metadata = output.get("metadata", {})
            sla_protected = bool(metadata.get("sla_protected", False))
            
            # Extract action and reason
            recommended_action = str(output.get("recommended_action", "no_action"))
            reason = str(output.get("reason", ""))
        
        except (ValueError, TypeError, KeyError) as e:
            raise ValueError(f"Invalid Engine 2 data: {e}")
        
        # Validate ranges
        if raw_pods < 1:
            raise ValueError(f"raw_pods must be >= 1: {raw_pods}")
        
        if optimized_pods is not None and optimized_pods < 1:
            raise ValueError(f"optimized_pods must be >= 1: {optimized_pods}")
        
        if carbon_saving_gco2 < 0:
            raise ValueError(f"carbon_saving_gco2 must be >= 0: {carbon_saving_gco2}")
        
        return {
            "raw_pods": raw_pods,
            "optimized_pods": optimized_pods,
            "carbon_saving_gco2": carbon_saving_gco2,
            "carbon_saving_percent": carbon_saving_percent,
            "sla_protected": sla_protected,
            "recommended_action": recommended_action,
            "reason": reason
        }
    
    def _extract_engine3_data(self, output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract and validate Engine 3 output data (optional).
        
        Args:
            output: Engine 3 output dictionary or None
        
        Returns:
            Validated Engine 3 data or empty dict if None
        
        Raises:
            ValueError: If provided data is invalid
        """
        if output is None:
            return {}
        
        try:
            delayable_jobs = int(output.get("delayable_jobs", 0))
            delayable_job_ids = output.get("delayable_job_ids", [])
            workload_reduction_percent = float(output.get("workload_reduction_percent", 0.0))
            reason = str(output.get("reason", ""))
        
        except (ValueError, TypeError, KeyError) as e:
            raise ValueError(f"Invalid Engine 3 data: {e}")
        
        # Validate ranges
        if delayable_jobs < 0:
            raise ValueError(f"delayable_jobs must be >= 0: {delayable_jobs}")
        
        if not isinstance(delayable_job_ids, list):
            raise ValueError(f"delayable_job_ids must be list")
        
        if not (0 <= workload_reduction_percent <= 1.0):
            raise ValueError(
                f"workload_reduction_percent must be 0-1: {workload_reduction_percent}"
            )
        
        return {
            "delayable_jobs": delayable_jobs,
            "delayable_job_ids": delayable_job_ids,
            "workload_reduction_percent": workload_reduction_percent,
            "reason": reason
        }
    
    def _build_decision_context(
        self,
        engine1_data: Dict[str, Any],
        engine2_data: Dict[str, Any],
        engine3_data: Dict[str, Any],
        current_pods: int
    ) -> DecisionContext:
        """
        Build merged decision context from all engines.
        
        Args:
            engine1_data: Validated Engine 1 data
            engine2_data: Validated Engine 2 data
            engine3_data: Validated Engine 3 data (may be empty)
            current_pods: Current pod count
        
        Returns:
            Merged DecisionContext
        """
        context = DecisionContext(
            # Engine 1
            engine1_predicted_cpu=engine1_data["predicted_cpu"],
            engine1_load_level=engine1_data["load_level"],
            engine1_recommended_pods=engine1_data["recommended_pods"],
            engine1_confidence=engine1_data.get("confidence"),
            
            # Engine 2
            engine2_raw_required_pods=engine2_data["raw_pods"],
            engine2_optimized_required_pods=engine2_data["optimized_pods"],
            engine2_recommended_action=engine2_data["recommended_action"],
            engine2_carbon_saving_gco2=engine2_data["carbon_saving_gco2"],
            engine2_carbon_saving_percent=engine2_data["carbon_saving_percent"],
            engine2_sla_protected=engine2_data["sla_protected"],
            engine2_reason=engine2_data["reason"],
            
            # Engine 3 (optional)
            engine3_delayable_jobs=engine3_data.get("delayable_jobs", 0),
            engine3_delayable_job_ids=engine3_data.get("delayable_job_ids", []),
            engine3_workload_reduction_percent=engine3_data.get("workload_reduction_percent", 0.0),
            engine3_reason=engine3_data.get("reason", ""),
            
            # System state
            current_pods=current_pods,
            current_cpu=engine1_data["predicted_cpu"]  # Use predicted as current proxy
        )
        
        return context
