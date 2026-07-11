"""
Main Engine 3 orchestrator - Job Prioritization Engine.

Integrates job classification, delay eligibility checking, and workload
estimation to determine which jobs can be safely delayed.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from job_prioritization_engine.job_classifier import JobClassifier, ClassifiedJob
from job_prioritization_engine.delay_eligibility import DelayEligibilityChecker, DelayEligibility
from job_prioritization_engine.workload_estimator import WorkloadEstimator, WorkloadReductionEstimate

logger = logging.getLogger(__name__)


class JobPrioritizationEngine:
    """
    Main Engine 3 orchestrator for job prioritization and delay analysis.
    
    Workflow:
    1. Accept job queue from system
    2. Classify each job by priority
    3. Check delay eligibility
    4. Estimate workload reduction
    5. Return structured decision support output
    """
    
    def __init__(self):
        """Initialize Engine 3 components."""
        self.classifier = JobClassifier()
        self.eligibility_checker = DelayEligibilityChecker()
        self.workload_estimator = WorkloadEstimator()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("JobPrioritizationEngine initialized")
    
    def evaluate(
        self,
        jobs: List[Dict[str, Any]],
        backlog_size: int = 0,
        current_load_level: str = "NORMAL",
        current_cpu: Optional[float] = None,
        current_pods: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform complete job prioritization analysis and return recommendation.
        
        Args:
            jobs: List of job metadata dictionaries, each with:
                - job_id: unique identifier
                - job_type: type/class of job
                - priority: optional explicit priority (HIGH/MEDIUM/LOW)
                - estimated_runtime_seconds: estimated duration
                - estimated_cpu_percent: estimated CPU contribution
                - deadline_seconds: time until deadline
                - already_delayed_seconds: cumulative delay already applied
            backlog_size: Optional current job backlog size
            current_load_level: Current system load (LOW/NORMAL/HIGH)
            current_cpu: Optional current CPU utilization (0-100)
            current_pods: Optional current pod count
        
        Returns:
            Structured Engine 3 output with:
            - delayable_jobs: count of jobs safe to delay
            - delayable_job_ids: list of job IDs
            - workload_reduction_percent: decimal 0-1 (NOT percentage)
            - delayed_cpu_percent: percentage 0-100 for display
            - reason: explanation
            - metadata: additional classification info
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Input validation
        if not isinstance(jobs, list):
            raise ValueError(f"jobs must be list, got {type(jobs)}")
        
        if not jobs:
            raise ValueError("jobs list cannot be empty")
        
        if backlog_size < 0:
            raise ValueError(f"backlog_size must be >= 0, got {backlog_size}")
        
        if current_load_level not in ("LOW", "NORMAL", "HIGH"):
            raise ValueError(
                f"current_load_level must be LOW/NORMAL/HIGH, got {current_load_level}"
            )
        
        if current_cpu is not None and not (0 <= current_cpu <= 100):
            raise ValueError(f"current_cpu must be 0-100, got {current_cpu}")
        
        if current_pods is not None and current_pods < 1:
            raise ValueError(f"current_pods must be >= 1, got {current_pods}")
        
        # Step 1: Classify all jobs
        classified_jobs = self.classifier.classify_jobs(jobs)
        classifications = {job.job_id: job for job in classified_jobs}
        
        # Build priority lookup for eligibility checking
        priority_map = {job.job_id: job.calculated_priority for job in classified_jobs}
        
        # Step 2: Get backlog adjustment factor
        backlog_adjustment = self.eligibility_checker.get_delayable_percentage_adjustment(
            backlog_size
        )
        
        # Step 3: Check delay eligibility
        eligibility_results = self.eligibility_checker.check_jobs(
            jobs=jobs,
            priorities=priority_map,
            backlog_size=backlog_size,
            current_load_level=current_load_level
        )
        delayable_checks = {
            job_id: result.is_delayable 
            for job_id, result in eligibility_results.items()
        }
        
        # Step 4: Estimate workload reduction
        workload_estimate = self.workload_estimator.estimate_reduction_with_filter(
            jobs=jobs,
            delayable_checks=delayable_checks,
            backlog_adjustment_factor=backlog_adjustment
        )
        
        # Step 5: Build output
        output = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "engine_version": "3.0",
            "input": {
                "total_jobs": len(jobs),
                "backlog_size": backlog_size,
                "current_load_level": current_load_level,
                "current_cpu": current_cpu,
                "current_pods": current_pods,
            },
            "classification_summary": self._build_classification_summary(classified_jobs),
            "delayable_jobs": workload_estimate.delayable_jobs_count,
            "delayable_job_ids": workload_estimate.delayable_job_ids,
            "workload_reduction_percent": workload_estimate.workload_reduction_percent,
            "delayed_cpu_percent": workload_estimate.delayed_cpu_percent,
            "is_meaningful": workload_estimate.is_meaningful,
            "reason": workload_estimate.reason,
            "metadata": {
                "backlog_adjustment_factor": backlog_adjustment,
                "total_immediate_cpu": workload_estimate.total_immediate_cpu,
                "total_delayable_cpu": workload_estimate.total_delayable_cpu,
                "eligibility_checks_failed": {
                    job_id: result.reason
                    for job_id, result in eligibility_results.items()
                    if not result.is_delayable
                },
            },
        }
        
        return output
    
    def _build_classification_summary(
        self,
        classified_jobs: List[ClassifiedJob]
    ) -> Dict[str, Any]:
        """Build classification summary statistics."""
        total = len(classified_jobs)
        high_count = sum(1 for j in classified_jobs if j.calculated_priority == "HIGH")
        medium_count = sum(1 for j in classified_jobs if j.calculated_priority == "MEDIUM")
        low_count = sum(1 for j in classified_jobs if j.calculated_priority == "LOW")
        
        return {
            "total_classified": total,
            "high_priority": high_count,
            "medium_priority": medium_count,
            "low_priority": low_count,
            "high_priority_percent": (high_count / total * 100) if total > 0 else 0,
            "medium_priority_percent": (medium_count / total * 100) if total > 0 else 0,
            "low_priority_percent": (low_count / total * 100) if total > 0 else 0,
        }
    
    def get_job_details(self, job_id: str, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get detailed information about a specific job for debugging.
        
        Args:
            job_id: Job identifier to look up
            jobs: List of all jobs
        
        Returns:
            Detailed job information or None if not found
        """
        for job in jobs:
            if job.get("job_id") == job_id:
                classification = self.classifier.classify(job)
                return {
                    "job_id": job_id,
                    "job_type": job.get("job_type"),
                    "classification": {
                        "explicit_priority": classification.explicit_priority,
                        "calculated_priority": classification.calculated_priority,
                        "reason": classification.priority_reason,
                    },
                    "metadata": {
                        "deadline_seconds": job.get("deadline_seconds"),
                        "already_delayed_seconds": job.get("already_delayed_seconds"),
                        "estimated_cpu_percent": job.get("estimated_cpu_percent"),
                    }
                }
        return None
