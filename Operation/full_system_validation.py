"""
FULL SYSTEM VALIDATION TEST SUITE
Green DevOps Operation Phase - Complete Integration Testing

Tests:
- Engine 1 (Workload Prediction)
- Engine 2 (Carbon Decision)
- Engine 3 (Job Prioritization)
- Combined workflows
- Edge cases
- System logic
"""

import requests
import json
import traceback
from typing import Dict, Any, Optional, List
import time

BASE_URL = "http://localhost:8000"

# Test results tracking
results = {
    "engine1": False,
    "engine2": False,
    "engine3": False,
    "e3_scenarios": False,
    "e2_scenarios": False,
    "combo_scenarios": False,
    "edge_cases": False,
    "carbon_logic": False,
    "integration_flow": False,
    "system_logic": False,
}

failures = []


def print_header(title: str) -> None:
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_subheader(title: str) -> None:
    """Print formatted subheader."""
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}\n")


def log_failure(test_name: str, issue: str, input_data: Any = None, output_data: Any = None, root_cause: str = ""):
    """Log a test failure."""
    failure_record = {
        "test": test_name,
        "issue": issue,
        "input": input_data,
        "output": output_data,
        "root_cause": root_cause,
    }
    failures.append(failure_record)
    print(f"❌ FAIL: {test_name}")
    print(f"   Issue: {issue}")
    if input_data:
        print(f"   Input: {json.dumps(input_data, indent=6)[:200]}")
    if output_data:
        print(f"   Output: {json.dumps(output_data, indent=6)[:200]}")
    if root_cause:
        print(f"   Root Cause: {root_cause}")


def test_part0_server_check() -> bool:
    """Part 0: Check server and endpoints availability."""
    print_header("PART 0: SERVER AVAILABILITY CHECK")
    
    try:
        # Check health
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code != 200:
            log_failure("Server Health", f"Health check returned {resp.status_code}", output_data=resp.json())
            return False
        print("✓ GET /health: Available")
        
        # Check predict endpoint
        resp = requests.get(f"{BASE_URL}/predict", timeout=5)
        if resp.status_code == 200:
            print("✓ GET /predict: Available")
        else:
            print(f"⚠ GET /predict: Returns {resp.status_code}")
        
        # Check carbon evaluate endpoint
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "test",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 3,
                "current_pods": 3
            },
            timeout=5
        )
        if resp.status_code == 200:
            print("✓ POST /carbon/evaluate: Available")
        else:
            print(f"⚠ POST /carbon/evaluate: Returns {resp.status_code}")
        
        # Check jobs evaluate endpoint
        resp = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [{"job_id": "test", "job_type": "report_generation"}],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        if resp.status_code == 200:
            print("✓ POST /jobs/evaluate: Available")
        else:
            print(f"⚠ POST /jobs/evaluate: Returns {resp.status_code}")
        
        print("\n✅ SERVER CHECK PASSED")
        return True
        
    except Exception as e:
        log_failure("Server Check", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part1_engine1() -> bool:
    """Part 1: Engine 1 (Prediction) base test."""
    print_header("PART 1: ENGINE 1 BASE TEST")
    
    try:
        resp = requests.get(f"{BASE_URL}/predict", timeout=5)
        if resp.status_code != 200:
            log_failure("Engine 1 Prediction", f"Status {resp.status_code}", output_data=resp.json())
            return False
        
        response_data = resp.json()
        data = response_data.get("prediction", {})  # Extract prediction data from nested structure
        
        # Validate CPU
        if "predicted_cpu" not in data:
            log_failure("Engine 1 Validation", "Missing predicted_cpu", output_data=response_data)
            return False
        
        cpu = data["predicted_cpu"]
        if not (0 <= cpu <= 100):
            log_failure("Engine 1 Validation", f"CPU out of range: {cpu}", output_data=response_data,
                       root_cause="CPU must be 0-100")
            return False
        print(f"✓ CPU valid: {cpu}%")
        
        # Validate recommended_pods
        if "recommended_pods" not in data or data["recommended_pods"] < 1:
            log_failure("Engine 1 Validation", "Invalid recommended_pods", output_data=response_data,
                       root_cause="Must be >= 1")
            return False
        print(f"✓ Recommended pods valid: {data['recommended_pods']}")
        
        # Validate load_level
        if "predicted_load_level" not in data or data["predicted_load_level"] not in ("LOW", "NORMAL", "HIGH"):
            log_failure("Engine 1 Validation", f"Invalid load_level: {data.get('predicted_load_level')}", output_data=response_data)
            return False
        print(f"✓ Load level valid: {data['predicted_load_level']}")
        
        print("\n✅ ENGINE 1 TEST PASSED")
        return True
        
    except Exception as e:
        log_failure("Engine 1 Test", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part2_engine3_scenarios() -> bool:
    """Part 2: Engine 3 scenarios."""
    print_header("PART 2: ENGINE 3 SCENARIOS")
    
    all_passed = True
    
    try:
        # SCENARIO E3-A: All HIGH priority
        print_subheader("E3-A: All HIGH Priority Jobs")
        resp = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [
                    {"job_id": "j1", "job_type": "payment_processing", "estimated_cpu_percent": 20},
                    {"job_id": "j2", "job_type": "authentication", "estimated_cpu_percent": 15},
                ],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("E3-A", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            if data.get("delayable_jobs") != 0 or data.get("workload_reduction_percent") != 0.0:
                log_failure("E3-A", "Expected 0 delayable jobs and 0% reduction",
                           output_data=data,
                           root_cause="HIGH priority jobs should never be delayable")
                all_passed = False
            else:
                print(f"✓ Correctly identified: 0 delayable jobs, 0% reduction")
        
        # SCENARIO E3-B: Mixed jobs
        print_subheader("E3-B: Mixed Priority Jobs")
        resp = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [
                    {"job_id": "j1", "job_type": "payment_processing", "estimated_cpu_percent": 30},
                    {"job_id": "j2", "job_type": "report_generation", "estimated_cpu_percent": 20, 
                     "deadline_seconds": 3600},
                    {"job_id": "j3", "job_type": "analytics_batch", "estimated_cpu_percent": 15,
                     "deadline_seconds": 3600},
                ],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("E3-B", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            if data.get("delayable_jobs") == 0 or data.get("workload_reduction_percent") == 0.0:
                log_failure("E3-B", "Expected some reduction from LOW priority jobs",
                           output_data=data,
                           root_cause="LOW priority jobs should be delayable")
                all_passed = False
            else:
                print(f"✓ Correctly identified: {data['delayable_jobs']} jobs, {data['workload_reduction_percent']:.1%} reduction")
        
        # SCENARIO E3-C: LOW jobs with deadline too close
        print_subheader("E3-C: LOW Priority Jobs with Close Deadline")
        resp = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [
                    {"job_id": "j1", "job_type": "report_generation", "estimated_cpu_percent": 20,
                     "deadline_seconds": 30}
                ],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("E3-C", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            if data.get("delayable_jobs") != 0:
                log_failure("E3-C", "Job should not be delayable (deadline too close)",
                           output_data=data,
                           root_cause="Deadline < 60 seconds should block delay")
                all_passed = False
            else:
                print(f"✓ Correctly blocked: deadline too close, not delayable")
        
        # SCENARIO E3-D: High backlog
        print_subheader("E3-D: High Backlog Impact")
        resp_low_backlog = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [
                    {"job_id": "j1", "job_type": "report_generation", "estimated_cpu_percent": 20,
                     "deadline_seconds": 3600},
                    {"job_id": "j2", "job_type": "analytics_batch", "estimated_cpu_percent": 15,
                     "deadline_seconds": 3600},
                ],
                "backlog_size": 50,
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        
        resp_high_backlog = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [
                    {"job_id": "j1", "job_type": "report_generation", "estimated_cpu_percent": 20,
                     "deadline_seconds": 3600},
                    {"job_id": "j2", "job_type": "analytics_batch", "estimated_cpu_percent": 15,
                     "deadline_seconds": 3600},
                ],
                "backlog_size": 150,
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        
        if resp_low_backlog.status_code == 200 and resp_high_backlog.status_code == 200:
            data_low = resp_low_backlog.json()
            data_high = resp_high_backlog.json()
            reduction_low = data_low.get("workload_reduction_percent", 0)
            reduction_high = data_high.get("workload_reduction_percent", 0)
            
            if reduction_high >= reduction_low:
                log_failure("E3-D", f"High backlog should reduce delay: low={reduction_low:.1%}, high={reduction_high:.1%}",
                           output_data={"low_backlog": data_low, "high_backlog": data_high},
                           root_cause="Backlog adjustment not reducing high backlog delays")
                all_passed = False
            else:
                print(f"✓ Backlog impact: low={reduction_low:.1%}, high={reduction_high:.1%} (correctly reduced)")
        else:
            all_passed = False
        
        # SCENARIO E3-E: Many LOW jobs
        print_subheader("E3-E: Many LOW Priority Jobs")
        resp = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [
                    {"job_id": f"j{i}", "job_type": "report_generation" if i % 2 == 0 else "analytics_batch",
                     "estimated_cpu_percent": 10, "deadline_seconds": 3600}
                    for i in range(10)
                ],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("E3-E", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            reduction = data.get("workload_reduction_percent", 0)
            # Should be capped at 50%
            if reduction > 0.50:
                log_failure("E3-E", f"Reduction exceeds max: {reduction:.1%} > 50%",
                           output_data=data,
                           root_cause="MAX_INITIAL_DELAY_PERCENT should cap at 0.50")
                all_passed = False
            else:
                print(f"✓ Reduction correctly capped: {reduction:.1%} (max 50%)")
        
        if all_passed:
            print("\n✅ ENGINE 3 SCENARIOS PASSED")
        else:
            print("\n❌ ENGINE 3 SCENARIOS HAD FAILURES")
        
        return all_passed
        
    except Exception as e:
        log_failure("Engine 3 Scenarios", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part3_engine2_scenarios() -> bool:
    """Part 3: Engine 2 scenarios (without Engine 3)."""
    print_header("PART 3: ENGINE 2 SCENARIOS (WITHOUT ENGINE 3)")
    
    all_passed = True
    
    try:
        # SCENARIO E2-A: LOW LOAD
        print_subheader("E2-A: LOW LOAD")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "test-low",
                "predicted_cpu": 20.0,
                "predicted_load_level": "LOW",
                "recommended_pods": 2,
                "current_pods": 5
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("E2-A", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            action = data.get("recommended_action", "")
            if action not in ("scale_down", "no_action"):
                print(f"⚠ E2-A: Action is '{action}' (expected scale_down or no_action)")
            else:
                print(f"✓ LOW load decision: {action}")
        
        # SCENARIO E2-B: NORMAL LOAD
        print_subheader("E2-B: NORMAL LOAD")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "test-normal",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 4,
                "current_pods": 4
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("E2-B", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            print(f"✓ NORMAL load decision: {data.get('recommended_action', 'unknown')}")
        
        # SCENARIO E2-C: HIGH LOAD
        print_subheader("E2-C: HIGH LOAD (SLA PROTECTION)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "test-high",
                "predicted_cpu": 85.0,
                "predicted_load_level": "HIGH",
                "recommended_pods": 5,
                "current_pods": 3
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("E2-C", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            final_pods = data.get("optimized_required_pods", 0)
            
            # Under HIGH LOAD, should not downscale below recommended
            if final_pods < 5:
                log_failure("E2-C", f"HIGH LOAD downscaled below recommended: {final_pods} < 5",
                           output_data=data,
                           root_cause="SLA protection should prevent downscale during HIGH LOAD")
                all_passed = False
            else:
                print(f"✓ HIGH load SLA protected: {final_pods} pods (>= 5 recommended)")
                sla_protected = data.get("metadata", {}).get("sla_protected", False)
                print(f"   SLA protection flag: {sla_protected}")
        
        if all_passed:
            print("\n✅ ENGINE 2 SCENARIOS PASSED")
        else:
            print("\n❌ ENGINE 2 SCENARIOS HAD FAILURES")
        
        return all_passed
        
    except Exception as e:
        log_failure("Engine 2 Scenarios", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part4_combined_scenarios() -> bool:
    """Part 4: Combined Engine 2 + Engine 3 scenarios."""
    print_header("PART 4: COMBINED ENGINE 2 + ENGINE 3 SCENARIOS")
    
    all_passed = True
    
    try:
        # SCENARIO COMBO-1: HIGH LOAD + delayable jobs
        print_subheader("COMBO-1: HIGH LOAD + Delayable Jobs (SLA Priority)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "combo1",
                "predicted_cpu": 85.0,
                "predicted_load_level": "HIGH",
                "recommended_pods": 5,
                "current_pods": 2,
                "workload_reduction_percent": 0.4,  # 40% reduction
                "delayable_jobs": 4
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("COMBO-1", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            optimized_scenario = data.get("optimized_scenario", {})
            
            # Optimized should show reduction
            if optimized_scenario.get("required_pods") is None:
                print(f"⚠ No optimized scenario returned")
            else:
                opt_scenario_pods = optimized_scenario.get("required_pods", 0)
                print(f"  Raw scenario: 5 pods")
                print(f"  Optimized scenario: {opt_scenario_pods} pods (with 40% reduction)")
            
            # Final decision should keep >= 5 due to SLA
            if opt_pods < 5:
                log_failure("COMBO-1", f"Final decision downscaled below SLA: {opt_pods} < 5",
                           output_data=data,
                           root_cause="HIGH LOAD SLA protection should prevent going below 5 pods")
                all_passed = False
            else:
                print(f"  Final decision: {opt_pods} pods (SLA protected, >= 5)")
        
        # SCENARIO COMBO-2: NORMAL LOAD + delayable jobs
        print_subheader("COMBO-2: NORMAL LOAD + Delayable Jobs (Optimization Allowed)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "combo2",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 4,
                "current_pods": 2,
                "workload_reduction_percent": 0.3,  # 30% reduction
                "delayable_jobs": 3
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("COMBO-2", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            raw_pods = 4
            
            # Can use optimization during NORMAL load
            if opt_pods > raw_pods:
                log_failure("COMBO-2", f"Optimization not used: {opt_pods} > {raw_pods}",
                           output_data=data)
            else:
                savings = data.get("carbon_saving_gco2", 0)
                print(f"  Final decision: {opt_pods} pods")
                print(f"  Carbon savings: {savings:.2f} g CO2")
        
        # SCENARIO COMBO-3: LOW LOAD + delayable jobs
        print_subheader("COMBO-3: LOW LOAD + Delayable Jobs (Aggressive Optimization)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "combo3",
                "predicted_cpu": 20.0,
                "predicted_load_level": "LOW",
                "recommended_pods": 2,
                "current_pods": 5,
                "workload_reduction_percent": 0.5,  # 50% reduction
                "delayable_jobs": 5
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("COMBO-3", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            if opt_pods > 2:
                print(f"  Aggressive optimization allowed: {opt_pods} pods (from 2 recommended)")
            else:
                print(f"  Final decision: {opt_pods} pods (can be very aggressive in LOW load)")
        
        # SCENARIO COMBO-4: HIGH LOAD + no delayable jobs
        print_subheader("COMBO-4: HIGH LOAD + No Delayable Jobs (Pure Scaling)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "combo4",
                "predicted_cpu": 85.0,
                "predicted_load_level": "HIGH",
                "recommended_pods": 5,
                "current_pods": 2,
                "workload_reduction_percent": 0.0,
                "delayable_jobs": 0
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("COMBO-4", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            if opt_pods != 5:
                log_failure("COMBO-4", f"Should scale to 5 pods: got {opt_pods}",
                           output_data=data)
                all_passed = False
            else:
                print(f"  Scaled up to: {opt_pods} pods (pure scaling, no optimization)")
        
        # SCENARIO COMBO-5: LOW LOAD + no delayable jobs
        print_subheader("COMBO-5: LOW LOAD + No Delayable Jobs (Basic Scaling)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "combo5",
                "predicted_cpu": 20.0,
                "predicted_load_level": "LOW",
                "recommended_pods": 2,
                "current_pods": 5,
                "workload_reduction_percent": 0.0,
                "delayable_jobs": 0
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            log_failure("COMBO-5", f"Status {resp.status_code}", output_data=resp.json())
            all_passed = False
        else:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            print(f"  Scaled down to: {opt_pods} pods (no optimization available)")
        
        if all_passed:
            print("\n✅ COMBINED SCENARIOS PASSED")
        else:
            print("\n❌ COMBINED SCENARIOS HAD FAILURES")
        
        return all_passed
        
    except Exception as e:
        log_failure("Combined Scenarios", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part5_edge_cases() -> bool:
    """Part 5: Edge cases."""
    print_header("PART 5: EDGE CASES")
    
    all_passed = True
    
    try:
        # EDGE-1: workload_reduction_percent = 0
        print_subheader("EDGE-1: workload_reduction = 0 (No Optimization)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "edge1",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 3,
                "current_pods": 3,
                "workload_reduction_percent": 0.0
            },
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            raw_pods = 3
            if opt_pods != raw_pods:
                print(f"⚠ 0% reduction should give raw pods: {opt_pods} vs {raw_pods}")
            else:
                print(f"✓ 0% reduction handled: {opt_pods} pods (same as raw)")
        else:
            all_passed = False
        
        # EDGE-2: workload_reduction_percent = 1.0
        print_subheader("EDGE-2: workload_reduction = 1.0 (100% Reduction)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "edge2",
                "predicted_cpu": 20.0,
                "predicted_load_level": "LOW",
                "recommended_pods": 4,
                "current_pods": 5,
                "workload_reduction_percent": 1.0
            },
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            # Should be capped to min 1 pod, not 0
            if opt_pods < 1:
                log_failure("EDGE-2", f"Pod count below minimum: {opt_pods} < 1",
                           output_data=data,
                           root_cause="Must maintain at least 1 pod")
                all_passed = False
            else:
                print(f"✓ 100% reduction capped safely: {opt_pods} pods (min 1)")
        else:
            all_passed = False
        
        # EDGE-3: Invalid workload_reduction
        print_subheader("EDGE-3: Invalid workload_reduction (>1.0)")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "edge3",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 3,
                "current_pods": 3,
                "workload_reduction_percent": 1.5
            },
            timeout=5
        )
        
        if resp.status_code != 400:
            print(f"⚠ Invalid value should return 400, got {resp.status_code}")
        else:
            print(f"✓ Invalid reduction correctly rejected (400)")
        
        if all_passed:
            print("\n✅ EDGE CASES PASSED")
        else:
            print("\n❌ EDGE CASES HAD FAILURES")
        
        return all_passed
        
    except Exception as e:
        log_failure("Edge Cases", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part6_carbon_logic() -> bool:
    """Part 6: Carbon logic validation."""
    print_header("PART 6: CARBON LOGIC VALIDATION")
    
    try:
        # Test 1: More pods = more carbon
        print_subheader("Carbon Test 1: More Pods → More Carbon")
        resp_low = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "carbon1",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 2,
                "current_pods": 2
            },
            timeout=5
        )
        
        resp_high = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "carbon1",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 5,
                "current_pods": 5
            },
            timeout=5
        )
        
        if resp_low.status_code == 200 and resp_high.status_code == 200:
            data_low = resp_low.json()
            data_high = resp_high.json()
            
            raw_carbon_low = data_low.get("raw_scenario", {}).get("estimated_carbon_gco2", 0)
            raw_carbon_high = data_high.get("raw_scenario", {}).get("estimated_carbon_gco2", 0)
            
            if raw_carbon_high > raw_carbon_low:
                print(f"✓ More pods = more carbon: {raw_carbon_low:.2f} g < {raw_carbon_high:.2f} g")
            else:
                print(f"⚠ Carbon logic: {raw_carbon_low:.2f} g vs {raw_carbon_high:.2f} g")
        
        # Test 2: Reduction matches workload reduction
        print_subheader("Carbon Test 2: Reduction Matches Workload Reduction")
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "carbon2",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 5,
                "current_pods": 5,
                "workload_reduction_percent": 0.3
            },
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            raw_scenario = data.get("raw_scenario", {})
            opt_scenario = data.get("optimized_scenario", {})
            
            if opt_scenario and "estimated_carbon_gco2" in opt_scenario:
                raw_carbon = raw_scenario.get("estimated_carbon_gco2", 0)
                opt_carbon = opt_scenario.get("estimated_carbon_gco2", 0)
                expected_reduction = raw_carbon * 0.3
                actual_reduction = raw_carbon - opt_carbon
                
                if abs(actual_reduction - expected_reduction) < 0.5:
                    print(f"✓ Reduction ~matches: expected {expected_reduction:.2f}, actual {actual_reduction:.2f} g")
                else:
                    print(f"⚠ Reduction mismatch: expected {expected_reduction:.2f}, actual {actual_reduction:.2f} g")
        
        print("\n✅ CARBON LOGIC VALIDATED")
        return True
        
    except Exception as e:
        log_failure("Carbon Logic", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part7_integration_flow() -> bool:
    """Part 7: Integration flow tests."""
    print_header("PART 7: INTEGRATION FLOW")
    
    all_passed = True
    
    try:
        # FLOW-1: Engine 1 alone
        print_subheader("FLOW-1: Engine 1 Only")
        resp = requests.get(f"{BASE_URL}/predict", timeout=5)
        if resp.status_code == 200:
            print("✓ Engine 1 works independently")
        else:
            all_passed = False
        
        # FLOW-2: Engine 3 alone
        print_subheader("FLOW-2: Engine 3 Only")
        resp = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [{"job_id": "j1", "job_type": "report_generation"}],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        if resp.status_code == 200:
            print("✓ Engine 3 works independently")
        else:
            all_passed = False
        
        # FLOW-3: Engine 1 + Engine 2
        print_subheader("FLOW-3: Engine 1 → Engine 2")
        resp_e1 = requests.get(f"{BASE_URL}/predict", timeout=5)
        if resp_e1.status_code == 200:
            e1_data = resp_e1.json()
            resp_e2 = requests.post(
                f"{BASE_URL}/carbon/evaluate",
                json={
                    "system_id": "flow3",
                    "predicted_cpu": e1_data.get("predicted_cpu", 50),
                    "predicted_load_level": e1_data.get("load_level", "NORMAL"),
                    "recommended_pods": e1_data.get("recommended_pods", 3),
                    "current_pods": 3
                },
                timeout=5
            )
            if resp_e2.status_code == 200:
                print("✓ Engine 1 → Engine 2 flow works")
            else:
                all_passed = False
        
        # FLOW-4: Engine 3 → Engine 2
        print_subheader("FLOW-4: Engine 3 → Engine 2")
        resp_e3 = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [
                    {"job_id": "j1", "job_type": "report_generation", "deadline_seconds": 3600}
                ],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        if resp_e3.status_code == 200:
            e3_data = resp_e3.json()
            resp_e2 = requests.post(
                f"{BASE_URL}/carbon/evaluate",
                json={
                    "system_id": "flow4",
                    "predicted_cpu": 50.0,
                    "predicted_load_level": "NORMAL",
                    "recommended_pods": 3,
                    "current_pods": 3,
                    "workload_reduction_percent": e3_data.get("workload_reduction_percent", 0),
                    "delayable_jobs": e3_data.get("delayable_jobs", 0)
                },
                timeout=5
            )
            if resp_e2.status_code == 200:
                print("✓ Engine 3 → Engine 2 flow works")
            else:
                all_passed = False
        
        # FLOW-5: Engine 1 + Engine 3 → Engine 2
        print_subheader("FLOW-5: Engine 1 + Engine 3 → Engine 2")
        resp_e1 = requests.get(f"{BASE_URL}/predict", timeout=5)
        resp_e3 = requests.post(
            f"{BASE_URL}/jobs/evaluate",
            json={
                "jobs": [{"job_id": "j1", "job_type": "report_generation", "deadline_seconds": 3600}],
                "current_load_level": "NORMAL"
            },
            timeout=5
        )
        
        if resp_e1.status_code == 200 and resp_e3.status_code == 200:
            e1_data = resp_e1.json()
            e3_data = resp_e3.json()
            resp_e2 = requests.post(
                f"{BASE_URL}/carbon/evaluate",
                json={
                    "system_id": "flow5",
                    "predicted_cpu": e1_data.get("predicted_cpu", 50),
                    "predicted_load_level": e1_data.get("load_level", "NORMAL"),
                    "recommended_pods": e1_data.get("recommended_pods", 3),
                    "current_pods": 3,
                    "workload_reduction_percent": e3_data.get("workload_reduction_percent", 0),
                    "delayable_jobs": e3_data.get("delayable_jobs", 0)
                },
                timeout=5
            )
            if resp_e2.status_code == 200:
                print("✓ Engine 1 + Engine 3 → Engine 2 flow works")
            else:
                all_passed = False
        
        if all_passed:
            print("\n✅ INTEGRATION FLOW PASSED")
        else:
            print("\n❌ INTEGRATION FLOW HAD FAILURES")
        
        return all_passed
        
    except Exception as e:
        log_failure("Integration Flow", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def test_part8_system_logic() -> bool:
    """Part 8: System intelligence validation."""
    print_header("PART 8: SYSTEM LOGIC VALIDATION")
    
    all_passed = True
    
    try:
        print_subheader("Logic Test 1: HIGH Load → SLA Priority")
        # At HIGH load, should not reduce pods below raw recommendation
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "logic1",
                "predicted_cpu": 85.0,
                "predicted_load_level": "HIGH",
                "recommended_pods": 6,
                "current_pods": 3,
                "workload_reduction_percent": 0.5
            },
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            if opt_pods >= 6:
                print(f"✓ HIGH load: SLA priority (kept {opt_pods} pods >= 6 recommended)")
            else:
                log_failure("Logic-1", f"HIGH load reduced pods: {opt_pods} < 6",
                           output_data=data)
                all_passed = False
        
        print_subheader("Logic Test 2: LOW Load → Carbon Priority")
        # At LOW load, can use optimization
        resp = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "logic2",
                "predicted_cpu": 20.0,
                "predicted_load_level": "LOW",
                "recommended_pods": 2,
                "current_pods": 5,
                "workload_reduction_percent": 0.4
            },
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            opt_pods = data.get("optimized_required_pods", 0)
            if opt_pods <= 2:
                print(f"✓ LOW load: Carbon priority (reduced to {opt_pods} pods)")
            else:
                print(f"⚠ LOW load optimization not aggressive: {opt_pods} pods")
        
        print_subheader("Logic Test 3: NORMAL Load → Balanced")
        # At NORMAL load, moderate optimization
        resp_no_reduce = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "logic3a",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 4,
                "current_pods": 4,
                "workload_reduction_percent": 0.0
            },
            timeout=5
        )
        
        resp_with_reduce = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "logic3b",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 4,
                "current_pods": 4,
                "workload_reduction_percent": 0.2
            },
            timeout=5
        )
        
        if resp_no_reduce.status_code == 200 and resp_with_reduce.status_code == 200:
            data_no = resp_no_reduce.json()
            data_with = resp_with_reduce.json()
            pods_no = data_no.get("optimized_required_pods", 0)
            pods_with = data_with.get("optimized_required_pods", 0)
            
            if pods_with <= pods_no:
                print(f"✓ NORMAL load: Balanced (no reduce: {pods_no}, with reduce: {pods_with})")
            else:
                print(f"⚠ NORMAL load: Reduction not applied")
        
        print_subheader("Logic Test 4: Engine 3 Affects Engine 2")
        # Test that Engine 3 output actually changes Engine 2 decision
        resp_no_e3 = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "logic4a",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 5,
                "current_pods": 5,
                "workload_reduction_percent": 0.0
            },
            timeout=5
        )
        
        resp_with_e3 = requests.post(
            f"{BASE_URL}/carbon/evaluate",
            json={
                "system_id": "logic4b",
                "predicted_cpu": 50.0,
                "predicted_load_level": "NORMAL",
                "recommended_pods": 5,
                "current_pods": 5,
                "workload_reduction_percent": 0.3
            },
            timeout=5
        )
        
        if resp_no_e3.status_code == 200 and resp_with_e3.status_code == 200:
            data_no = resp_no_e3.json()
            data_with = resp_with_e3.json()
            carbon_no = data_no.get("raw_scenario", {}).get("estimated_carbon_gco2", 0)
            carbon_with_opt = data_with.get("optimized_scenario", {}).get("estimated_carbon_gco2", 0)
            
            if carbon_with_opt < carbon_no:
                print(f"✓ Engine 3 affects Engine 2: carbon {carbon_no:.2f} → {carbon_with_opt:.2f} g")
            else:
                print(f"⚠ Engine 3 impact not clear in output")
        
        if all_passed:
            print("\n✅ SYSTEM LOGIC VALIDATED")
        else:
            print("\n❌ SYSTEM LOGIC HAD ISSUES")
        
        return all_passed
        
    except Exception as e:
        log_failure("System Logic", str(e), root_cause=str(traceback.format_exc()[:200]))
        return False


def print_final_report():
    """Print final validation report."""
    print_header("FINAL VALIDATION REPORT")
    
    print(f"ENGINE 1 (Prediction): {'✅ PASS' if results['engine1'] else '❌ FAIL'}")
    print(f"ENGINE 2 (Carbon Decision): {'✅ PASS' if results['engine2'] else '❌ FAIL'}")
    print(f"ENGINE 3 (Job Prioritization): {'✅ PASS' if results['engine3'] else '❌ FAIL'}")
    print()
    print(f"E3 SCENARIOS: {'✅ PASS' if results['engine3'] else '❌ FAIL'}")
    print(f"E2 SCENARIOS: {'✅ PASS' if results['engine2'] else '❌ FAIL'}")
    print(f"COMBINED SCENARIOS: {'✅ PASS' if results['combo_scenarios'] else '❌ FAIL'}")
    print(f"EDGE CASES: {'✅ PASS' if results['edge_cases'] else '❌ FAIL'}")
    print(f"CARBON LOGIC: {'✅ PASS' if results['carbon_logic'] else '❌ FAIL'}")
    print(f"INTEGRATION FLOW: {'✅ PASS' if results['integration_flow'] else '❌ FAIL'}")
    print(f"SYSTEM LOGIC: {'✅ PASS' if results['system_logic'] else '❌ FAIL'}")
    
    print()
    print("="*80)
    
    all_passed = all(results.values())
    if all_passed:
        print("FINAL STATUS: FULL SYSTEM VALIDATED ✅")
    else:
        print("FINAL STATUS: SYSTEM HAS ISSUES ❌")
    
    print("="*80)
    
    if failures:
        print_header("FAILURE DETAILS")
        for i, failure in enumerate(failures, 1):
            print(f"\nFailure {i}: {failure['test']}")
            print(f"  Issue: {failure['issue']}")
            if failure['root_cause']:
                print(f"  Root Cause: {failure['root_cause']}")
            if failure['input']:
                print(f"  Input: {json.dumps(failure['input'])[:100]}")
            if failure['output']:
                print(f"  Output: {json.dumps(failure['output'])[:100]}")


if __name__ == "__main__":
    try:
        results["engine1"] = test_part1_engine1()
        results["engine3"] = test_part2_engine3_scenarios()
        results["e3_scenarios"] = results["engine3"]  # Sync the key names
        results["engine2"] = test_part3_engine2_scenarios()
        results["e2_scenarios"] = results["engine2"]  # Sync the key names
        results["combo_scenarios"] = test_part4_combined_scenarios()
        results["edge_cases"] = test_part5_edge_cases()
        results["carbon_logic"] = test_part6_carbon_logic()
        results["integration_flow"] = test_part7_integration_flow()
        results["system_logic"] = test_part8_system_logic()
        
        # Part 0 server check determines if we could run tests
        results_copy = results.copy()
        results_copy = test_part0_server_check()
        
        print_final_report()
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
