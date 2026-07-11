"""
Configuration constants for Engine 3 - Job Prioritization Engine.
Green DevOps Operation Phase component.

Defines job priority rules, delay eligibility constraints, and workload
reduction policies for safe job deferral.
"""

# ============================================================================
# JOB PRIORITY CLASSIFICATION RULES
# ============================================================================

# High Priority Job Types
# These jobs are typically critical and should not be delayed
HIGH_PRIORITY_TYPES = {
    "payment_processing",
    "authentication",
    "user_request",
    "urgent_transaction",
    "security_check",
    "critical_alert",
}

# Medium Priority Job Types
# Can be delayed in some conditions but generally should be prioritized
MEDIUM_PRIORITY_TYPES = {
    "cache_refresh",
    "indexing",
    "notification_dispatch",
    "session_cleanup",
    "database_maintenance",
    "config_update",
}

# Low Priority Job Types
# Safe candidates for delay during high load
LOW_PRIORITY_TYPES = {
    "report_generation",
    "analytics_batch",
    "log_compression",
    "backup_sync",
    "data_export",
    "cleanup_task",
    "batch_processing",
}

# ============================================================================
# DELAY ELIGIBILITY CONSTRAINTS
# ============================================================================

# Maximum allowed delay for a job (seconds)
# Jobs already delayed longer than this cannot be delayed further
MAX_ALREADY_DELAYED_SECONDS = 600  # 10 minutes

# Minimum time remaining on deadline (seconds)
# Jobs with deadline closer than this cannot be delayed
MIN_DEADLINE_BUFFER_SECONDS = 60  # 1 minute

# Maximum backlog size before restricting delays
# If backlog exceeds this, reduce delay recommendations
MAX_ACCEPTABLE_BACKLOG = 100

# Beyond this backlog, completely block delays
CRITICAL_BACKLOG_THRESHOLD = 200

# ============================================================================
# PRIORITY OVERRIDE RULES
# ============================================================================

# Jobs that are always HIGH priority regardless of metadata
ALWAYS_HIGH_PRIORITY_TYPES = {
    "payment_processing",
    "authentication",
    "security_check",
}

# Jobs that are always LOW priority unless explicitly marked HIGH
ALWAYS_LOW_PRIORITY_TYPES = {
    "report_generation",
    "analytics_batch",
    "log_compression",
    "data_export",
}

# ============================================================================
# DELAY POLICY SETTINGS
# ============================================================================

# Allow MEDIUM priority jobs to be delayed in LOW load conditions
ALLOW_MEDIUM_DELAY_IN_LOW_LOAD = True

# Maximum percentage of workload that can be initially considered for delay
# Engine 2 may apply additional SLA constraints that override this
MAX_INITIAL_DELAY_PERCENT = 0.50  # 50%

# Minimum estimated workload reduction to recommend delay
# Don't recommend delay unless it will reduce load by at least this much
MIN_MEANINGFUL_DELAY_REDUCTION = 0.05  # 5%

# ============================================================================
# WORKLOAD ESTIMATION DEFAULTS
# ============================================================================

# Default estimated CPU contribution for jobs without explicit values
# Used as fallback if estimated_cpu_percent is not provided
DEFAULT_JOB_CPU_ESTIMATE = 5.0  # 5% per job

# Safety margin for workload reduction calculations
# Actual reduction = calculated * safety_margin (to account for overhead)
WORKLOAD_REDUCTION_SAFETY_MARGIN = 0.95  # Apply 95% (5% safety margin)

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = "INFO"
ENABLE_DETAILED_LOGGING = False
