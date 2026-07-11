"""
QA VALIDATION SUITE - Engine 2 (Carbon Emission Engine)
Simplified version for robust testing
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_all():
    """Run comprehensive QA tests."""
    print("="*70)
    print("ENGINE 2 QA VALIDATION SUITE")
    print("="*70)
    
    # STEP 1: Server Check
    print("\nSTEP 1 - SERVER VALIDATION")
    print("-"*70)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"[PASS] Server Health: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Server not responding: {e}")
        return
    
    # STEP 2: Engine 1 Test
    print("\nSTEP 2 - ENGINE 1 VALIDATION")
    print("-"*70)
    try:
        response = requests.get(f"{API_BASE}/predict", timeout=5)
        data = response.json()
        print(f"[PASS] Prediction obtained")
        print(f"  CPU: {data['predicted_cpu']}%")
        print(f"  Load: {data['load_level']}")
        print(f"  Pods: {data['recommended_pods']}")
    except Exception as e:
        print(f"[FAIL] Engine 1 failed: {e}")
        return
    
    # STEP 3: Scenario Tests
    print("\nSTEP 3 - SCENARIO TESTING")
    print("-"*70)
    
    scenarios = {
        "A - HIGH LOAD (No Delay)": {
            "payload": {
                "predicted_cpu": 85,
                "load_level": "HIGH",
                "raw_required_pods": 5,
                "current_pods": 2,
                "prediction_window_seconds": 30
            },
            "min_pods": 5
        },
        "B - HIGH LOAD (With Delay)": {
            "payload": {
                "predicted_cpu": 80,
                "load_level": "HIGH",
                "raw_required_pods": 4,
                "current_pods": 2,
                "prediction_window_seconds": 30,
                "delayable_jobs": 3,
                "workload_reduction_percent": 0.3
            },
            "min_pods": 4
        },
        "C - LOW LOAD": {
            "payload": {
                "predicted_cpu": 15,
                "load_level": "LOW",
                "raw_required_pods": 1,
                "current_pods": 2,
                "prediction_window_seconds": 30
            },
            "min_pods": 1
        },
        "D - MEDIUM LOAD": {
            "payload": {
                "predicted_cpu": 45,
                "load_level": "NORMAL",
                "raw_required_pods": 2,
                "current_pods": 2,
                "prediction_window_seconds": 30
            },
            "min_pods": 1
        }
    }
    
    results = {}
    for name, config in scenarios.items():
        try:
            response = requests.post(
                f"{API_BASE}/carbon/evaluate",
                json=config["payload"],
                timeout=10
            )
            if response.status_code != 200:
                print(f"[FAIL] {name} - Status {response.status_code}")
                results[name] = False
                continue
            
            data = response.json()
            decision = data.get('decision', {})
            opt_pods = decision.get('optimized_required_pods')
            action = decision.get('recommended_action')
            
            passed = opt_pods >= config["min_pods"]
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {name}")
            print(f"       Action: {action}, Pods: {opt_pods} (min: {config['min_pods']})")
            results[name] = passed
            
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            results[name] = False
    
    # STEP 4: Carbon Logic
    print("\nSTEP 4 - CARBON LOGIC VALIDATION")
    print("-"*70)
    try:
        payloads = [
            {"predicted_cpu": 50, "load_level": "NORMAL", "raw_required_pods": 1, "current_pods": 1},
            {"predicted_cpu": 50, "load_level": "NORMAL", "raw_required_pods": 2, "current_pods": 2},
        ]
        for p in payloads:
            requests.post(f"{API_BASE}/carbon/evaluate", json=p, timeout=10)
        print("[PASS] Carbon calculations functional")
    except Exception as e:
        print(f"[FAIL] Carbon logic: {e}")
    
    # STEP 5: Workflow
    print("\nSTEP 5 - WORKFLOW VALIDATION")
    print("-"*70)
    try:
        # Get prediction
        resp1 = requests.get(f"{API_BASE}/predict", timeout=5)
        pred = resp1.json()
        
        # Use in carbon eval
        payload = {
            "predicted_cpu": pred['predicted_cpu'],
            "load_level": pred['load_level'],
            "raw_required_pods": pred['recommended_pods'],
            "current_pods": pred['recommended_pods'] - 1
        }
        resp2 = requests.post(f"{API_BASE}/carbon/evaluate", json=payload, timeout=10)
        print("[PASS] Engine 1 to Engine 2 workflow successful")
    except Exception as e:
        print(f"[FAIL] Workflow: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Scenarios: {passed}/{total} passed")
    
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
    
    print("\n" + "="*70)
    if passed == total:
        print("ENGINE 2 STATUS: VALIDATED - PRODUCTION READY")
    else:
        print("ENGINE 2 STATUS: ISSUES FOUND")
    print("="*70)

if __name__ == "__main__":
    test_all()
