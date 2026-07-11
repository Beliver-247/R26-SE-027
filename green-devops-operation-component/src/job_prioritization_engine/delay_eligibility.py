"""
Delay Eligibility module for Engine 3.

Determines whether each job is safe to delay based on deadline,
already delayed time, backlog, and other constraints.
"""

import logging
from typing import Dict, Any, Tuple
from dataclasses import dataclass

from job_prioritization_engine.config import (
    MAX_ALREADY_DELAYED_SECONDS,
    MIN_DEADLINE_BUFFER_SECONDS,
    MAX_ACCEPTABLE_BACKLOG,
    CRITICAL_BACKLOG_THRESHOLD,
    ALLOW_MEDIUM_DELAY_IN_LOW_LOAD,
)

logger = logging.getLogger(__name__)


@dataclass
class DelayEligibility:
    """Result of delay eligibility check."""
    job_id: str
    is_delayable: bool
    reason: str
    check_results: Dict[str, bool]  # Individual check results


class DelayEligibilityChecker:
    """Checks whether jobs are safe to delay."""
    
    def __init__(self):
        """Initialize delay eligibility checker."""
        logger.info("DelayEligibilityChecker initialized")
    
    def check_single_job(
        self,
        job: Dict[str, Any],
        priority: str,
        backlog_size: int = 0,
        current_load_level: str = "NORMAL"
    ) -> DelayEligibility:
        """
        Check if a single job is safe to delay.
        
        Args:
            job: Job metadata with keys like deadline_seconds, already_delayed_seconds
            priority: Priority classification (HIGH/MEDIUM/LOW)
            backlog_size: Current job backlog size
            current_load_level: Current system load level (LOW/NORMAL/HIGH)
        
        Returns:
            DelayEligibility result with yes/no and reason
        """
        job_id = job.get("job_id", "unknown")
        check_results = {}
        
        # Check 1: Priority must be LOW (or MEDIUM in low load with policy)
        if priority == "HIGH":
            check_results["priority_allows_delay"] = False
            reason = "HIGH priority jobs cannot be delayed"
            return self._make_ineligible(job_id, reason, check_results)
        
        if priority == "MEDIUM":
            if ALLOW_MEDIUM_DELAY_IN_LOW_LOAD and current_load_level == "LOW":
                check_results["priority_allows_delay"] = True
            else:
                check_results["priority_allows_delay"] = False
                reason = (
                    "MEDIUM priority jobs only delayable in LOW load; "
                    f"current load: {current_load_level}"
                )
                return self._make_ineligible(job_id, reason, check_results)
        else:
            check_results["priority_allows_delay"] = True
        
        # Check 2: Deadline not too close
        deadline_seconds = job.get("deadline_seconds", float("inf"))
        if deadline_seconds < MIN_DEADLINE_BUFFER_SECONDS:
            check_results["deadline_allows_delay"] = False
            reason = (
                f"Deadline too close: {deadline_seconds}s < "
                f"minimum buffer {MIN_DEADLINE_BUFFER_SECONDS}s"
            )
            return self._make_ineligible(job_id, reason, check_results)
        check_results["deadline_allows_delay"] = True
        
        # Check 3: Not already delayed too long
        already_delayed = job.get("already_delayed_seconds", 0)
        if already_delayed >= MAX_ALREADY_DELAYED_SECONDS:
            check_results["delay_history_allows_delay"] = False
            reason = (
                f"Job already delayed {already_delayed}s >= "
                f"max {MAX_ALREADY_DELAYED_SECONDS}s"
            )
            return self._make_ineligible(job_id, reason, check_results)
        check_results["delay_history_allows_delay"] = True
        
        # Check 4: Backlog not too high
        if backlog_size >= CRITICAL_BACKLOG_THRESHOLD:
            check_results["backlog_allows_delay"] = False
            reason = (
                f"Backlog critical: {backlog_size} >= "
                f"critical threshold {CRITICAL_BACKLOG_THRESHOLD}"
            )
            return self._make_ineligible(job_id, reason, check_results)
        
        check_results["backlog_allows_delay"] = True
        
        # All checks passed
        return DelayEligibility(
            job_id=job_id,
            is_delayable=True,
            reason="Job meets all delay eligibility criteria",
            check_results=check_results
        )
    
    def check_jobs(
        self,
        jobs: list,
        priorities: Dict[str, str],
        backlog_size: int = 0,
        current_load_level: str = "NORMAL"
    ) -> Dict[str, DelayEligibility]:
        """
        Check delay eligibility for multiple jobs.
        
        Args:
            jobs: List of job metadata dictionaries
            priorities: Dict mapping job_id -> priority classification
            backlog_size: Current job backlog size
            current_load_level: Current system load level
        
        Returns:
            Dict mapping job_id -> DelayEligibility result
        """
        results = {}
        for job in jobs:
            job_id = job.get("job_id", "unknown")
            priority = priorities.get(job_id, "MEDIUM")
            results[job_id] = self.check_single_job(
                job=job,
                priority=priority,
                backlog_size=backlog_size,
                current_load_level=current_load_level
            )
        return results
    
    def _make_ineligible(
        self,
        job_id: str,
        reason: str,
        check_results: Dict[str, bool]
    ) -> DelayEligibility:
        """Create an ineligible DelayEligibility result."""
        return DelayEligibility(
            job_id=job_id,
            is_delayable=False,
            reason=reason,
            check_results=check_results
        )
    
    def get_delayable_percentage_adjustment(self, backlog_size: int) -> float:
        """
        Get workload reduction adjustment factor based on backlog.
        
        Args:
            backlog_size: Current job backlog size
        
        Returns:
            Adjustment factor 0.0-1.0 (1.0 = no adjustment, 0.0 = block all delays)
        """
        if backlog_size >= CRITICAL_BACKLOG_THRESHOLD:
            return 0.0  # Block all delays
        
        if backlog_size >= MAX_ACCEPTABLE_BACKLOG:
            # Reduce delays linearly from MAX to CRITICAL
            ratio = (backlog_size - MAX_ACCEPTABLE_BACKLOG) / (
                CRITICAL_BACKLOG_THRESHOLD - MAX_ACCEPTABLE_BACKLOG
            )
            return 1.0 - ratio  # 1.0 at MAX, 0.0 at CRITICAL
        
        return 1.0  # No adjustment
