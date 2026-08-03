#!/usr/bin/env python3
"""
Engine 2 Validation Suite - Complete QA Testing

Validates:
1. Engine 2 endpoint correctness
2. Engine 1 → Engine 2 integration
3. Carbon calculation logic
4. Decision logic validation
5. Low load handling
"""

import requests
import json
import sys
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"
PREDICT_ENDPOINT = f"{API_BASE_URL}/predict"
CARBON_ENDPOINT = f"{API_BASE_URL}/carbon/evaluate"

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Result tracking
results = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def log_step(step: int, title: str) -> None:
    """Log step header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"STEP {step}: {title}".center(80))
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def log_pass(msg: str) -> None:
    """Log passing test."""
    print(f"{GREEN}✓ PASS{RESET}: {msg}")


def log_fail(msg: str) -> None:
    """Log failing test."""
    print(f"{RED}✗ FAIL{RESET}: {msg}")


def log_info(msg: str) -> None:
    """Log info message."""
    print(f"{YELLOW}ℹ{RESET} {msg}")


def log_data(label: str, data: Any, truncate: bool = True) -> None:
    """Log data in structured format."""
    print(f"\n{BLUE}{label}:{RESET}")
    json_str = json.dumps(data, indent=2)
    if truncate and len(json_str) > 500:
        print(json_str[:500] + "\n... (truncated)")
    else:
        print(json_str)


def record_result(test_name: str, passed: bool, details: str = "") -> None:
    """Record test result."""
    results[test_name] = {
        "passed": passed,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# STEP 1: GET ENGINE 1 OUTPUT
# ============================================================================

def step_1_get_engine1_output() -> Optional[Dict[str, Any]]:
    """Get real Engine 1 prediction output."""
    log_step(1, "GET REAL ENGINE 1 OUTPUT")
    
    try:
        log_info(f"Calling: GET {PREDICT_ENDPOINT}")
        response = requests.get(PREDICT_ENDPOINT, timeout=10)
        
        if response.status_code != 200:
            log_fail(f"HTTP {response.status_code}: {response.text}")
            record_result("Engine1_GetPrediction", False, f"HTTP {response.status_code}")
            return None
        
        result = response.json()
        log_pass("Got prediction response")
        
        # Validate prediction structure
        if "prediction" not in result:
            log_fail("Response missing 'prediction' field")
            record_result("Engine1_GetPrediction", False, "Missing prediction field")
            return None
        
        prediction = result["prediction"]
        required_fields = ["predicted_cpu_percent", "predicted_load_level", 
                          "recommended_pods", "system_id"]
        
        missing_fields = [f for f in required_fields if f not in prediction]
        if missing_fields:
            log_fail(f"Missing fields: {missing_fields}")
            record_result("Engine1_GetPrediction", False, f"Missing: {missing_fields}")
            return None
        
        log_data("Engine 1 Output", prediction)
        
        # Validate field values
        cpu = prediction["predicted_cpu_percent"]
        load = prediction["predicted_load_level"]
        pods = prediction["recommended_pods"]
        
        log_pass(f"CPU: {cpu}%, Load: {load}, Pods: {pods}")
        
        if not (0 <= cpu <= 100):
            log_fail(f"CPU out of range: {cpu}")
            record_result("Engine1_GetPrediction", False, f"Invalid CPU: {cpu}")
            return None
        
        if load not in ("LOW", "NORMAL", "HIGH"):
            log_fail(f"Invalid load level: {load}")
            record_result("Engine1_GetPrediction", False, f"Invalid load: {load}")
            return None
        
        if not (1 <= pods <= 20):
            log_fail(f"Pods out of range: {pods}")
            record_result("Engine1_GetPrediction", False, f"Invalid pods: {pods}")
            return None
        
        log_pass("All Engine 1 fields valid")
        record_result("Engine1_GetPrediction", True, "Valid prediction obtained")
        
        return prediction
    
    except Exception as e:
        log_fail(f"Exception: {e}")
        record_result("Engine1_GetPrediction", False, str(e))
        return None


# ============================================================================
# STEP 2: TEST ENGINE 2 WITHOUT JOB DATA
# ============================================================================

def step_2_test_engine2_no_job_data(prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Test Engine 2 without job deferral data."""
    log_step(2, "TEST ENGINE 2 WITHOUT JOB DATA")
    
    try:
        # Build request using Engine 1 output
        request_data = {
            "system_id": prediction["system_id"],
            "predicted_cpu": prediction["predicted_cpu_percent"],
            "predicted_load_level": prediction["predicted_load_level"],
            "recommended_pods": prediction["recommended_pods"],
            "current_pods": prediction["recommended_pods"],  # Assume current = recommended
            "prediction_window_seconds": 30
        }
        
        log_info(f"Sending carbon evaluation request")
        log_data("Request Body", request_data)
        
        response = requests.post(CARBON_ENDPOINT, json=request_data, timeout=10)
        
        if response.status_code != 200:
            log_fail(f"HTTP {response.status_code}: {response.text}")
            record_result("Engine2_NoJobData", False, f"HTTP {response.status_code}")
            return None
        
        result = response.json()
        log_pass("Got carbon evaluation response")
        log_data("Response", result)
        
        # Validate response structure
        required_fields = ["status", "scenarios", "decision", "input"]
        missing_fields = [f for f in required_fields if f not in result]
        if missing_fields:
            log_fail(f"Response missing fields: {missing_fields}")
            record_result("Engine2_NoJobData", False, f"Missing: {missing_fields}")
            return None
        
        log_pass("Response has all required fields")
        
        # Validate scenarios
        scenarios = result.get("scenarios", [])
        if not scenarios:
            log_fail("No scenarios in response")
            record_result("Engine2_NoJobData", False, "No scenarios")
            return None
        
        log_pass(f"Found {len(scenarios)} scenarios")
        
        # Check scenario structure
        for i, scenario in enumerate(scenarios):
            required_scenario_fields = ["name", "pod_count", "carbon_gco2"]
            missing = [f for f in required_scenario_fields if f not in scenario]
            if missing:
                log_fail(f"Scenario {i} missing fields: {missing}")
                record_result("Engine2_NoJobData", False, f"Scenario {i} incomplete")
                return None
        
        log_pass("All scenarios have required fields")
        
        # Validate decision
        decision = result.get("decision", {})
        if "recommended_action" not in decision:
            log_fail("Decision missing recommended_action")
            record_result("Engine2_NoJobData", False, "No action in decision")
            return None
        
        action = decision["recommended_action"]
        valid_actions = ["scale_up", "scale_down", "delay_jobs", "hybrid", "no_action"]
        if action not in valid_actions:
            log_fail(f"Invalid action: {action}")
            record_result("Engine2_NoJobData", False, f"Invalid action: {action}")
            return None
        
        log_pass(f"Decision action valid: {action}")
        
        # Validate carbon values are present and numeric
        carbon_values = []
        for scenario in scenarios:
            carbon = scenario.get("carbon_gco2")
            if carbon is None:
                log_fail(f"Scenario {scenario.get('name')} missing carbon_gco2")
                record_result("Engine2_NoJobData", False, "Missing carbon value")
                return None
            
            if not isinstance(carbon, (int, float)):
                log_fail(f"Carbon value not numeric: {carbon}")
                record_result("Engine2_NoJobData", False, "Carbon not numeric")
                return None
            
            carbon_values.append(carbon)
        
        log_pass(f"Carbon values present: {carbon_values}")
        
        record_result("Engine2_NoJobData", True, f"Action: {action}")
        return result
    
    except Exception as e:
        log_fail(f"Exception: {e}")
        record_result("Engine2_NoJobData", False, str(e))
        return None


# ============================================================================
# STEP 3: TEST ENGINE 2 WITH JOB DEFERRAL
# ============================================================================

def step_3_test_engine2_with_job_deferral(prediction: Dict[str, Any], 
                                          baseline_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Test Engine 2 with job deferral data (mock Engine 3)."""
    log_step(3, "TEST ENGINE 2 WITH JOB DEFERRAL (MOCK ENGINE 3)")
    
    try:
        # Build request with job deferral data
        request_data = {
            "system_id": prediction["system_id"],
            "predicted_cpu": prediction["predicted_cpu_percent"],
            "predicted_load_level": prediction["predicted_load_level"],
            "recommended_pods": prediction["recommended_pods"],
            "current_pods": prediction["recommended_pods"],
            "prediction_window_seconds": 30,
            "delayable_jobs": 10,
            "workload_reduction_percent": 0.30  # 30%
        }
        
        log_info("Adding job deferral data (mock Engine 3)")
        log_data("Request with deferral", request_data)
        
        response = requests.post(CARBON_ENDPOINT, json=request_data, timeout=10)
        
        if response.status_code != 200:
            log_fail(f"HTTP {response.status_code}: {response.text}")
            record_result("Engine2_WithJobDeferral", False, f"HTTP {response.status_code}")
            return None
        
        result = response.json()
        log_pass("Got carbon evaluation response with deferral data")
        
        # Compare with baseline
        baseline_scenarios = baseline_result.get("scenarios", [])
        deferral_scenarios = result.get("scenarios", [])
        
        baseline_carbon = [s.get("carbon_gco2", 0) for s in baseline_scenarios]
        deferral_carbon = [s.get("carbon_gco2", 0) for s in deferral_scenarios]
        
        log_info(f"Baseline carbon: {baseline_carbon}")
        log_info(f"With deferral carbon: {deferral_carbon}")
        
        # Check if carbon was reduced
        baseline_min = min(baseline_carbon) if baseline_carbon else 0
        deferral_min = min(deferral_carbon) if deferral_carbon else 0
        
        if deferral_min >= baseline_min:
            log_fail(f"Carbon NOT reduced with deferral: {deferral_min} >= {baseline_min}")
            record_result("Engine2_WithJobDeferral", False, "No carbon reduction")
        else:
            log_pass(f"Carbon reduced: {baseline_min} → {deferral_min}")
            record_result("Engine2_WithJobDeferral", True, "Carbon properly reduced")
        
        # Check decision action
        action = result.get("decision", {}).get("recommended_action")
        if action in ("delay_jobs", "hybrid"):
            log_pass(f"Decision changed to job-aware: {action}")
        else:
            log_info(f"Decision still: {action} (may be OK if high load)")
        
        log_data("Deferral Result", result)
        return result
    
    except Exception as e:
        log_fail(f"Exception: {e}")
        record_result("Engine2_WithJobDeferral", False, str(e))
        return None


# ============================================================================
# STEP 4: LOW LOAD TEST
# ============================================================================

def step_4_test_low_load() -> Optional[Dict[str, Any]]:
    """Test Engine 2 with low load scenario."""
    log_step(4, "LOW LOAD TEST")
    
    try:
        request_data = {
            "system_id": "low-load-test",
            "predicted_cpu": 15.0,  # Very low CPU
            "predicted_load_level": "LOW",
            "recommended_pods": 1,  # Minimal pods
            "current_pods": 3,  # Currently over-provisioned
            "prediction_window_seconds": 30
        }
        
        log_info("Testing low load scenario")
        log_data("Request", request_data)
        
        response = requests.post(CARBON_ENDPOINT, json=request_data, timeout=10)
        
        if response.status_code != 200:
            log_fail(f"HTTP {response.status_code}")
            record_result("Engine2_LowLoad", False, f"HTTP {response.status_code}")
            return None
        
        result = response.json()
        log_pass("Got response for low load")
        
        decision = result.get("decision", {})
        action = decision.get("recommended_action")
        
        # For low load, expect no_action or scale_down
        if action in ("no_action", "scale_down"):
            log_pass(f"Correct action for low load: {action}")
            record_result("Engine2_LowLoad", True, f"Correct action: {action}")
        else:
            log_fail(f"Unexpected action for low load: {action}")
            record_result("Engine2_LowLoad", False, f"Wrong action: {action}")
        
        # Check carbon values are low
        scenarios = result.get("scenarios", [])
        carbon_values = [s.get("carbon_gco2", 0) for s in scenarios]
        max_carbon = max(carbon_values) if carbon_values else 0
        
        if max_carbon < 10:  # Very low carbon for low load
            log_pass(f"Carbon values appropriately low: max={max_carbon}")
        else:
            log_info(f"Carbon relatively high for low load: max={max_carbon}")
        
        log_data("Low Load Result", result)
        return result
    
    except Exception as e:
        log_fail(f"Exception: {e}")
        record_result("Engine2_LowLoad", False, str(e))
        return None


# ============================================================================
# STEP 5: CARBON CALCULATION VALIDATION
# ============================================================================

def step_5_validate_carbon_calculations(no_deferral_result: Optional[Dict[str, Any]],
                                       with_deferral_result: Optional[Dict[str, Any]]) -> bool:
    """Validate that carbon calculations are meaningful (not static)."""
    log_step(5, "CARBON CALCULATION VALIDATION")
    
    all_passed = True
    
    try:
        # Test 1: Carbon increases with pod count
        log_info("Test 5a: Carbon increases with pod count")
        
        test_configs = [
            {"pods": 1, "cpu": 20},
            {"pods": 5, "cpu": 50},
            {"pods": 10, "cpu": 80}
        ]
        
        carbon_by_pods = {}
        
        for config in test_configs:
            request = {
                "system_id": "carbon-test",
                "predicted_cpu": config["cpu"],
                "predicted_load_level": "NORMAL",
                "recommended_pods": config["pods"],
                "current_pods": config["pods"],
                "prediction_window_seconds": 30
            }
            
            response = requests.post(CARBON_ENDPOINT, json=request, timeout=10)
            if response.status_code != 200:
                log_fail(f"Failed to get response for {config['pods']} pods")
                all_passed = False
                continue
            
            result = response.json()
            scenarios = result.get("scenarios", [])
            
            if scenarios:
                carbon = scenarios[0].get("carbon_gco2", 0)  # First scenario
                carbon_by_pods[config["pods"]] = carbon
                log_info(f"  {config['pods']} pods → {carbon:.2f} g CO2")
        
        # Validate carbon increases with pod count
        if carbon_by_pods:
            pods_list = sorted(carbon_by_pods.keys())
            carbons = [carbon_by_pods[p] for p in pods_list]
            
            increasing = all(carbons[i] <= carbons[i+1] for i in range(len(carbons)-1))
            
            if increasing:
                log_pass("Carbon increases (or stays same) with pod count ✓")
            else:
                log_fail("Carbon does NOT correlate with pod count")
                all_passed = False
        
        # Test 2: Scenarios have different carbon values
        log_info("\nTest 5b: Scenarios have different carbon values")
        
        if no_deferral_result:
            scenarios = no_deferral_result.get("scenarios", [])
            carbon_values = [s.get("carbon_gco2", 0) for s in scenarios]
            
            if len(set(carbon_values)) == 1:
                log_fail("All scenarios have same carbon value (static!) ✗")
                all_passed = False
            else:
                log_pass(f"Scenarios have varying carbon: {carbon_values}")
        
        # Test 3: Job deferral reduces carbon meaningfully
        log_info("\nTest 5c: Job deferral reduces carbon meaningfully")
        
        if no_deferral_result and with_deferral_result:
            baseline_carbon = min([s.get("carbon_gco2", float('inf')) for s in 
                                   no_deferral_result.get("scenarios", [])])
            deferral_carbon = min([s.get("carbon_gco2", float('inf')) for s in 
                                   with_deferral_result.get("scenarios", [])])
            
            reduction_percent = ((baseline_carbon - deferral_carbon) / baseline_carbon * 100 
                               if baseline_carbon > 0 else 0)
            
            log_info(f"  Baseline: {baseline_carbon:.2f} g CO2")
            log_info(f"  With deferral: {deferral_carbon:.2f} g CO2")
            log_info(f"  Reduction: {reduction_percent:.1f}%")
            
            if reduction_percent > 0:
                log_pass(f"Job deferral meaningfully reduces carbon by {reduction_percent:.1f}%")
            else:
                log_fail("Job deferral does not reduce carbon")
                all_passed = False
        
        record_result("Engine2_CarbonCalculations", all_passed, 
                     "Carbon calculations are meaningful" if all_passed else "Issues found")
        return all_passed
    
    except Exception as e:
        log_fail(f"Exception: {e}")
        record_result("Engine2_CarbonCalculations", False, str(e))
        return False


# ============================================================================
# STEP 6: DECISION LOGIC VALIDATION
# ============================================================================

def step_6_validate_decision_logic() -> bool:
    """Validate decision logic is not just raw scaling."""
    log_step(6, "DECISION LOGIC VALIDATION")
    
    all_passed = True
    
    try:
        # Test: System should prefer conservative action when safe
        
        test_cases = [
            {
                "name": "High Load - Should scale up",
                "data": {
                    "predicted_cpu": 85.0,
                    "predicted_load_level": "HIGH",
                    "recommended_pods": 8,
                    "current_pods": 2
                },
                "expect_action": "scale_up"
            },
            {
                "name": "Low Load - Should scale down",
                "data": {
                    "predicted_cpu": 15.0,
                    "predicted_load_level": "LOW",
                    "recommended_pods": 1,
                    "current_pods": 5
                },
                "expect_action": lambda a: a in ("scale_down", "no_action")
            },
            {
                "name": "Normal Load - Should not always scale up",
                "data": {
                    "predicted_cpu": 50.0,
                    "predicted_load_level": "NORMAL",
                    "recommended_pods": 4,
                    "current_pods": 4
                },
                "expect_action": lambda a: a in ("no_action", "scale_down", "scale_up")
            }
        ]
        
        for test_case in test_cases:
            request = {
                "system_id": f"decision-test",
                "predicted_cpu": test_case["data"]["predicted_cpu"],
                "predicted_load_level": test_case["data"]["predicted_load_level"],
                "recommended_pods": test_case["data"]["recommended_pods"],
                "current_pods": test_case["data"]["current_pods"],
                "prediction_window_seconds": 30
            }
            
            response = requests.post(CARBON_ENDPOINT, json=request, timeout=10)
            
            if response.status_code != 200:
                log_fail(f"{test_case['name']}: Failed to get response")
                all_passed = False
                continue
            
            result = response.json()
            action = result.get("decision", {}).get("recommended_action")
            expected = test_case["expect_action"]
            
            # Check if action matches expectation
            if callable(expected):
                matches = expected(action)
            else:
                matches = (action == expected)
            
            if matches:
                log_pass(f"{test_case['name']}: {action} ✓")
            else:
                log_fail(f"{test_case['name']}: Expected {expected}, got {action}")
                all_passed = False
        
        record_result("Engine2_DecisionLogic", all_passed, 
                     "Decision logic is sound" if all_passed else "Some decision issues")
        return all_passed
    
    except Exception as e:
        log_fail(f"Exception: {e}")
        record_result("Engine2_DecisionLogic", False, str(e))
        return False


# ============================================================================
# STEP 7: DATA FLOW VALIDATION
# ============================================================================

def step_7_validate_data_flow(engine1_output: Dict[str, Any]) -> bool:
    """Validate Engine 1 → Engine 2 data flow."""
    log_step(7, "DATA FLOW VALIDATION (ENGINE 1 → ENGINE 2)")
    
    try:
        # Test: Can pass Engine 1 output directly without mapping
        
        request = {
            "system_id": engine1_output["system_id"],
            "predicted_cpu": engine1_output["predicted_cpu_percent"],
            "predicted_load_level": engine1_output["predicted_load_level"],
            "recommended_pods": engine1_output["recommended_pods"],
            "current_pods": engine1_output["recommended_pods"],
            "prediction_window_seconds": 30
        }
        
        log_info("Direct mapping from Engine 1 output:")
        for key, value in request.items():
            log_info(f"  {key}: {value}")
        
        response = requests.post(CARBON_ENDPOINT, json=request, timeout=10)
        
        if response.status_code != 200:
            log_fail(f"Failed to pass Engine 1 output: HTTP {response.status_code}")
            record_result("Engine2_DataFlow", False, "Endpoint rejected data")
            return False
        
        result = response.json()
        
        # Verify echo-back in input
        echoed = result.get("input", {})
        
        fields_to_check = ["predicted_cpu", "predicted_load_level", 
                          "recommended_pods", "current_pods"]
        
        all_match = True
        for field in fields_to_check:
            if field in request and field in echoed:
                if request[field] == echoed[field]:
                    log_pass(f"Field '{field}' echoed correctly")
                else:
                    log_fail(f"Field '{field}' not echoed correctly")
                    all_match = False
        
        if all_match:
            log_pass("Engine 1 → Engine 2 data flow works correctly")
            record_result("Engine2_DataFlow", True, "Direct mapping works")
        else:
            log_fail("Data flow has issues")
            record_result("Engine2_DataFlow", False, "Field mapping errors")
        
        return all_match
    
    except Exception as e:
        log_fail(f"Exception: {e}")
        record_result("Engine2_DataFlow", False, str(e))
        return False


# ============================================================================
# FINAL REPORT
# ============================================================================

def print_final_report() -> None:
    """Print final validation report."""
    print(f"\n\n{BLUE}{'=' * 80}{RESET}")
    print("FINAL VALIDATION REPORT - ENGINE 2".center(80))
    print(f"{BLUE}{'=' * 80}{RESET}\n")
    
    # Calculate pass/fail for major categories
    categories = {
        "Engine 2 Endpoint": ["Engine2_NoJobData", "Engine2_WithJobDeferral"],
        "Engine 1 → Engine 2 Integration": ["Engine1_GetPrediction", "Engine2_DataFlow"],
        "Scenario Generation": ["Engine2_NoJobData"],
        "Carbon Calculation": ["Engine2_CarbonCalculations"],
        "Decision Logic": ["Engine2_DecisionLogic"],
        "Low Load Handling": ["Engine2_LowLoad"]
    }
    
    category_results = {}
    
    for category, test_keys in categories.items():
        category_passed = all(results.get(key, {}).get("passed", False) for key in test_keys)
        category_results[category] = category_passed
        
        status = f"{GREEN}PASS{RESET}" if category_passed else f"{RED}FAIL{RESET}"
        print(f"{category}: {status}")
    
    print(f"\n{BLUE}{'-' * 80}{RESET}")
    print("DETAILED RESULTS:\n")
    
    for test_name, result in results.items():
        status = f"{GREEN}✓{RESET}" if result["passed"] else f"{RED}✗{RESET}"
        print(f"{status} {test_name}: {result['details']}")
    
    # Overall status
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    all_passed = all(category_results.values())
    
    if all_passed:
        print(f"{GREEN}ENGINE 2 VALIDATED ✅{RESET}".center(80))
    else:
        print(f"{RED}ENGINE 2 VALIDATION FAILED ❌{RESET}".center(80))
    
    print(f"{BLUE}{'=' * 80}{RESET}\n")
    
    return all_passed


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main() -> int:
    """Run complete validation suite."""
    
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print("ENGINE 2 VALIDATION SUITE - COMPLETE QA TESTING".center(80))
    print(f"{BLUE}{'=' * 80}{RESET}\n")
    
    # Step 1: Get Engine 1 output
    engine1_output = step_1_get_engine1_output()
    if not engine1_output:
        log_fail("Cannot proceed without Engine 1 output")
        return 1
    
    # Step 2: Test Engine 2 without job data
    no_deferral_result = step_2_test_engine2_no_job_data(engine1_output)
    if not no_deferral_result:
        log_fail("Cannot proceed without baseline Engine 2 result")
        return 1
    
    # Step 3: Test Engine 2 with job deferral
    with_deferral_result = step_3_test_engine2_with_job_deferral(engine1_output, 
                                                                 no_deferral_result)
    
    # Step 4: Low load test
    step_4_test_low_load()
    
    # Step 5: Carbon calculation validation
    step_5_validate_carbon_calculations(no_deferral_result, with_deferral_result)
    
    # Step 6: Decision logic validation
    step_6_validate_decision_logic()
    
    # Step 7: Data flow validation
    step_7_validate_data_flow(engine1_output)
    
    # Print final report
    all_passed = print_final_report()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
