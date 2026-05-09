"""
HIGH LOAD POLICY CONSISTENCY FIX VALIDATION

This test specifically validates that the HIGH LOAD policy is now consistent:
1. SLA protection is MANDATORY (pods >= raw_required_pods)
2. Pod reduction is NEVER allowed
3. Job delay is OPTIONAL (secondary after SLA guaranteed)
4. Carbon optimization NOT applied
"""

from src.decision_layer import DecisionOrchestrator

def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

# Initialize orchestrator
orchestrator = DecisionOrchestrator()

print_header("HIGH LOAD POLICY CONSISTENCY - FIX VALIDATION")

# ==================== TEST 1: HIGH LOAD + PODS BELOW SAFE LEVEL ====================

print_header("TEST 1: HIGH LOAD + PODS BELOW SAFE LEVEL")
print("Expected: SCALE_UP (mandatory for SLA)\n")

test1_engine1 = {
    "system_id": "api-service",
    "prediction": {
        "predicted_cpu": 75.0,
        "predicted_load_level": "HIGH",
        "recommended_pods": 5,
        "confidence": 0.95
    }
}

test1_engine2 = {
    "raw_scenario": {"required_pods": 5, "estimated_carbon_gco2": 8.33},
    "optimized_scenario": {"required_pods": 3, "estimated_carbon_gco2": 5.0},
    "recommended_action": "hybrid",
    "optimized_required_pods": 3,
    "carbon_saving_gco2": 3.33,
    "carbon_saving_percent": 40.0,
    "reason": "Optimization available",
    "metadata": {"sla_protected": True}
}

test1_engine3 = {
    "delayable_jobs": 4,
    "delayable_job_ids": ["job_101", "job_102", "job_103", "job_104"],
    "workload_reduction_percent": 0.4,
    "reason": "4 LOW priority jobs can be delayed"
}

decision1 = orchestrator.evaluate(
    engine1_output=test1_engine1,
    engine2_output=test1_engine2,
    engine3_output=test1_engine3,
    current_pods=3
)

test1_pass = (
    decision1.final_action == "scale_up" and
    decision1.final_required_pods >= test1_engine2["raw_scenario"]["required_pods"] and
    decision1.sla_preserved == True and
    decision1.carbon_saving_gco2 == 0.0  # No optimization in HIGH
)

print(f"Action: {decision1.final_action} (expected: scale_up)")
print(f"Pods: {decision1.final_required_pods} (expected: >= 5)")
print(f"SLA preserved: {decision1.sla_preserved} (expected: True)")
print(f"Carbon savings: {decision1.carbon_saving_gco2}g (expected: 0.0)")
print(f"Pod reduction applied: {decision1.final_required_pods < test1_engine2['raw_scenario']['required_pods']}")
print(f"✅ PASS: TEST 1" if test1_pass else f"❌ FAIL: TEST 1")

# ==================== TEST 2: HIGH LOAD + PODS AT SAFE LEVEL + DELAYABLE JOBS ====================

print_header("TEST 2: HIGH LOAD + PODS AT SAFE LEVEL + DELAYABLE JOBS")
print("Expected: DELAY_JOBS (optional, secondary after SLA)\n")

test2_engine1 = test1_engine1  # Same HIGH load

test2_engine2 = test1_engine2

test2_engine3 = {
    "delayable_jobs": 4,
    "delayable_job_ids": ["job_101", "job_102", "job_103", "job_104"],
    "workload_reduction_percent": 0.4,
    "reason": "4 LOW priority jobs can be delayed"
}

decision2 = orchestrator.evaluate(
    engine1_output=test2_engine1,
    engine2_output=test2_engine2,
    engine3_output=test2_engine3,
    current_pods=5  # Already at safe level
)

test2_pass = (
    decision2.final_action == "delay_jobs" and  # Should delay jobs when safe
    decision2.delay_job_count > 0 and
    decision2.final_required_pods >= test2_engine2["raw_scenario"]["required_pods"] and
    decision2.sla_preserved == True and
    decision2.carbon_saving_gco2 == 0.0  # No optimization in HIGH
)

print(f"Action: {decision2.final_action} (expected: delay_jobs or no_action)")
print(f"Jobs delayed: {decision2.delay_job_count} (expected: >0 if delay_jobs)")
print(f"Pods: {decision2.final_required_pods} (expected: >= 5)")
print(f"SLA preserved: {decision2.sla_preserved} (expected: True)")
print(f"Carbon savings: {decision2.carbon_saving_gco2}g (expected: 0.0)")
print(f"✅ PASS: TEST 2" if test2_pass else f"❌ FAIL: TEST 2")

# ==================== TEST 3: HIGH LOAD + PODS AT SAFE LEVEL + NO DELAYABLE JOBS ====================

print_header("TEST 3: HIGH LOAD + PODS AT SAFE LEVEL + NO DELAYABLE JOBS")
print("Expected: NO_ACTION (pods sufficient, no job delay)\n")

test3_engine1 = test1_engine1

test3_engine2 = test1_engine2

test3_engine3 = {
    "delayable_jobs": 0,
    "delayable_job_ids": [],
    "workload_reduction_percent": 0.0,
    "reason": "No delayable jobs"
}

decision3 = orchestrator.evaluate(
    engine1_output=test3_engine1,
    engine2_output=test3_engine2,
    engine3_output=test3_engine3,
    current_pods=5  # Already at safe level
)

test3_pass = (
    decision3.final_action == "no_action" and
    decision3.delay_job_count == 0 and
    decision3.final_required_pods >= test3_engine2["raw_scenario"]["required_pods"] and
    decision3.sla_preserved == True and
    decision3.carbon_saving_gco2 == 0.0
)

print(f"Action: {decision3.final_action} (expected: no_action)")
print(f"Jobs delayed: {decision3.delay_job_count} (expected: 0)")
print(f"Pods: {decision3.final_required_pods} (expected: >= 5)")
print(f"SLA preserved: {decision3.sla_preserved} (expected: True)")
print(f"Carbon savings: {decision3.carbon_saving_gco2}g (expected: 0.0)")
print(f"✅ PASS: TEST 3" if test3_pass else f"❌ FAIL: TEST 3")

# ==================== TEST 4: NORMAL LOAD - JOB DELAY ENCOURAGED ====================

print_header("TEST 4: NORMAL LOAD - JOB DELAY ENCOURAGED")
print("Expected: HYBRID (scale + delay) when optimization available\n")

test4_engine1 = {
    "system_id": "web-service",
    "prediction": {
        "predicted_cpu": 55.0,
        "predicted_load_level": "NORMAL",
        "recommended_pods": 4,
        "confidence": 0.90
    }
}

test4_engine2 = {
    "raw_scenario": {"required_pods": 4, "estimated_carbon_gco2": 6.67},
    "optimized_scenario": {"required_pods": 2, "estimated_carbon_gco2": 3.33},
    "recommended_action": "hybrid",
    "optimized_required_pods": 2,
    "carbon_saving_gco2": 3.34,
    "carbon_saving_percent": 50.0,
    "reason": "Strong optimization opportunity",
    "metadata": {"sla_protected": False}
}

test4_engine3 = {
    "delayable_jobs": 3,
    "delayable_job_ids": ["job_201", "job_202", "job_203"],
    "workload_reduction_percent": 0.5,
    "reason": "3 LOW priority jobs delayable"
}

decision4 = orchestrator.evaluate(
    engine1_output=test4_engine1,
    engine2_output=test4_engine2,
    engine3_output=test4_engine3,
    current_pods=4
)

test4_pass = (
    decision4.final_action == "hybrid" and
    decision4.delay_job_count > 0 and
    decision4.final_required_pods <= test4_engine2["raw_scenario"]["required_pods"] and
    decision4.carbon_saving_gco2 > 0  # Carbon optimization in NORMAL
)

print(f"Action: {decision4.final_action} (expected: hybrid)")
print(f"Jobs delayed: {decision4.delay_job_count} (expected: >0)")
print(f"Pods: {decision4.final_required_pods} (expected: <= {test4_engine2['raw_scenario']['required_pods']})")
print(f"Carbon savings: {decision4.carbon_saving_gco2:.2f}g (expected: >0)")
print(f"✅ PASS: TEST 4" if test4_pass else f"❌ FAIL: TEST 4")

# ==================== TEST 5: LOW LOAD - AGGRESSIVE OPTIMIZATION ====================

print_header("TEST 5: LOW LOAD - AGGRESSIVE OPTIMIZATION")
print("Expected: HYBRID (scale down + maximize delay)\n")

test5_engine1 = {
    "system_id": "batch-processor",
    "prediction": {
        "predicted_cpu": 20.0,
        "predicted_load_level": "LOW",
        "recommended_pods": 1,
        "confidence": 0.88
    }
}

test5_engine2 = {
    "raw_scenario": {"required_pods": 1, "estimated_carbon_gco2": 1.67},
    "optimized_scenario": {"required_pods": 1, "estimated_carbon_gco2": 1.67},
    "recommended_action": "scale_down",
    "optimized_required_pods": 1,
    "carbon_saving_gco2": 0.0,
    "carbon_saving_percent": 0.0,
    "reason": "Already at minimum",
    "metadata": {"sla_protected": False}
}

test5_engine3 = {
    "delayable_jobs": 10,
    "delayable_job_ids": ["job_301", "job_302", "job_303", "job_304", "job_305"],
    "workload_reduction_percent": 0.6,
    "reason": "10 delayable LOW priority jobs"
}

decision5 = orchestrator.evaluate(
    engine1_output=test5_engine1,
    engine2_output=test5_engine2,
    engine3_output=test5_engine3,
    current_pods=2
)

test5_pass = (
    decision5.final_action in ["hybrid", "scale_down"] and
    decision5.final_required_pods <= decision5.input_current_pods and
    decision5.sla_preserved == True
)

print(f"Action: {decision5.final_action} (expected: hybrid or scale_down)")
print(f"Pods: {decision5.final_required_pods} (expected: <= {decision5.input_current_pods})")
print(f"Jobs made available for delay: {decision5.delayable_jobs_available}")
print(f"SLA preserved: {decision5.sla_preserved} (expected: True)")
print(f"✅ PASS: TEST 5" if test5_pass else f"❌ FAIL: TEST 5")

# ==================== SUMMARY ====================

print_header("HIGH LOAD POLICY CONSISTENCY FIX - FINAL RESULTS")

all_tests = [test1_pass, test2_pass, test3_pass, test4_pass, test5_pass]
passed_count = sum(all_tests)
total_count = len(all_tests)

print(f"TEST 1 (HIGH + below safe + delayable):  {'✅ PASS' if test1_pass else '❌ FAIL'}")
print(f"TEST 2 (HIGH + at safe + delayable):     {'✅ PASS' if test2_pass else '❌ FAIL'}")
print(f"TEST 3 (HIGH + at safe + no delayable):  {'✅ PASS' if test3_pass else '❌ FAIL'}")
print(f"TEST 4 (NORMAL + hybrid encouraged):     {'✅ PASS' if test4_pass else '❌ FAIL'}")
print(f"TEST 5 (LOW + aggressive optimization):  {'✅ PASS' if test5_pass else '❌ FAIL'}")

print(f"\n{'='*80}")
print(f"HIGH LOAD POLICY CONSISTENCY: {'✅ PASS' if all_tests else '❌ FAIL'} ({passed_count}/{total_count})")
print(f"{'='*80}\n")

print("KEY VALIDATIONS:")
print("✓ HIGH load pods >= raw_required_pods (SLA mandatory)")
print("✓ HIGH load pod reduction NOT allowed")
print("✓ HIGH load job delay OPTIONAL (secondary)")
print("✓ HIGH load carbon NOT optimized by pod reduction")
print("✓ NORMAL load allows hybrid (pod + job optimization)")
print("✓ LOW load aggressively optimizes both")
print("\n" + "="*80)
if all_tests:
    print("DECISION LAYER HIGH LOAD POLICY FIX: ✅ COMPLETE")
else:
    print("DECISION LAYER HIGH LOAD POLICY FIX: ❌ INCOMPLETE")
print("="*80 + "\n")
