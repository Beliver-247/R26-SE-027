"""
Green DevOps System - Full Integration Test
Demonstrates all engines and decision layer working together
"""

import json
import requests
import time

BASE_URL = "http://localhost:5000"

def test_scenario(name, description, predicted_cpu, load_level, current_pods):
    """Test a complete scenario through all engines"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {name}")
    print(f"{'='*80}")
    print(f"Description: {description}")
    print(f"Predicted CPU: {predicted_cpu}%")
    print(f"Load Level: {load_level}")
    print(f"Current Pods: {current_pods}")
    
    # Step 1: Get prediction (this will override CPU but shows Engine 1)
    print(f"\n[1] ENGINE 1 - WORKLOAD PREDICTION")
    resp = requests.get(f"{BASE_URL}/predict")
    if resp.status_code != 200:
        print(f"❌ FAILED: {resp.text}")
        return False
    
    pred = resp.json()["prediction"]
    print(f"✅ Predicted CPU: {pred['predicted_cpu']:.2f}%")
    print(f"✅ Load Level: {pred['predicted_load_level']}")
    print(f"✅ Recommended Pods: {pred['recommended_pods']}")
    print(f"✅ Confidence: {pred['confidence']:.2%}")
    
    # Use our test values for decision scenario
    test_pods = max(1, predicted_cpu // 20)
    
    # Step 2: Test Engine 3 (Jobs)
    print(f"\n[2] ENGINE 3 - JOB SCHEDULING")
    jobs_payload = {
        "jobs": [
            {"job_id": "job_1", "job_type": "report", "priority": "LOW", "estimated_cpu_percent": 10, "deadline_seconds": 3600},
            {"job_id": "job_2", "job_type": "payment", "priority": "HIGH", "estimated_cpu_percent": 20, "deadline_seconds": 10},
            {"job_id": "job_3", "job_type": "analytics", "priority": "LOW", "estimated_cpu_percent": 15, "deadline_seconds": 1800},
        ]
    }
    
    resp = requests.post(f"{BASE_URL}/jobs/evaluate", json=jobs_payload)
    if resp.status_code != 200:
        print(f"❌ FAILED: {resp.text}")
        return False
    
    jobs = resp.json()
    print(f"✅ Delayable Jobs: {jobs['delayable_jobs']}")
    print(f"✅ Workload Reduction: {jobs['workload_reduction_percent']:.1%}")
    print(f"✅ Reason: {jobs['reason']}")
    
    # Step 3: Test Engine 2 (Carbon)
    print(f"\n[3] ENGINE 2 - CARBON OPTIMIZATION")
    carbon_payload = {
        "system_id": "test-system",
        "predicted_cpu": predicted_cpu,
        "predicted_load_level": load_level,
        "recommended_pods": test_pods,
        "raw_required_pods": test_pods,
        "current_pods": current_pods,
        "prediction_window_seconds": 30,
        "delayable_jobs": jobs["delayable_jobs"],
        "workload_reduction_percent": jobs["workload_reduction_percent"]
    }
    
    resp = requests.post(f"{BASE_URL}/carbon/evaluate", json=carbon_payload)
    if resp.status_code != 200:
        print(f"❌ FAILED: {resp.text}")
        return False
    
    carbon = resp.json()
    print(f"✅ Raw Scenario Pods: {carbon['raw_scenario']['required_pods']}")
    print(f"✅ Raw Carbon: {carbon['raw_scenario']['estimated_carbon_gco2']:.2f}g CO2")
    if carbon["optimized_scenario"]:
        print(f"✅ Optimized Pods: {carbon['optimized_scenario']['required_pods']}")
        print(f"✅ Optimized Carbon: {carbon['optimized_scenario']['estimated_carbon_gco2']:.2f}g CO2")
    print(f"✅ Recommended Action: {carbon['recommended_action']}")
    print(f"✅ SLA Protected: {carbon['metadata']['sla_protected']}")
    
    # Step 4: Test Decision Layer
    print(f"\n[4] DECISION LAYER - ORCHESTRATION")
    decision_payload = {
        "system_id": "test-system",
        "engine1_output": {
            "system_id": "test-system",
            "prediction": {
                "predicted_cpu": predicted_cpu,
                "predicted_load_level": load_level,
                "recommended_pods": test_pods,
                "confidence": 0.95
            }
        },
        "engine2_output": {
            "raw_scenario": carbon["raw_scenario"],
            "optimized_scenario": carbon["optimized_scenario"],
            "recommended_action": carbon["recommended_action"],
            "optimized_required_pods": carbon.get("optimized_required_pods", test_pods),
            "carbon_saving_gco2": carbon["carbon_saving_gco2"],
            "carbon_saving_percent": carbon["carbon_saving_percent"],
            "reason": carbon["reason"],
            "metadata": carbon["metadata"]
        },
        "engine3_output": {
            "delayable_jobs": jobs["delayable_jobs"],
            "delayable_job_ids": jobs["delayable_job_ids"],
            "workload_reduction_percent": jobs["workload_reduction_percent"],
            "reason": jobs["reason"]
        },
        "current_pods": current_pods
    }
    
    resp = requests.post(f"{BASE_URL}/decision/evaluate", json=decision_payload)
    if resp.status_code != 200:
        print(f"❌ FAILED: {resp.text}")
        return False
    
    decision = resp.json()["decision"]
    print(f"✅ Final Action: {decision['final_action']}")
    print(f"✅ Final Pods: {decision['final_required_pods']}")
    delay_count = len(decision.get('jobs_to_delay', []))
    print(f"✅ Jobs to Delay: {delay_count}")
    print(f"✅ Carbon Savings: {decision['carbon_saving_gco2']:.2f}g CO2 ({decision['carbon_saving_percent']:.1f}%)")
    print(f"✅ SLA Preserved: {decision['sla_preserved']}")
    
    reasoning = resp.json().get("reasoning", {})
    print(f"✅ Reasoning: {reasoning.get('reason', 'N/A')}")
    
    return True

# Run test scenarios
print("\n")
print("█" * 80)
print("  GREEN DEVOPS SYSTEM - FULL INTEGRATION DEMONSTRATION")
print("█" * 80)

results = {}

# Scenario 1: HIGH LOAD
results["HIGH LOAD"] = test_scenario(
    "HIGH LOAD - SLA PROTECTION",
    "High CPU demand → SLA protection priority",
    predicted_cpu=85,
    load_level="HIGH",
    current_pods=2
)

# Scenario 2: NORMAL LOAD
results["NORMAL LOAD"] = test_scenario(
    "NORMAL LOAD - HYBRID DECISION",
    "Moderate CPU demand → balanced SLA and efficiency",
    predicted_cpu=55,
    load_level="NORMAL",
    current_pods=3
)

# Scenario 3: LOW LOAD
results["LOW LOAD"] = test_scenario(
    "LOW LOAD - SCALE DOWN",
    "Low CPU demand → carbon optimization priority",
    predicted_cpu=25,
    load_level="LOW",
    current_pods=4
)

# Summary
print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"HIGH LOAD Scenario:    {'✅ PASS' if results['HIGH LOAD'] else '❌ FAIL'}")
print(f"NORMAL LOAD Scenario:  {'✅ PASS' if results['NORMAL LOAD'] else '❌ FAIL'}")
print(f"LOW LOAD Scenario:     {'✅ PASS' if results['LOW LOAD'] else '❌ FAIL'}")

all_pass = all(results.values())
print(f"\n{'='*80}")
if all_pass:
    print("LIVE DEMO FLOW: ✅ PASS")
    print("SYSTEM READY FOR PP1 DEMO ✅")
else:
    print("LIVE DEMO FLOW: ❌ FAIL")
print(f"{'='*80}\n")
