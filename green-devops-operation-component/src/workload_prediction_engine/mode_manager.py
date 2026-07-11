"""
Mode manager for Engine 1 runtime lifecycle.

Manages transitions between cold-start and runtime modes.
- Cold-start: Not enough real runtime data yet, use pretrained model
- Runtime: Have >= 12 real timesteps (6 minutes), use runtime data for prediction
- Retraining: Have enough data (e.g., 1 day), ready to fine-tune model
"""

import logging
from typing import Literal
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ModeManager:
    """
    Determine whether Engine 1 should use cold-start or runtime mode.
    
    Rules:
    - Cold-start: runtime_record_count < 12
    - Runtime: runtime_record_count >= 12
    - Retraining-ready: enough time has passed or record count high
    """
    
    COLD_START = "cold_start"
    RUNTIME = "runtime"
    
    def __init__(
        self,
        retraining_threshold_records: int = 2880,  # 1 day of 30-sec data
        retraining_cooldown_hours: int = 24
    ):
        """
        Initialize mode manager.
        
        Args:
            retraining_threshold_records: Records before retraining is suggested
                Default: 2880 = 24 hours * 3600 sec / 30 sec per record
            retraining_cooldown_hours: Minimum hours between retrain suggestions
        """
        self.retraining_threshold_records = retraining_threshold_records
        self.retraining_cooldown_hours = retraining_cooldown_hours
        self.last_retraining_suggestion = None
        self.logger = logging.getLogger(__name__)
    
    def get_mode(self, runtime_record_count: int) -> Literal["cold_start", "runtime"]:
        """
        Determine current mode based on available runtime records.
        
        Args:
            runtime_record_count: Number of runtime records in store
        
        Returns:
            "cold_start" or "runtime"
        """
        if runtime_record_count < 12:
            return self.COLD_START
        else:
            return self.RUNTIME
    
    def should_retrain(self, runtime_record_count: int) -> bool:
        """
        Check if enough data exists for retraining.
        
        Args:
            runtime_record_count: Number of runtime records in store
        
        Returns:
            True if retraining is recommended
        """
        # Check record threshold
        if runtime_record_count < self.retraining_threshold_records:
            return False
        
        # Check cooldown (don't suggest too frequently)
        if self.last_retraining_suggestion:
            time_since = datetime.utcnow() - self.last_retraining_suggestion
            if time_since < timedelta(hours=self.retraining_cooldown_hours):
                return False
        
        # Mark suggestion logged
        self.last_retraining_suggestion = datetime.utcnow()
        
        self.logger.info(
            f"Retraining recommended: {runtime_record_count} records "
            f"(threshold: {self.retraining_threshold_records})"
        )
        
        return True
    
    def get_mode_info(self, runtime_record_count: int, mode: str) -> dict:
        """
        Get detailed information about current mode.
        
        Returns:
            Dict with mode details
        """
        return {
            'current_mode': mode,
            'record_count': runtime_record_count,
            'records_for_runtime': 12,
            'mode_description': (
                'Using pretrained model, collecting real runtime data'
                if mode == self.COLD_START
                else 'Using real runtime data from last 6 minutes'
            ),
            'retrain_ready': self.should_retrain(runtime_record_count),
            'timesteps_for_full_window': 12,
            'seconds_for_full_window': 360  # 12 * 30 sec
        }
    
    def log_mode_transition(
        self,
        old_mode: str,
        new_mode: str,
        runtime_record_count: int
    ):
        """Log mode transition event."""
        if old_mode != new_mode:
            self.logger.warning(
                f"Mode transition: {old_mode} -> {new_mode} "
                f"(records: {runtime_record_count})"
            )


class ModeHistory:
    """
    Track mode transitions over time for debugging and analytics.
    """
    
    def __init__(self):
        """Initialize mode history tracker."""
        self.transitions = []
        self.logger = logging.getLogger(__name__)
    
    def record_transition(
        self,
        from_mode: str,
        to_mode: str,
        record_count: int,
        timestamp: datetime = None
    ):
        """
        Record a mode transition.
        
        Args:
            from_mode: Previous mode
            to_mode: New mode
            record_count: Runtime records at transition
            timestamp: When transition occurred
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        event = {
            'timestamp': timestamp,
            'from_mode': from_mode,
            'to_mode': to_mode,
            'record_count': record_count
        }
        
        self.transitions.append(event)
        
        if from_mode != to_mode:
            self.logger.info(
                f"[Mode History] {from_mode} -> {to_mode} at {timestamp} "
                f"({record_count} records)"
            )
    
    def get_transitions(self) -> list:
        """Get all recorded transitions."""
        return self.transitions
    
    def get_last_transition(self) -> dict:
        """Get most recent transition."""
        if self.transitions:
            return self.transitions[-1]
        return None
    
    def get_duration_in_mode(self, mode: str) -> float:
        """
        Get how long (in seconds) spent in given mode.
        
        Args:
            mode: Mode to check
        
        Returns:
            Duration in seconds (0 if not in mode or not transitioned)
        """
        in_mode_start = None
        total_duration = 0.0
        
        for event in self.transitions:
            if event['to_mode'] == mode and in_mode_start is None:
                in_mode_start = event['timestamp']
            elif event['to_mode'] != mode and in_mode_start is not None:
                duration = (event['timestamp'] - in_mode_start).total_seconds()
                total_duration += duration
                in_mode_start = None
        
        # If still in mode, add time until now
        if in_mode_start is not None:
            duration = (datetime.utcnow() - in_mode_start).total_seconds()
            total_duration += duration
        
        return total_duration
