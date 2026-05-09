"""
Workload Estimator module for Engine 3.

Estimates workload reduction from delaying eligible jobs.
"""

import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

from job_prioritization_engine.config import (
    DEFAULT_JOB_CPU_ESTIMATE,
    WORKLOAD_REDUCTION_SAFETY_MARGIN,
    MAX_INITIAL_DELAY_PERCENT,
    MIN_MEANINGFUL_DELAY_REDUCTION,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkloadReductionEstimate:
    """Estimated workload reduction from delaying jobs."""
    delayable_jobs_count: int
    delayable_job_ids: List[str]
    total_delayable_cpu: float
    total_immediate_cpu: float
    workload_reduction_percent: float  # 0-1 float
    delayed_cpu_percent: float  # 0-100 percentage for display
    is_meaningful: bool
    reason: str


class WorkloadEstimator:
    """Estimates workload reduction from delayed jobs."""
    
    def __init__(self):
        """Initialize workload estimator."""
        logger.info("WorkloadEstimator initialized")
    
    def estimate_reduction(
        self,
        delayable_job_ids: List[str],
        jobs: List[Dict[str, Any]],
        backlog_adjustment_factor: float = 1.0
    ) -> WorkloadReductionEstimate:
        """
        Estimate workload reduction from delayable jobs.
        
        Args:
            delayable_job_ids: List of job IDs that are eligible for delay
            jobs: Full list of job metadata
            backlog_adjustment_factor: Adjustment factor based on backlog (0-1)
        
        Returns:
            WorkloadReductionEstimate with detailed metrics
        """
        # Build job lookup
        job_lookup = {job.get("job_id"): job for job in jobs}
        
        # Calculate CPU contributions
        total_immediate_cpu = 0.0
        total_delayable_cpu = 0.0
        
        for job in jobs:
            cpu = self._get_estimated_cpu(job)
            total_immediate_cpu += cpu
        
        for job_id in delayable_job_ids:
            if job_id in job_lookup:
                cpu = self._get_estimated_cpu(job_lookup[job_id])
                total_delayable_cpu += cpu
        
        # Calculate reduction percentage
        if total_immediate_cpu > 0:
            raw_reduction = total_delayable_cpu / total_immediate_cpu
        else:
            raw_reduction = 0.0
        
        # Apply safety margin and backlog adjustment
        adjusted_reduction = (
            raw_reduction 
            * WORKLOAD_REDUCTION_SAFETY_MARGIN 
            * backlog_adjustment_factor
        )
        
        # Clamp to valid range
        adjusted_reduction = max(0.0, min(adjusted_reduction, MAX_INITIAL_DELAY_PERCENT))
        
        # Check if reduction is meaningful
        is_meaningful = adjusted_reduction >= MIN_MEANINGFUL_DELAY_REDUCTION
        
        # Build reason string
        if not delayable_job_ids:
            reason = "No jobs eligible for delay"
        elif not is_meaningful:
            reason = (
                f"Estimated reduction {adjusted_reduction:.1%} < "
                f"minimum meaningful {MIN_MEANINGFUL_DELAY_REDUCTION:.1%}"
            )
        else:
            reason = (
                f"{len(delayable_job_ids)} jobs can be delayed; "
                f"estimated {adjusted_reduction:.1%} workload reduction"
            )
        
        return WorkloadReductionEstimate(
            delayable_jobs_count=len(delayable_job_ids),
            delayable_job_ids=delayable_job_ids,
            total_delayable_cpu=total_delayable_cpu,
            total_immediate_cpu=total_immediate_cpu,
            workload_reduction_percent=adjusted_reduction,
            delayed_cpu_percent=adjusted_reduction * 100.0,
            is_meaningful=is_meaningful,
            reason=reason
        )
    
    def _get_estimated_cpu(self, job: Dict[str, Any]) -> float:
        """
        Get estimated CPU contribution for a job.
        
        Uses provided estimate or falls back to default.
        
        Args:
            job: Job metadata dictionary
        
        Returns:
            Estimated CPU percentage
        """
        estimated = job.get("estimated_cpu_percent")
        if estimated is not None and estimated >= 0:
            return float(estimated)
        return DEFAULT_JOB_CPU_ESTIMATE
    
    def estimate_reduction_with_filter(
        self,
        jobs: List[Dict[str, Any]],
        delayable_checks: Dict[str, bool],
        backlog_adjustment_factor: float = 1.0
    ) -> WorkloadReductionEstimate:
        """
        Estimate reduction using delay eligibility check results.
        
        Args:
            jobs: List of job metadata
            delayable_checks: Dict mapping job_id -> is_delayable boolean
            backlog_adjustment_factor: Backlog adjustment (0-1)
        
        Returns:
            WorkloadReductionEstimate
        """
        delayable_ids = [
            job.get("job_id")
            for job in jobs
            if delayable_checks.get(job.get("job_id"), False)
        ]
        
        return self.estimate_reduction(
            delayable_ids,
            jobs,
            backlog_adjustment_factor
        )
