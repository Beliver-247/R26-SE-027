"""System constants and enumerations"""

# Job Priority Levels
JOB_PRIORITY_CRITICAL = "critical"
JOB_PRIORITY_IMPORTANT = "important"
JOB_PRIORITY_DELAYABLE = "delayable"
JOB_PRIORITY_BACKGROUND = "background"

JOB_PRIORITIES = [
    JOB_PRIORITY_CRITICAL,
    JOB_PRIORITY_IMPORTANT,
    JOB_PRIORITY_DELAYABLE,
    JOB_PRIORITY_BACKGROUND,
]

# Scaling Actions
SCALING_ACTION_SCALE_UP = "scale_up"
SCALING_ACTION_SCALE_DOWN = "scale_down"
SCALING_ACTION_NO_CHANGE = "no_change"

# SLA States
SLA_COMPLIANT = "compliant"
SLA_AT_RISK = "at_risk"
SLA_VIOLATED = "violated"

# Model Names
MODEL_WORKLOAD_PREDICTOR = "workload_predictor"
MODEL_CARBON_ESTIMATOR = "carbon_estimator"
MODEL_JOB_PRIORITIZER = "job_prioritizer"

# Metric Collection
DEFAULT_METRIC_COLLECTION_INTERVAL = 30  # seconds
DEFAULT_PREDICTION_WINDOW = 30  # seconds

# Confidence Thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.80
MIN_CONFIDENCE_THRESHOLD = 0.50
