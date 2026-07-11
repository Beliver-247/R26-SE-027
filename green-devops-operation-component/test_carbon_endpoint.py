"""
Test script for the /carbon/evaluate endpoint.

This script demonstrates how to use the carbon evaluation endpoint
with the Engine 1 Workload Prediction API.
"""

import requests
import json
from typing import Dict, Any

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

# API endpoint
API_BASE_URL = "http://localhost:8000"
CARBON_ENDPOINT = f"{API_BASE_URL}/carbon/evaluate"

# ============================================================================
# TEST CASES
# ============================================================================

def test_basic_carbon_evaluation() -> Dict[str, Any]:
    """
    Test basic carbon evaluation with minimal required fields.
    
    This tests a scenario where:
    - CPU is high (75.5%)
    - Recommended pods: 5
    - Current pods: 3 (need to scale up)
    """
    payload = {
        "system_id": "api-service",
        "predicted_cpu": 75.5,
        "predicted_load_level": "HIGH",
        "recommended_pods": 5,
        "current_pods": 3,
        "prediction_window_seconds": 30
    }
    
    print("=" * 80)
    print("TEST 1: Basic Carbon Evaluation")
    print("=" * 80)
    print(f"Request to: POST {CARBON_ENDPOINT}")
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(CARBON_ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
        return response.json()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Is the server running?")
        return None


def test_carbon_with_job_deferral() -> Dict[str, Any]:
    """
    Test carbon evaluation with job deferral option.
    
    This tests a scenario where:
    - CPU is moderate (65%)
    - Load level: NORMAL
    - Job deferral can reduce workload by 20%
    """
    payload = {
        "system_id": "worker-service",
        "predicted_cpu": 65.0,
        "predicted_load_level": "NORMAL",
        "recommended_pods": 4,
        "current_pods": 4,
        "prediction_window_seconds": 30,
        "delayable_jobs": 12,
        "workload_reduction_percent": 20.0
    }
    
    print("=" * 80)
    print("TEST 2: Carbon Evaluation with Job Deferral")
    print("=" * 80)
    print(f"Request to: POST {CARBON_ENDPOINT}")
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(CARBON_ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
        return response.json()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Is the server running?")
        return None


def test_carbon_low_load() -> Dict[str, Any]:
    """
    Test carbon evaluation during low load.
    
    This tests a scenario where:
    - CPU is low (25%)
    - Load level: LOW
    - Few pods needed
    """
    payload = {
        "system_id": "batch-service",
        "predicted_cpu": 25.0,
        "predicted_load_level": "LOW",
        "recommended_pods": 2,
        "current_pods": 4,
        "prediction_window_seconds": 30
    }
    
    print("=" * 80)
    print("TEST 3: Carbon Evaluation During Low Load")
    print("=" * 80)
    print(f"Request to: POST {CARBON_ENDPOINT}")
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(CARBON_ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
        return response.json()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Is the server running?")
        return None


def test_invalid_input() -> None:
    """Test error handling with invalid input."""
    payload = {
        "system_id": "invalid-service",
        "predicted_cpu": 150.0,  # Invalid: > 100%
        "predicted_load_level": "INVALID",  # Invalid load level
        "recommended_pods": 0,  # Invalid: < 1
        "current_pods": 1,
        "prediction_window_seconds": 30
    }
    
    print("=" * 80)
    print("TEST 4: Error Handling - Invalid Input")
    print("=" * 80)
    print(f"Request to: POST {CARBON_ENDPOINT}")
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(CARBON_ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Is the server running?")


def print_usage_guide() -> None:
    """Print usage guide for the carbon evaluation endpoint."""
    guide = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    CARBON EVALUATION ENDPOINT GUIDE                        ║
╚════════════════════════════════════════════════════════════════════════════╝

ENDPOINT: POST /carbon/evaluate

DESCRIPTION:
  Evaluates carbon emissions for a workload prediction and recommends
  optimization strategies to minimize environmental impact.

REQUEST BODY (JSON):
  {
    "system_id": "str",
      → System identifier
    "predicted_cpu": float,
      → Predicted CPU percentage (0-100), from Engine 1
    "predicted_load_level": str,
      → Load level: "LOW", "NORMAL", or "HIGH"
    "recommended_pods": int,
      → Recommended pod count (1-20), from Engine 1
    "current_pods": int,
      → Current running pod count (1-20)
    "prediction_window_seconds": int,
      → Prediction window in seconds (default: 30)
    "delayable_jobs": int (optional),
      → Number of jobs that can be deferred for carbon reduction
    "workload_reduction_percent": float (optional),
      → Maximum workload reduction percentage (0-100)
  }

RESPONSE (JSON):
  {
    "status": "success",
    "timestamp": "ISO 8601",
    "system_id": "str",
    "engine_version": "2.0",
    "input": {
      ...echo of input parameters...
    },
    "scenarios": [
      {
        "name": "scenario_name",
        "description": "...",
        "pod_count": int,
        "energy_kwh": float,
        "carbon_gco2": float
      },
      ...
    ],
    "decision": {
      "recommended_action": "scale_up|scale_down|delay_jobs|hybrid|no_action",
      "carbon_saving_percent": float,
      "carbon_saving_gco2": float,
      "reasoning": "..."
    },
    "metadata": {
      "energy_model": {...},
      "carbon_calculator": {...}
    },
    "evaluation_ms": float
  }

EXAMPLE USAGE:

  curl -X POST http://localhost:8000/carbon/evaluate \\
    -H "Content-Type: application/json" \\
    -d '{
      "system_id": "api-service",
      "predicted_cpu": 75.5,
      "predicted_load_level": "HIGH",
      "recommended_pods": 5,
      "current_pods": 3,
      "prediction_window_seconds": 30,
      "delayable_jobs": 10,
      "workload_reduction_percent": 15.0
    }'

KEY FEATURES:

  1. Multi-Scenario Analysis
     - Evaluates multiple scaling strategies
     - Compares energy and carbon footprints
  
  2. Job Deferral Support
     - Optional job deferral for carbon reduction
     - Balances performance vs environmental impact
  
  3. Error Handling
     - Validates all input parameters
     - Returns descriptive error messages
  
  4. Performance Measurement
     - Returns evaluation time in milliseconds
     - Useful for monitoring API performance

═══════════════════════════════════════════════════════════════════════════════
"""
    print(guide)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n")
    print_usage_guide()
    
    print("\n")
    print("Running Test Cases...")
    print("(Make sure the API server is running on http://localhost:8000)")
    print("\n")
    
    # Run test cases
    test_basic_carbon_evaluation()
    test_carbon_with_job_deferral()
    test_carbon_low_load()
    test_invalid_input()
    
    print("\n")
    print("=" * 80)
    print("Test suite completed!")
    print("=" * 80)
