#!/usr/bin/env python3
"""
Green DevOps System - Quick Validation Script
Validates all components are running and responsive
"""

import requests
import sys
from typing import Tuple

def check_endpoint(url: str, method: str = "GET", name: str = "") -> Tuple[bool, str]:
    """Check if an endpoint is responsive"""
    try:
        if method == "GET":
            resp = requests.get(url, timeout=5)
        else:
            resp = requests.post(url, json={}, timeout=5)
        
        if resp.status_code in [200, 400, 422]:  # 400/422 expected for POST without full data
            return True, f"HTTP {resp.status_code}"
        else:
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("\n" + "="*80)
    print("GREEN DEVOPS SYSTEM - QUICK VALIDATION")
    print("="*80 + "\n")
    
    all_pass = True
    
    # Check API Server
    print("Checking API Server...")
    ok, msg = check_endpoint("http://localhost:5000/health", name="Health")
    print(f"  Health Endpoint: {'✅ PASS' if ok else '❌ FAIL'} ({msg})")
    all_pass = all_pass and ok
    
    # Check Engine 1
    print("\nChecking Engine 1 (Workload Prediction)...")
    ok, msg = check_endpoint("http://localhost:5000/predict", name="Predict")
    print(f"  /predict: {'✅ PASS' if ok else '❌ FAIL'} ({msg})")
    all_pass = all_pass and ok
    
    # Check Engine 3
    print("\nChecking Engine 3 (Job Scheduling)...")
    ok, msg = check_endpoint("http://localhost:5000/jobs/evaluate", "POST", "Jobs")
    print(f"  /jobs/evaluate: {'✅ PASS' if ok else '❌ FAIL'} ({msg})")
    all_pass = all_pass and ok
    
    # Check Engine 2
    print("\nChecking Engine 2 (Carbon Optimization)...")
    ok, msg = check_endpoint("http://localhost:5000/carbon/evaluate", "POST", "Carbon")
    print(f"  /carbon/evaluate: {'✅ PASS' if ok else '❌ FAIL'} ({msg})")
    all_pass = all_pass and ok
    
    # Check Decision Layer
    print("\nChecking Decision Layer...")
    ok, msg = check_endpoint("http://localhost:5000/decision/evaluate", "POST", "Decision")
    print(f"  /decision/evaluate: {'✅ PASS' if ok else '❌ FAIL'} ({msg})")
    all_pass = all_pass and ok
    
    # Check Dashboard
    print("\nChecking Dashboard...")
    ok, msg = check_endpoint("http://localhost:8501/_stcore/health", name="Dashboard")
    print(f"  Dashboard Health: {'✅ PASS' if ok else '❌ FAIL'} ({msg})")
    all_pass = all_pass and ok
    
    # Summary
    print("\n" + "="*80)
    if all_pass:
        print("✅ SYSTEM VALIDATION PASSED - All components running")
        print("="*80 + "\n")
        return 0
    else:
        print("❌ SYSTEM VALIDATION FAILED - Some components not responding")
        print("="*80 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
