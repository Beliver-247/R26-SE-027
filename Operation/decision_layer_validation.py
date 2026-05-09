"""
Decision Layer Validation Test Suite

Tests all decision scenarios:
- Scenario A: HIGH load + delayable jobs
- Scenario B: HIGH load + no delayable jobs
- Scenario C: NORMAL load + optimized scenario available
- Scenario D: LOW load + strong optimization
- Scenario E: No optimized scenario
- Scenario F: Missing Engine 3 data
"""

import json
from src.decision_layer import DecisionOrchestrator, DecisionContext

def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_test(scenario: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {scenario}")
    if details:
        print(f"     {details}")

# Initialize orchestrator
orchestrator = DecisionOrchestrator()

# Track results
all_passed = True
test_results = []

print_header("DECISION LAYER VALIDATION TEST SUITE")

# ==================== SCENARIO A: HIGH LOAD + DELAYABLE JOBS ====================

print_header("SCENARIO A: HIGH LOAD + DELAYABLE JOBS")

scenario_a_engine1 = {
    "system_id": "api-service",
    "prediction": {
        "predicted_cpu": 85.0,
        "predicted_load_level": "HIGH",
        "recommended_pods": 5,
        "confidence": 0.95
    }
}

scenario_a_engine2 = {
    "raw_scenario": {"required_pods": 5, "estimated_carbon_gco2": 8.33},
    "optimized_scenario": {"required_pods": 3, "estimated_carbon_gco2": 5.0},
    "recommended_action": "hybrid",
    "optimized_required_pods": 3,
    "carbon_saving_gco2": 3.33,
    "carbon_saving_percent": 40.0,
    "reason": "Optimization available",
    "metadata": {"sla_protected": True}
}

scenario_a_engine3 = {
    "delayable_jobs": 4,
    "delayable_job_ids": ["job_101", "job_102", "job_103", "job_104"],
    "workload_reduction_percent": 0.4,
    "reason": "4 LOW priority jobs can be delayed"
}

try:
    decision_a = orchestrator.evaluate(
        engine1_output=scenario_a_engine1,
        engine2_output=scenario_a_engine2,
        engine3_output=scenario_a_engine3,
        current_pods=3
    )
    
    # Validate expectations
    test_a1 = decision_a.final_required_pods >= scenario_a_engine2["raw_scenario"]["required_pods"]
    print_test(
        "A1: SLA preserved (final_pods >= raw_pods)",
        test_a1,
        f"final={decision_a.final_required_pods} >= raw={scenario_a_engine2['raw_scenario']['required_pods']}"
    )
    all_passed = all_passed and test_a1
    
    test_a2 = decision_a.sla_preserved == True
    print_test("A2: SLA flag is True", test_a2)
    all_passed = all_passed and test_a2
    
    test_a3 = decision_a.final_action in ["delay_jobs", "scale_up", "no_action"]
    print_test(
        "A3: Action is HIGH load safe",
        test_a3,
        f"action={decision_a.final_action}"
    )
    all_passed = all_passed and test_a3
    
    test_result = {
        "scenario": "A: HIGH + delayable",
        "passed": test_a1 and test_a2 and test_a3,
        "action": decision_a.final_action,
        "pods": decision_a.final_required_pods
    }
    test_results.append(test_result)
    
except Exception as e:
    print(f"❌ SCENARIO A FAILED: {e}")
    all_passed = False
    test_results.append({"scenario": "A: HIGH + delayable", "passed": False, "error": str(e)})

# ==================== SCENARIO B: HIGH LOAD + NO DELAYABLE JOBS ====================

print_header("SCENARIO B: HIGH LOAD + NO DELAYABLE JOBS")

scenario_b_engine1 = scenario_a_engine1  # Same HIGH load

scenario_b_engine2 = scenario_a_engine2

scenario_b_engine3 = {
    "delayable_jobs": 0,
    "delayable_job_ids": [],
    "workload_reduction_percent": 0.0,
    "reason": "All jobs are HIGH priority"
}

try:
    decision_b = orchestrator.evaluate(
        engine1_output=scenario_b_engine1,
        engine2_output=scenario_b_engine2,
        engine3_output=scenario_b_engine3,
        current_pods=3
    )
    
    # Validate expectations
    test_b1 = decision_b.delay_job_count == 0
    print_test("B1: No jobs delayed", test_b1)
    all_passed = all_passed and test_b1
    
    test_b2 = decision_b.final_required_pods >= scenario_b_engine2["raw_scenario"]["required_pods"]
    print_test(
        "B2: Safe pod count",
        test_b2,
        f"final={decision_b.final_required_pods} >= raw={scenario_b_engine2['raw_scenario']['required_pods']}"
    )
    all_passed = all_passed and test_b2
    
    test_b3 = decision_b.sla_preserved == True
    print_test("B3: SLA protected", test_b3)
    all_passed = all_passed and test_b3
    
    test_result = {
        "scenario": "B: HIGH + no delayable",
        "passed": test_b1 and test_b2 and test_b3,
        "action": decision_b.final_action,
        "pods": decision_b.final_required_pods
    }
    test_results.append(test_result)
    
except Exception as e:
    print(f"❌ SCENARIO B FAILED: {e}")
    all_passed = False
    test_results.append({"scenario": "B: HIGH + no delayable", "passed": False, "error": str(e)})

# ==================== SCENARIO C: NORMAL LOAD + OPTIMIZED SCENARIO ====================

print_header("SCENARIO C: NORMAL LOAD + OPTIMIZED SCENARIO")

scenario_c_engine1 = {
    "system_id": "web-service",
    "prediction": {
        "predicted_cpu": 55.0,
        "predicted_load_level": "NORMAL",
        "recommended_pods": 4,
        "confidence": 0.90
    }
}

scenario_c_engine2 = {
    "raw_scenario": {"required_pods": 4, "estimated_carbon_gco2": 6.67},
    "optimized_scenario": {"required_pods": 2, "estimated_carbon_gco2": 3.33},
    "recommended_action": "hybrid",
    "optimized_required_pods": 2,
    "carbon_saving_gco2": 3.34,
    "carbon_saving_percent": 50.0,
    "reason": "Strong optimization opportunity",
    "metadata": {"sla_protected": False}
}

scenario_c_engine3 = {
    "delayable_jobs": 3,
    "delayable_job_ids": ["job_201", "job_202", "job_203"],
    "workload_reduction_percent": 0.5,
    "reason": "3 LOW priority jobs delayable"
}

try:
    decision_c = orchestrator.evaluate(
        engine1_output=scenario_c_engine1,
        engine2_output=scenario_c_engine2,
        engine3_output=scenario_c_engine3,
        current_pods=4
    )
    
    # Validate expectations
    test_c1 = decision_c.final_action in ["hybrid", "scale_down"]
    print_test(
        "C1: Action allows optimization",
        test_c1,
        f"action={decision_c.final_action}"
    )
    all_passed = all_passed and test_c1
    
    test_c2 = decision_c.final_required_pods <= scenario_c_engine2["raw_scenario"]["required_pods"]
    print_test(
        "C2: Optimization applied",
        test_c2,
        f"final={decision_c.final_required_pods} <= raw={scenario_c_engine2['raw_scenario']['required_pods']}"
    )
    all_passed = all_passed and test_c2
    
    test_c3 = decision_c.carbon_saving_gco2 > 0
    print_test(
        "C3: Carbon savings recorded",
        test_c3,
        f"saved={decision_c.carbon_saving_gco2:.2f}g CO2"
    )
    all_passed = all_passed and test_c3
    
    test_result = {
        "scenario": "C: NORMAL + optimized",
        "passed": test_c1 and test_c2 and test_c3,
        "action": decision_c.final_action,
        "pods": decision_c.final_required_pods,
        "carbon_saved": decision_c.carbon_saving_gco2
    }
    test_results.append(test_result)
    
except Exception as e:
    print(f"❌ SCENARIO C FAILED: {e}")
    all_passed = False
    test_results.append({"scenario": "C: NORMAL + optimized", "passed": False, "error": str(e)})

# ==================== SCENARIO D: LOW LOAD + STRONG OPTIMIZATION ====================

print_header("SCENARIO D: LOW LOAD + STRONG OPTIMIZATION")

scenario_d_engine1 = {
    "system_id": "batch-processor",
    "prediction": {
        "predicted_cpu": 20.0,
        "predicted_load_level": "LOW",
        "recommended_pods": 1,
        "confidence": 0.88
    }
}

scenario_d_engine2 = {
    "raw_scenario": {"required_pods": 1, "estimated_carbon_gco2": 1.67},
    "optimized_scenario": {"required_pods": 1, "estimated_carbon_gco2": 1.67},
    "recommended_action": "scale_down",
    "optimized_required_pods": 1,
    "carbon_saving_gco2": 0.0,
    "carbon_saving_percent": 0.0,
    "reason": "Already at minimum",
    "metadata": {"sla_protected": False}
}

scenario_d_engine3 = {
    "delayable_jobs": 10,
    "delayable_job_ids": ["job_301", "job_302", "job_303", "job_304", "job_305"],
    "workload_reduction_percent": 0.6,
    "reason": "10 delayable LOW priority jobs"
}

try:
    decision_d = orchestrator.evaluate(
        engine1_output=scenario_d_engine1,
        engine2_output=scenario_d_engine2,
        engine3_output=scenario_d_engine3,
        current_pods=2
    )
    
    # Validate expectations
    test_d1 = decision_d.final_action in ["scale_down", "hybrid", "delay_jobs"]
    print_test(
        "D1: Action allows LOW load optimization",
        test_d1,
        f"action={decision_d.final_action}"
    )
    all_passed = all_passed and test_d1
    
    test_d2 = decision_d.final_required_pods <= decision_d.input_current_pods
    print_test(
        "D2: Scales down or maintains",
        test_d2,
        f"final={decision_d.final_required_pods}, current={decision_d.input_current_pods}"
    )
    all_passed = all_passed and test_d2
    
    test_d3 = decision_d.sla_preserved == True  # LOW load still preserves SLA
    print_test("D3: SLA preserved", test_d3)
    all_passed = all_passed and test_d3
    
    test_result = {
        "scenario": "D: LOW + strong",
        "passed": test_d1 and test_d2 and test_d3,
        "action": decision_d.final_action,
        "pods": decision_d.final_required_pods
    }
    test_results.append(test_result)
    
except Exception as e:
    print(f"❌ SCENARIO D FAILED: {e}")
    all_passed = False
    test_results.append({"scenario": "D: LOW + strong", "passed": False, "error": str(e)})

# ==================== SCENARIO E: NO OPTIMIZED SCENARIO ====================

print_header("SCENARIO E: NO OPTIMIZED SCENARIO")

scenario_e_engine1 = {
    "system_id": "critical-service",
    "prediction": {
        "predicted_cpu": 75.0,
        "predicted_load_level": "HIGH",
        "recommended_pods": 6,
        "confidence": 0.92
    }
}

scenario_e_engine2 = {
    "raw_scenario": {"required_pods": 6, "estimated_carbon_gco2": 10.0},
    "optimized_scenario": None,  # No optimization available
    "recommended_action": "scale_up",
    "optimized_required_pods": 6,
    "carbon_saving_gco2": 0.0,
    "carbon_saving_percent": 0.0,
    "reason": "No optimization possible",
    "metadata": {"sla_protected": True}
}

scenario_e_engine3 = None  # No Engine 3 data

try:
    decision_e = orchestrator.evaluate(
        engine1_output=scenario_e_engine1,
        engine2_output=scenario_e_engine2,
        engine3_output=scenario_e_engine3,
        current_pods=4
    )
    
    # Validate expectations
    test_e1 = decision_e.had_engine3_data == False
    print_test("E1: Engine 3 data correctly marked absent", test_e1)
    all_passed = all_passed and test_e1
    
    test_e2 = decision_e.final_required_pods >= scenario_e_engine2["raw_scenario"]["required_pods"]
    print_test(
        "E2: Falls back to raw scenario",
        test_e2,
        f"final={decision_e.final_required_pods} >= raw={scenario_e_engine2['raw_scenario']['required_pods']}"
    )
    all_passed = all_passed and test_e2
    
    test_e3 = decision_e.carbon_saving_gco2 == 0.0
    print_test("E3: No carbon savings (no optimization)", test_e3)
    all_passed = all_passed and test_e3
    
    test_result = {
        "scenario": "E: No optimized",
        "passed": test_e1 and test_e2 and test_e3,
        "action": decision_e.final_action,
        "pods": decision_e.final_required_pods
    }
    test_results.append(test_result)
    
except Exception as e:
    print(f"❌ SCENARIO E FAILED: {e}")
    all_passed = False
    test_results.append({"scenario": "E: No optimized", "passed": False, "error": str(e)})

# ==================== SCENARIO F: MISSING ENGINE 3 DATA ====================

print_header("SCENARIO F: MISSING ENGINE 3 DATA")

scenario_f_engine1 = scenario_c_engine1
scenario_f_engine2 = scenario_c_engine2
scenario_f_engine3 = None  # Missing Engine 3 data

try:
    decision_f = orchestrator.evaluate(
        engine1_output=scenario_f_engine1,
        engine2_output=scenario_f_engine2,
        engine3_output=scenario_f_engine3,
        current_pods=4
    )
    
    # Validate expectations
    test_f1 = decision_f.had_engine3_data == False
    print_test("F1: Missing E3 detected correctly", test_f1)
    all_passed = all_passed and test_f1
    
    test_f2 = decision_f.delay_job_count == 0
    print_test("F2: No jobs delayed (E3 missing)", test_f2)
    all_passed = all_passed and test_f2
    
    test_f3 = decision_f.final_required_pods is not None
    print_test(
        "F3: Decision still produced",
        test_f3,
        f"action={decision_f.final_action}, pods={decision_f.final_required_pods}"
    )
    all_passed = all_passed and test_f3
    
    test_result = {
        "scenario": "F: Missing E3",
        "passed": test_f1 and test_f2 and test_f3,
        "action": decision_f.final_action,
        "pods": decision_f.final_required_pods
    }
    test_results.append(test_result)
    
except Exception as e:
    print(f"❌ SCENARIO F FAILED: {e}")
    all_passed = False
    test_results.append({"scenario": "F: Missing E3", "passed": False, "error": str(e)})

# ==================== SUMMARY ====================

print_header("VALIDATION RESULTS SUMMARY")

for result in test_results:
    status = "✅ PASS" if result["passed"] else "❌ FAIL"
    print(f"{status}: {result['scenario']}")
    if "action" in result:
        print(f"    Action: {result['action']}, Pods: {result['pods']}")
    if "error" in result:
        print(f"    Error: {result['error']}")

print_header("FINAL VALIDATION STATUS")

print("DECISION LAYER INPUT MERGE:", "✅ PASS" if all_passed else "❌ FAIL")
print("DECISION RULES:", "✅ PASS" if all_passed else "❌ FAIL")
print("HIGH LOAD PROTECTION:", "✅ PASS" if all([r["passed"] for r in test_results if "HIGH" in r.get("scenario", "")]) else "❌ FAIL")
print("LOW/NORMAL LOAD OPTIMIZATION:", "✅ PASS" if all([r["passed"] for r in test_results if "NORMAL" in r.get("scenario", "") or "LOW" in r.get("scenario", "")]) else "❌ FAIL")
print("MISSING DATA HANDLING:", "✅ PASS" if test_results[-1]["passed"] else "❌ FAIL")
print("VALIDATION:", "✅ PASS" if all_passed else "❌ FAIL")

print("\n" + "="*80)
if all_passed:
    print("FINAL STATUS: DECISION LAYER IMPLEMENTATION COMPLETE ✅")
else:
    print("FINAL STATUS: DECISION LAYER IMPLEMENTATION INCOMPLETE ❌")
print("="*80 + "\n")
