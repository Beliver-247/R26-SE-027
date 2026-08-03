"""
Decision Layer Policy Rules

Implements decision rules for different load levels and scenarios.
The policy rules are the core logic that converts merged engine outputs
into final actions.
"""

from typing import Optional, List, Tuple
import logging

from .config import DecisionLayerConfig, HighLoadPolicy, NormalLoadPolicy, LowLoadPolicy
from .output_contract import DecisionContext, DecisionOutput


logger = logging.getLogger(__name__)


class PolicyRules:
    """
    Decision policy rules based on load level.
    
    These rules determine the final action based on merged engine outputs.
    """
    
    def __init__(self):
        """Initialize policy rules."""
        self.config = DecisionLayerConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def apply_policy(self, context: DecisionContext) -> DecisionOutput:
        """
        Apply the appropriate policy rule based on load level.
        
        Args:
            context: Merged decision context from all engines
        
        Returns:
            Final decision output
        
        Raises:
            ValueError: If context is invalid
        """
        # Validate context
        if context.engine1_load_level not in ["HIGH", "NORMAL", "LOW"]:
            raise ValueError(f"Invalid load level: {context.engine1_load_level}")
        
        # Route to appropriate policy
        if context.engine1_load_level == "HIGH":
            return self._apply_high_load_policy(context)
        elif context.engine1_load_level == "NORMAL":
            return self._apply_normal_load_policy(context)
        else:  # LOW
            return self._apply_low_load_policy(context)
    
    def _apply_high_load_policy(self, context: DecisionContext) -> DecisionOutput:
        """
        Apply HIGH LOAD policy.
        
        During HIGH load, SLA protection is paramount.
        
        RULE: Keep pods >= raw_required_pods (mandatory SLA protection)
        - Pod reduction is NEVER allowed
        - Job delay is OPTIONAL (only after SLA via required pods is guaranteed)
        - Carbon optimization via pod reduction is NOT applied
        
        Action priority:
        1. Scale UP if needed (pods < raw_required_pods)
        2. Delay jobs if already at safe level (pods >= raw_required_pods) - OPTIONAL
        3. No action if stable
        """
        policy = self.config.HIGH_LOAD_POLICY
        
        # SLA protection: final pods must be >= raw_required_pods
        # This ensures SLA is met before considering any optimization strategies
        final_pods = max(context.engine2_raw_required_pods, context.current_pods)
        
        # Determine action based on pod safety level
        if context.current_pods < context.engine2_raw_required_pods:
            # PRIORITY 1: Scale UP if below safe level (mandatory for SLA)
            action = "scale_up"
            reason = (
                f"{policy.reason_prefix}. Current pods ({context.current_pods}) < "
                f"required pods ({context.engine2_raw_required_pods}). Scaling up for SLA protection."
            )
            jobs_to_delay = []
            job_count = 0
        elif context.has_engine3_data() and context.engine3_delayable_jobs > 0 and policy.allow_delayed_jobs:
            # PRIORITY 2: Delay jobs if safe level reached (OPTIONAL, secondary strategy)
            # This reduces workload pressure without affecting SLA
            action = "delay_jobs"
            reason = (
                f"{policy.reason_prefix}. Pods at safe level ({context.current_pods}). "
                f"Identified {context.engine3_delayable_jobs} delayable jobs. "
                f"[OPTIONAL] Delaying jobs to reduce workload pressure."
            )
            jobs_to_delay = context.engine3_delayable_job_ids
            job_count = context.engine3_delayable_jobs
        else:
            # PRIORITY 3: No action if stable and no job delay opportunities
            action = "no_action"
            reason = f"{policy.reason_prefix}. Current pods ({context.current_pods}) sufficient for SLA."
            jobs_to_delay = []
            job_count = 0
        
        # Build output with SLA guarantee
        output = DecisionOutput(
            timestamp=self._iso_timestamp(),
            decision_id=self._generate_decision_id("high"),
            final_action=action,
            raw_required_pods=context.engine2_raw_required_pods,
            optimized_required_pods=context.engine2_optimized_required_pods,
            final_required_pods=final_pods,
            jobs_to_delay=jobs_to_delay,
            delay_job_count=job_count,
            carbon_saving_gco2=0.0,  # No pod optimization in HIGH load
            carbon_saving_percent=0.0,
            sla_preserved=True,  # Always guaranteed in HIGH load
            reason=reason,
            policy_applied="HIGH_LOAD",
            input_load_level=context.engine1_load_level,
            input_predicted_cpu=context.engine1_predicted_cpu,
            input_current_pods=context.current_pods,
            had_engine3_data=context.has_engine3_data(),
            delayable_jobs_available=context.engine3_delayable_jobs,
        )
        
        return output
    
    def _apply_normal_load_policy(self, context: DecisionContext) -> DecisionOutput:
        """
        Apply NORMAL LOAD policy.
        
        During NORMAL load, balance between SLA and carbon optimization.
        
        RULE: Use optimized pods when beneficial and SLA permits
        - Pod reduction is allowed with safeguards
        - Job delay is encouraged (via hybrid approach)
        - Carbon optimization is applied when available
        
        Action priority:
        1. Scale UP if needed (pods < raw_required_pods)
        2. Use HYBRID if optimization available (pod reduction + job delay)
        3. Scale DOWN if no job delay opportunity
        4. No action if stable
        """
        policy = self.config.NORMAL_LOAD_POLICY
        
        # Determine final pods based on available optimization
        if (context.engine2_optimized_required_pods is not None and 
            context.engine2_optimized_required_pods < context.engine2_raw_required_pods):
            # Optimization is possible and beneficial
            final_pods = context.engine2_optimized_required_pods
            can_optimize = True
        else:
            # No optimization or not beneficial, use raw
            final_pods = context.engine2_raw_required_pods
            can_optimize = False
        
        # Ensure minimum pods
        final_pods = max(final_pods, self.config.MINIMUM_PODS)
        
        # Determine action based on current state
        if context.current_pods < context.engine2_raw_required_pods:
            final_pods = context.engine2_raw_required_pods
            action = "scale_up"
            reason = (
                f"{policy.reason_prefix}. Current pods ({context.current_pods}) < "
                f"required pods ({context.engine2_raw_required_pods}). Scaling up to meet demand."
            )
        elif can_optimize and context.engine3_delayable_jobs > 0 and policy.prefer_optimization:
            # HYBRID: Optimize pods AND delay jobs for maximum efficiency
            action = "hybrid"
            carbon_saved = context.engine2_carbon_saving_gco2
            reason = (
                f"{policy.reason_prefix}. Using hybrid: scale to {final_pods} pods + "
                f"delay {context.engine3_delayable_jobs} jobs. "
                f"Carbon saving: {carbon_saved:.2f}g CO2."
            )
        elif can_optimize and policy.allow_scale_down:
            # Scale down without pod optimization (no job delays)
            action = "scale_down"
            carbon_saved = context.engine2_carbon_saving_gco2
            reason = (
                f"{policy.reason_prefix}. Optimization available without job delays. "
                f"Scaling down to {final_pods} pods. Carbon saving: {carbon_saved:.2f}g CO2."
            )
        else:
            action = "no_action"
            reason = f"{policy.reason_prefix}. Current pods ({context.current_pods}) sufficient."
        
        # Build output
        output = DecisionOutput(
            timestamp=self._iso_timestamp(),
            decision_id=self._generate_decision_id("normal"),
            final_action=action,
            raw_required_pods=context.engine2_raw_required_pods,
            optimized_required_pods=context.engine2_optimized_required_pods,
            final_required_pods=final_pods,
            jobs_to_delay=(context.engine3_delayable_job_ids if action == "hybrid" else []),
            delay_job_count=(context.engine3_delayable_jobs if action == "hybrid" else 0),
            carbon_saving_gco2=context.engine2_carbon_saving_gco2 if can_optimize else 0.0,
            carbon_saving_percent=context.engine2_carbon_saving_percent if can_optimize else 0.0,
            sla_preserved=True,
            reason=reason,
            policy_applied="NORMAL_LOAD",
            input_load_level=context.engine1_load_level,
            input_predicted_cpu=context.engine1_predicted_cpu,
            input_current_pods=context.current_pods,
            had_engine3_data=context.has_engine3_data(),
            delayable_jobs_available=context.engine3_delayable_jobs,
        )
        
        return output
    
    def _apply_low_load_policy(self, context: DecisionContext) -> DecisionOutput:
        """
        Apply LOW LOAD policy.
        
        During LOW load, prioritize carbon optimization.
        
        RULE: Aggressively optimize pods and delay jobs
        - Pod reduction is encouraged
        - Job delay is MAXIMIZED for workload reduction
        - SLA is preserved but not the primary concern
        
        Action priority:
        1. Use HYBRID if optimization available (aggressive scaling + delay jobs)
        2. Scale DOWN if optimization available (no job delays)
        3. Scale DOWN if workload reduced anyway
        4. No action if already optimal
        """
        policy = self.config.LOW_LOAD_POLICY
        
        # Determine final pods - use optimized if available, otherwise raw
        if context.engine2_optimized_required_pods is not None:
            final_pods = context.engine2_optimized_required_pods
            can_optimize = True
        else:
            final_pods = context.engine2_raw_required_pods
            can_optimize = False
        
        # Ensure minimum pods
        final_pods = max(final_pods, self.config.MINIMUM_PODS)
        
        # Determine action - prioritize carbon optimization
        if can_optimize and final_pods < context.current_pods:
            if context.engine3_delayable_jobs > 0 and policy.allow_delayed_jobs:
                # HYBRID: Aggressive scaling + maximize job delays
                action = "hybrid"
                reason = (
                    f"{policy.reason_prefix}. Strong optimization available. "
                    f"Scaling down to {final_pods} pods + delaying {context.engine3_delayable_jobs} jobs. "
                    f"Carbon saving: {context.engine2_carbon_saving_gco2:.2f}g CO2."
                )
                jobs_to_delay = context.engine3_delayable_job_ids
                job_count = context.engine3_delayable_jobs
            else:
                # Scale down without job delays
                action = "scale_down"
                reason = (
                    f"{policy.reason_prefix}. Opportunity for optimization. "
                    f"Scaling down from {context.current_pods} to {final_pods} pods. "
                    f"Carbon saving: {context.engine2_carbon_saving_gco2:.2f}g CO2."
                )
                jobs_to_delay = []
                job_count = 0
        elif final_pods < context.current_pods:
            # Workload reduced anyway, scale down
            action = "scale_down"
            reason = (
                f"{policy.reason_prefix}. Workload reduced. "
                f"Scaling down from {context.current_pods} to {final_pods} pods."
            )
            jobs_to_delay = []
            job_count = 0
        else:
            # Already at optimal pod count
            action = "no_action"
            reason = f"{policy.reason_prefix}. Already at optimal pod count."
            jobs_to_delay = []
            job_count = 0
        
        # Build output
        output = DecisionOutput(
            timestamp=self._iso_timestamp(),
            decision_id=self._generate_decision_id("low"),
            final_action=action,
            raw_required_pods=context.engine2_raw_required_pods,
            optimized_required_pods=context.engine2_optimized_required_pods,
            final_required_pods=final_pods,
            jobs_to_delay=jobs_to_delay,
            delay_job_count=job_count,
            carbon_saving_gco2=context.engine2_carbon_saving_gco2 if can_optimize else 0.0,
            carbon_saving_percent=context.engine2_carbon_saving_percent if can_optimize else 0.0,
            sla_preserved=True,
            reason=reason,
            policy_applied="LOW_LOAD",
            input_load_level=context.engine1_load_level,
            input_predicted_cpu=context.engine1_predicted_cpu,
            input_current_pods=context.current_pods,
            had_engine3_data=context.has_engine3_data(),
            delayable_jobs_available=context.engine3_delayable_jobs,
        )
        
        return output
    
    def _iso_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def _generate_decision_id(self, load_prefix: str) -> str:
        """Generate a unique decision ID."""
        import time
        timestamp = int(time.time() * 1000)
        return f"decision_{load_prefix}_{timestamp}"
