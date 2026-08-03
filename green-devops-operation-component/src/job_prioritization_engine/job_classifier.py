"""
Job Classifier module for Engine 3.

Classifies jobs into HIGH/MEDIUM/LOW priority based on job metadata
and configured rules.
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

try:
    from .config import (
        HIGH_PRIORITY_TYPES,
        MEDIUM_PRIORITY_TYPES,
        LOW_PRIORITY_TYPES,
        ALWAYS_HIGH_PRIORITY_TYPES,
        ALWAYS_LOW_PRIORITY_TYPES,
    )
except ImportError:
    from job_prioritization_engine.config import (
        HIGH_PRIORITY_TYPES,
        MEDIUM_PRIORITY_TYPES,
        LOW_PRIORITY_TYPES,
        ALWAYS_HIGH_PRIORITY_TYPES,
        ALWAYS_LOW_PRIORITY_TYPES,
    )

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedJob:
    """Result of job classification."""
    job_id: str
    job_type: str
    explicit_priority: str  # From metadata
    calculated_priority: str  # Based on type and rules
    priority_reason: str
    estimated_cpu_percent: float


class JobClassifier:
    """Classifies jobs into priority levels."""
    
    def __init__(self):
        """Initialize job classifier."""
        logger.info("JobClassifier initialized")
    
    def classify(self, job: Dict[str, Any]) -> ClassifiedJob:
        """
        Classify a single job into HIGH/MEDIUM/LOW priority.
        
        Args:
            job: Job metadata dictionary with keys:
                - job_id: unique identifier
                - job_type: type of job (string)
                - priority: optional explicit priority (HIGH/MEDIUM/LOW)
                - estimated_cpu_percent: optional CPU contribution
        
        Returns:
            ClassifiedJob with priority classification and reason
        """
        job_id = job.get("job_id", "unknown")
        job_type = job.get("job_type", "unknown").lower()
        explicit_priority = job.get("priority", "").upper()
        estimated_cpu = job.get("estimated_cpu_percent", 0.0)
        
        # Step 1: Check for absolute overrides
        if job_type in ALWAYS_HIGH_PRIORITY_TYPES:
            return ClassifiedJob(
                job_id=job_id,
                job_type=job_type,
                explicit_priority=explicit_priority,
                calculated_priority="HIGH",
                priority_reason=f"Job type '{job_type}' is always HIGH priority",
                estimated_cpu_percent=estimated_cpu
            )
        
        if job_type in ALWAYS_LOW_PRIORITY_TYPES:
            return ClassifiedJob(
                job_id=job_id,
                job_type=job_type,
                explicit_priority=explicit_priority,
                calculated_priority="LOW",
                priority_reason=f"Job type '{job_type}' is typically LOW priority",
                estimated_cpu_percent=estimated_cpu
            )
        
        # Step 2: Use explicit priority if provided
        if explicit_priority in ("HIGH", "MEDIUM", "LOW"):
            return ClassifiedJob(
                job_id=job_id,
                job_type=job_type,
                explicit_priority=explicit_priority,
                calculated_priority=explicit_priority,
                priority_reason=f"Explicit priority from metadata: {explicit_priority}",
                estimated_cpu_percent=estimated_cpu
            )
        
        # Step 3: Classify by job type
        if job_type in HIGH_PRIORITY_TYPES:
            priority = "HIGH"
            reason = f"Job type '{job_type}' classified as HIGH priority"
        elif job_type in MEDIUM_PRIORITY_TYPES:
            priority = "MEDIUM"
            reason = f"Job type '{job_type}' classified as MEDIUM priority"
        elif job_type in LOW_PRIORITY_TYPES:
            priority = "LOW"
            reason = f"Job type '{job_type}' classified as LOW priority"
        else:
            # Default: unknown types become MEDIUM
            priority = "MEDIUM"
            reason = f"Unknown job type '{job_type}'; defaulted to MEDIUM"
        
        return ClassifiedJob(
            job_id=job_id,
            job_type=job_type,
            explicit_priority=explicit_priority,
            calculated_priority=priority,
            priority_reason=reason,
            estimated_cpu_percent=estimated_cpu
        )
    
    def classify_jobs(self, jobs: List[Dict[str, Any]]) -> List[ClassifiedJob]:
        """
        Classify a list of jobs.
        
        Args:
            jobs: List of job metadata dictionaries
        
        Returns:
            List of ClassifiedJob results
        """
        classified = []
        for job in jobs:
            try:
                classified.append(self.classify(job))
            except Exception as e:
                logger.warning(f"Error classifying job {job.get('job_id', 'unknown')}: {e}")
                # Create a neutral classification on error
                classified.append(ClassifiedJob(
                    job_id=job.get("job_id", "unknown"),
                    job_type=job.get("job_type", "unknown"),
                    explicit_priority="",
                    calculated_priority="MEDIUM",
                    priority_reason=f"Classification error: {str(e)}",
                    estimated_cpu_percent=job.get("estimated_cpu_percent", 0.0)
                ))
        
        return classified
    
    def get_priority_level(self, priority: str) -> int:
        """
        Get numeric priority level for sorting (higher = more important).
        
        Args:
            priority: Priority string (HIGH/MEDIUM/LOW)
        
        Returns:
            Numeric priority level (3=HIGH, 2=MEDIUM, 1=LOW)
        """
        priority_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return priority_map.get(priority.upper(), 1)
