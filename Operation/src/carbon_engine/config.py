"""
Configuration constants for Engine 2 - Carbon Emission Engine.
Green DevOps Operation Phase component.

Defines energy consumption models, carbon intensity factors, and optimization thresholds.
"""

# ============================================================================
# ENERGY CONSUMPTION MODEL
# ============================================================================

# Energy per pod per hour (kWh)
# Assumes typical cloud pod: CPU + memory + network
# Based on: ~0.5 kW per pod average
ENERGY_PER_POD_KWH_PER_HOUR = 0.5

# ============================================================================
# CARBON INTENSITY
# ============================================================================

# Carbon intensity of grid electricity (grams CO2 per kWh)
# Varies by region; using US average: ~400 g CO2/kWh
# Production grids: 200-900 g CO2/kWh depending on mix
CARBON_INTENSITY_GCO2_PER_KWH = 400.0

# ============================================================================
# POD SCALING CONSTRAINTS
# ============================================================================

# Minimum pods to maintain for baseline operation
MIN_REQUIRED_PODS = 1

# Maximum pods allowed even if predicted
MAX_PODS = 20

# ============================================================================
# WORKLOAD REDUCTION CONSTRAINTS
# ============================================================================

# Maximum percentage of workload that can be delayed (%)
# Example: 30% means up to 30% of jobs can be deferred
MAX_ALLOWED_REDUCTION_PERCENT = 30.0

# Minimum acceptable reduction percent (%)
# Don't recommend tiny reductions
MIN_MEANINGFUL_REDUCTION_PERCENT = 5.0

# ============================================================================
# CARBON OPTIMIZATION THRESHOLDS
# ============================================================================

# Carbon saving threshold to recommend delay strategy (%)
# Only recommend delaying if saves > X% carbon
CARBON_SAVING_THRESHOLD_PERCENT = 10.0

# Performance degradation acceptable for carbon savings (%)
# If scaling down causes performance degradation > X%, don't do it
MAX_ACCEPTABLE_PERFORMANCE_DEGRADATION_PERCENT = 15.0

# ============================================================================
# SCENARIO EVALUATION
# ============================================================================

# Decision modes
DECISION_SCALE_UP = "scale_up"
DECISION_DELAY_JOBS = "delay_jobs"
DECISION_HYBRID = "hybrid"
DECISION_NO_ACTION = "no_action"

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = "INFO"
ENABLE_DETAILED_LOGGING = True
