#!/usr/bin/env python3
"""
Quick reference: Carbon Endpoint API

Use this for quick lookups during development.
"""

# ============================================================================
# QUICK API REFERENCE
# ============================================================================

# Endpoint
ENDPOINT = "POST /carbon/evaluate"
BASE_URL = "http://localhost:8000"
FULL_URL = f"{BASE_URL}/carbon/evaluate"

# ============================================================================
# REQUEST TEMPLATES
# ============================================================================

# Minimal request (required fields only)
MINIMAL_REQUEST = {
    "system_id": "service-name",
    "predicted_cpu": 50.0,
    "predicted_load_level": "NORMAL",
    "recommended_pods": 3,
    "current_pods": 3
}

# Full request with all optional fields
FULL_REQUEST = {
    "system_id": "service-name",
    "predicted_cpu": 75.5,
    "predicted_load_level": "HIGH",
    "recommended_pods": 5,
    "current_pods": 3,
    "prediction_window_seconds": 30,
    "delayable_jobs": 10,
    "workload_reduction_percent": 20.0
}

# Scale-up scenario
SCALE_UP_REQUEST = {
    "system_id": "api-service",
    "predicted_cpu": 85.0,
    "predicted_load_level": "HIGH",
    "recommended_pods": 6,
    "current_pods": 2
}

# Scale-down scenario
SCALE_DOWN_REQUEST = {
    "system_id": "batch-service",
    "predicted_cpu": 20.0,
    "predicted_load_level": "LOW",
    "recommended_pods": 1,
    "current_pods": 4
}

# Job deferral scenario
JOB_DEFERRAL_REQUEST = {
    "system_id": "worker-service",
    "predicted_cpu": 65.0,
    "predicted_load_level": "NORMAL",
    "recommended_pods": 4,
    "current_pods": 4,
    "delayable_jobs": 25,
    "workload_reduction_percent": 30.0
}

# ============================================================================
# RESPONSE TEMPLATE
# ============================================================================

RESPONSE_TEMPLATE = {
    "status": "success",
    "timestamp": "2026-04-17T10:30:45Z",
    "system_id": "api-service",
    "engine_version": "2.0",
    "input": {
        "predicted_cpu": 75.5,
        "predicted_load_level": "HIGH",
        "recommended_pods": 5,
        "current_pods": 3,
        "prediction_window_seconds": 30,
        "has_job_data": False
    },
    "scenarios": [
        {
            "name": "raw_scale",
            "description": "Scale to Engine 1 recommendation",
            "pod_count": 5,
            "energy_kwh": 0.041667,
            "carbon_gco2": 16.67,
            "carbon_kg": 0.01667
        },
        {
            "name": "conservative",
            "description": "Conservative scaling with margin",
            "pod_count": 4,
            "energy_kwh": 0.033333,
            "carbon_gco2": 13.33,
            "carbon_kg": 0.01333
        }
    ],
    "decision": {
        "recommended_action": "scale_up",
        "carbon_saving_percent": 15.0,
        "carbon_saving_gco2": 50.0,
        "reasoning": "HIGH load requires scaling, conservative approach saves 15% carbon"
    },
    "metadata": {
        "energy_model": {
            "energy_per_pod_kwh_per_hour": 0.5,
            "model_type": "linear_scaling",
            "assumptions": ["Linear scaling", "Time-proportional consumption"]
        },
        "carbon_calculator": {
            "carbon_intensity_gco2_per_kwh": 400.0,
            "carbon_intensity_description": "Moderate grid (mixed sources)"
        }
    },
    "evaluation_ms": 12.45
}

# ============================================================================
# DECISION ACTIONS
# ============================================================================

ACTIONS = {
    "scale_up": "Increase pod count (performance required)",
    "scale_down": "Reduce pod count (low load)",
    "delay_jobs": "Defer non-critical jobs (high carbon savings)",
    "hybrid": "Scale down + defer jobs (optimal carbon reduction)",
    "no_action": "Keep current pods (already optimal)"
}

# ============================================================================
# FIELD VALIDATION
# ============================================================================

FIELD_CONSTRAINTS = {
    "predicted_cpu": {"type": float, "min": 0.0, "max": 100.0},
    "predicted_load_level": {"type": str, "values": ["LOW", "NORMAL", "HIGH"]},
    "recommended_pods": {"type": int, "min": 1, "max": 20},
    "current_pods": {"type": int, "min": 1, "max": 20},
    "prediction_window_seconds": {"type": int, "min": 1},
    "delayable_jobs": {"type": int, "min": 0, "optional": True},
    "workload_reduction_percent": {"type": float, "min": 0.0, "max": 100.0, "optional": True}
}

# ============================================================================
# PYTHON EXAMPLES
# ============================================================================

PYTHON_EXAMPLE_1 = """
import requests

response = requests.post(
    "http://localhost:8000/carbon/evaluate",
    json={
        "system_id": "api-service",
        "predicted_cpu": 75.5,
        "predicted_load_level": "HIGH",
        "recommended_pods": 5,
        "current_pods": 3
    }
)

result = response.json()
action = result["decision"]["recommended_action"]
saving = result["decision"]["carbon_saving_percent"]

print(f"Action: {action}, Carbon Saving: {saving:.1f}%")
"""

PYTHON_EXAMPLE_2 = """
# Integration with Engine 1 prediction
import requests

e1_response = requests.get("http://localhost:8000/predict")
e1_result = e1_response.json()["prediction"]

e2_response = requests.post(
    "http://localhost:8000/carbon/evaluate",
    json={
        "system_id": e1_result["system_id"],
        "predicted_cpu": e1_result["predicted_cpu_percent"],
        "predicted_load_level": e1_result["predicted_load_level"],
        "recommended_pods": e1_result["recommended_pods"],
        "current_pods": 3
    }
)

decision = e2_response.json()["decision"]
print(f"Recommendation: {decision['recommended_action']}")
"""

# ============================================================================
# CURL EXAMPLES
# ============================================================================

CURL_EXAMPLE_1 = """
curl -X POST http://localhost:8000/carbon/evaluate \\
  -H "Content-Type: application/json" \\
  -d '{
    "system_id": "api-service",
    "predicted_cpu": 75.5,
    "predicted_load_level": "HIGH",
    "recommended_pods": 5,
    "current_pods": 3
  }' | jq .
"""

CURL_EXAMPLE_2 = """
# Pretty print response
curl -s -X POST http://localhost:8000/carbon/evaluate \\
  -H "Content-Type: application/json" \\
  -d @request.json | jq '.decision'
"""

# ============================================================================
# ERROR HANDLING
# ============================================================================

ERROR_EXAMPLES = {
    "invalid_cpu": {
        "request": {"predicted_cpu": 150.0, "...": "other_fields"},
        "error": "Invalid input: predicted_cpu must be 0-100, got 150.0",
        "status": 400
    },
    "invalid_load_level": {
        "request": {"predicted_load_level": "EXTREME", "...": "other_fields"},
        "error": "Invalid input: predicted_load_level must be LOW/NORMAL/HIGH",
        "status": 400
    },
    "invalid_pods": {
        "request": {"recommended_pods": 0, "current_pods": 25, "...": "other_fields"},
        "error": "Invalid input: recommended_pods must be 1-20, got 0",
        "status": 400
    },
    "engine_not_ready": {
        "error": "Carbon Emission Engine not available",
        "status": 503
    }
}

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

CONFIG = {
    "ENERGY_PER_POD_KWH_PER_HOUR": 0.5,
    "CARBON_INTENSITY_GCO2_PER_KWH": 400.0,
    "MIN_REQUIRED_PODS": 1,
    "MAX_PODS": 20,
    "MAX_ALLOWED_REDUCTION_PERCENT": 30.0,
    "CARBON_SAVING_THRESHOLD_PERCENT": 10.0,
    "MAX_ACCEPTABLE_PERFORMANCE_DEGRADATION_PERCENT": 15.0
}

# ============================================================================
# TYPICAL RESPONSE TIMES
# ============================================================================

PERFORMANCE = {
    "typical_evaluation_ms": "5-15",
    "max_evaluation_ms": "50",
    "throughput": "100s-1000s per second",
    "memory_per_eval": "minimal (< 1MB)"
}

# ============================================================================
# TESTING CHECKLIST
# ============================================================================

TESTING_CHECKLIST = """
Quick Testing Checklist:

[ ] API Server Running
    python scripts/run_live_api.py --system-id test-pod --port 8000

[ ] Test Basic Request
    POST /carbon/evaluate with minimal required fields

[ ] Test All Optional Fields
    POST /carbon/evaluate with delayable_jobs and workload_reduction_percent

[ ] Test Boundary Values
    - predicted_cpu: 0, 50, 100
    - recommended_pods: 1, 10, 20
    - workload_reduction_percent: 0, 50, 100

[ ] Test Error Cases
    - predicted_cpu > 100 (should fail)
    - invalid predicted_load_level (should fail)
    - recommended_pods > 20 (should fail)

[ ] Test Response Structure
    - status field is "success"
    - scenarios array has multiple items
    - decision has recommended_action and carbon_saving_percent

[ ] Measure Performance
    - evaluation_ms is reasonable (< 50ms)
    - Handle concurrent requests

[ ] Integration Test
    - Run with Engine 1 prediction output
    - Apply decision recommendation
"""

# ============================================================================
# COMMON PATTERNS
# ============================================================================

PATTERN_1_CONTINUOUS_MONITORING = """
Pattern: Continuous Carbon-Aware Monitoring

for each timestep:
  1. metrics = collect_system_metrics(system_id)
  2. prediction = get_engine1_prediction(system_id)
  3. carbon_eval = post_to_carbon_evaluate(prediction, metrics)
  4. decision = carbon_eval.decision.recommended_action
  5. apply_scaling_decision(system_id, decision)
  6. wait(30_seconds)
"""

PATTERN_2_BATCH_JOB_OPTIMIZATION = """
Pattern: Batch Job Optimization with Deferral

for each batch_job:
  1. job_analysis = analyze_job_criticality()
  2. if job_deferrable:
       carbon_eval = post_to_carbon_evaluate({
         ...,
         delayable_jobs: count,
         workload_reduction_percent: estimate
       })
       if carbon_eval.decision.carbon_saving_percent > 20:
         defer_job(batch_job)
       else:
         run_job_now()
"""

PATTERN_3_DASHBOARD_INTEGRATION = """
Pattern: Dashboard Display Integration

on_dashboard_load():
  carbon_eval = post_to_carbon_evaluate(current_prediction)
  
  display_scenarios_chart(carbon_eval.scenarios)
  display_recommendation(carbon_eval.decision)
  display_carbon_metrics(carbon_eval.decision.carbon_saving_gco2)
  show_timeline(carbon_eval.metadata)
"""

# ============================================================================
# CHEAT SHEET
# ============================================================================

CHEAT_SHEET = """
╔══════════════════════════════════════════════════════════════════════════╗
║                   CARBON ENDPOINT CHEAT SHEET                            ║
╚══════════════════════════════════════════════════════════════════════════╝

URL: POST http://localhost:8000/carbon/evaluate

REQUIRED FIELDS:
  system_id             : str
  predicted_cpu         : float (0-100)
  predicted_load_level  : str (LOW|NORMAL|HIGH)
  recommended_pods      : int (1-20)
  current_pods          : int (1-20)

OPTIONAL FIELDS:
  prediction_window_seconds     : int (default: 30)
  delayable_jobs                : int
  workload_reduction_percent    : float (0-100)

RESPONSE CONTAINS:
  status                : "success" / error
  timestamp             : ISO 8601
  scenarios             : array of {name, pods, energy_kwh, carbon_gco2}
  decision              : {recommended_action, carbon_saving_percent}
  evaluation_ms         : float

DECISION ACTIONS:
  scale_up      → increase pods (performance priority)
  scale_down    → decrease pods (low load)
  delay_jobs    → defer work (high carbon savings)
  hybrid        → scale + defer (optimal carbon)
  no_action     → keep current

ERROR CODES:
  200           : Success
  400           : Validation error (invalid inputs)
  500           : Internal error (engine failure)
  503           : Service unavailable (engine not initialized)

QUICK TEST:
  curl -X POST http://localhost:8000/carbon/evaluate \\
    -H "Content-Type: application/json" \\
    -d '{"system_id":"test","predicted_cpu":75,"predicted_load_level":"HIGH",
         "recommended_pods":5,"current_pods":3}'

═══════════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(CHEAT_SHEET)
    print("\nFor full details, see CARBON_EVALUATION_GUIDE.md")
    print("For integration examples, see integration_example.py")
    print("For testing, run: python test_carbon_endpoint.py")
