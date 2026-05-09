#!/usr/bin/env python3
"""
Test Data Flow Validation Script for Green DevOps Demo System

Validates the complete data flow:
1. Demo scenario runner functionality
2. Engine 3 (Jobs) API endpoint
3. Engine 2 (Carbon) API endpoint
4. Decision Layer API endpoint
5. Dashboard data integration
6. History file generation

Run after starting: API server, dashboard, and demo scenario runner
"""

import requests
import json
import time
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

# ============================================================================
# Setup
# ============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_URL = "http://localhost:5000"
DEMO_DIR = Path("data/demo")
DEMO_LATEST = DEMO_DIR / "latest_decision.json"
DEMO_HISTORY = DEMO_DIR / "demo_history.csv"

# Test results tracker
test_results = {
    "TEST DATA RUNNER": "UNKNOWN",
    "ENGINE 3 API FLOW": "UNKNOWN",
    "ENGINE 2 API FLOW": "UNKNOWN",
    "DECISION API FLOW": "UNKNOWN",
    "DASHBOARD LIVE VALUES": "UNKNOWN",
    "SCENARIO HISTORY GRAPH": "UNKNOWN",
}

# ============================================================================
# Test Functions
# ============================================================================

def test_api_connectivity():
    """Test basic API connectivity."""
    logger.info("\n" + "="*80)
    logger.info("TEST: API Connectivity")
    logger.info("="*80)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        if response.status_code == 200:
            logger.info(f"✓ API server responding at {API_URL}")
            return True
        else:
            logger.error(f"✗ API returned {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ API unreachable: {e}")
        return False


def test_engine3_jobs_endpoint():
    """Test Engine 3 /jobs/evaluate endpoint."""
    logger.info("\n" + "="*80)
    logger.info("TEST: Engine 3 (Jobs) API Endpoint")
    logger.info("="*80)
    
    test_results["ENGINE 3 API FLOW"] = "FAIL"
    
    try:
        payload = {
            "jobs": [
                {
                    "job_id": "test_job_1",
                    "job_type": "test",
                    "priority": "LOW",
                    "estimated_runtime_seconds": 100,
                    "estimated_cpu_percent": 10,
                    "deadline_seconds": 3600,
                    "already_delayed_seconds": 0
                }
            ],
            "backlog_size": 1,
            "current_load_level": "NORMAL",
            "current_cpu": 50.0,
            "current_pods": 2
        }
        
        logger.info(f"Calling POST {API_URL}/jobs/evaluate")
        response = requests.post(f"{API_URL}/jobs/evaluate", json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Engine 3 response: {response.status_code}")
            logger.info(f"  - Delayable jobs: {data.get('delayable_jobs', 'N/A')}")
            logger.info(f"  - Workload reduction: {data.get('workload_reduction_percent', 0)*100:.1f}%")
            test_results["ENGINE 3 API FLOW"] = "PASS"
            return True
        else:
            logger.error(f"✗ Engine 3 returned {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Engine 3 call failed: {e}")
        return False


def test_engine2_carbon_endpoint():
    """Test Engine 2 /carbon/evaluate endpoint."""
    logger.info("\n" + "="*80)
    logger.info("TEST: Engine 2 (Carbon) API Endpoint")
    logger.info("="*80)
    
    test_results["ENGINE 2 API FLOW"] = "FAIL"
    
    try:
        payload = {
            "system_id": "test-system",
            "predicted_cpu": 65.0,
            "predicted_load_level": "NORMAL",
            "recommended_pods": 3,
            "current_pods": 2,
            "prediction_window_seconds": 30,
            "delayable_jobs": 2,
            "workload_reduction_percent": 0.3
        }
        
        logger.info(f"Calling POST {API_URL}/carbon/evaluate")
        response = requests.post(f"{API_URL}/carbon/evaluate", json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Engine 2 response: {response.status_code}")
            logger.info(f"  - Carbon saving: {data.get('carbon_saving_gco2', 0):.1f}g CO2")
            logger.info(f"  - Recommended action: {data.get('recommended_action', 'N/A')}")
            test_results["ENGINE 2 API FLOW"] = "PASS"
            return True
        else:
            logger.error(f"✗ Engine 2 returned {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Engine 2 call failed: {e}")
        return False


def test_decision_layer_endpoint():
    """Test Decision Layer /decision/evaluate endpoint."""
    logger.info("\n" + "="*80)
    logger.info("TEST: Decision Layer API Endpoint")
    logger.info("="*80)
    
    test_results["DECISION API FLOW"] = "FAIL"
    
    try:
        payload = {
            "system_id": "test-system",
            "current_pods": 2,
            "engine1_output": {
                "system_id": "test-system",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "prediction_window_seconds": 30,
                "prediction": {
                    "predicted_cpu": 65.0,
                    "predicted_load_level": "NORMAL",
                    "recommended_pods": 3,
                    "confidence": 0.85
                },
                "data_source": "test"
            },
            "engine2_output": {
                "raw_scenario": {"required_pods": 3},
                "optimized_scenario": {"required_pods": 2},
                "recommended_action": "hybrid",
                "carbon_saving_gco2": 10.0,
                "carbon_saving_percent": 20.0
            },
            "engine3_output": {
                "delayable_jobs": 2,
                "delayable_job_ids": ["job_1", "job_2"],
                "workload_reduction_percent": 0.3
            }
        }
        
        logger.info(f"Calling POST {API_URL}/decision/evaluate")
        response = requests.post(f"{API_URL}/decision/evaluate", json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Decision Layer response: {response.status_code}")
            decision = data.get("decision", {})
            logger.info(f"  - Final action: {decision.get('action', 'N/A')}")
            logger.info(f"  - Final pods: {decision.get('final_pods', 'N/A')}")
            logger.info(f"  - SLA preserved: {decision.get('sla_preserved', 'N/A')}")
            test_results["DECISION API FLOW"] = "PASS"
            return True
        else:
            logger.error(f"✗ Decision Layer returned {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Decision Layer call failed: {e}")
        return False


def test_demo_data_runner():
    """Test demo scenario runner file generation."""
    logger.info("\n" + "="*80)
    logger.info("TEST: Demo Scenario Runner Output")
    logger.info("="*80)
    
    test_results["TEST DATA RUNNER"] = "FAIL"
    
    # Check if demo latest file exists and has valid content
    if not DEMO_LATEST.exists():
        logger.warning(f"⚠️ Demo latest file not found: {DEMO_LATEST}")
        logger.info("   → Run demo runner: python scripts/run_demo_scenarios.py")
        return False
    
    try:
        with open(DEMO_LATEST, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        required_keys = ["timestamp", "scenario_name", "steps"]
        if all(k in data for k in required_keys):
            logger.info(f"✓ Demo latest file exists and is valid")
            logger.info(f"  - Scenario: {data.get('scenario_name', 'N/A')}")
            logger.info(f"  - Timestamp: {data.get('timestamp', 'N/A')}")
            test_results["TEST DATA RUNNER"] = "PASS"
            return True
        else:
            logger.error(f"✗ Demo latest file structure invalid")
            return False
    
    except Exception as e:
        logger.error(f"✗ Failed to read demo latest file: {e}")
        return False


def test_dashboard_data_integration():
    """Test that dashboard can read demo data."""
    logger.info("\n" + "="*80)
    logger.info("TEST: Dashboard Data Integration")
    logger.info("="*80)
    
    test_results["DASHBOARD LIVE VALUES"] = "FAIL"
    
    try:
        # Try to import and test the demo adapter
        from dashboard.demo_adapter import (
            is_demo_mode_available,
            get_latest_demo_result,
            format_demo_display_data
        )
        
        if is_demo_mode_available():
            logger.info(f"✓ Demo mode is available")
            
            result = get_latest_demo_result()
            if result:
                logger.info(f"✓ Latest demo result retrieved")
                
                display_data = format_demo_display_data(result)
                if display_data and "engine1" in display_data:
                    logger.info(f"✓ Demo data formatted for dashboard")
                    logger.info(f"  - CPU: {display_data['engine1']['predicted_cpu']}%")
                    logger.info(f"  - Load: {display_data['engine1']['predicted_load_level']}")
                    logger.info(f"  - Pods: {display_data['decision']['final_pods']}")
                    test_results["DASHBOARD LIVE VALUES"] = "PASS"
                    return True
        else:
            logger.warning(f"⚠️ Demo mode not available yet")
            logger.info("   → Run demo runner to generate data")
            return False
    
    except Exception as e:
        logger.error(f"✗ Dashboard integration test failed: {e}")
        return False


def test_scenario_history():
    """Test scenario history CSV generation."""
    logger.info("\n" + "="*80)
    logger.info("TEST: Scenario History Graph")
    logger.info("="*80)
    
    test_results["SCENARIO HISTORY GRAPH"] = "FAIL"
    
    if not DEMO_HISTORY.exists() or DEMO_HISTORY.stat().st_size == 0:
        logger.warning(f"⚠️ Demo history file not found or empty: {DEMO_HISTORY}")
        logger.info("   → Run demo runner multiple times to generate history")
        return False
    
    try:
        df = pd.read_csv(DEMO_HISTORY)
        
        # Validate structure
        required_columns = [
            "timestamp", "scenario_name", "predicted_cpu", "load_level",
            "final_pods", "final_action", "jobs_delayed", "carbon_saving_gco2"
        ]
        
        if all(col in df.columns for col in required_columns):
            logger.info(f"✓ History file exists with valid structure")
            logger.info(f"  - Records: {len(df)}")
            logger.info(f"  - Columns: {', '.join(df.columns)}")
            
            # Show sample data
            if len(df) > 0:
                logger.info(f"  - Latest scenario: {df.iloc[-1]['scenario_name']}")
                logger.info(f"  - Latest CPU: {df.iloc[-1]['predicted_cpu']}%")
                logger.info(f"  - Latest action: {df.iloc[-1]['final_action']}")
            
            # Validate data variety (should have multiple scenarios)
            unique_scenarios = df['scenario_name'].nunique()
            if unique_scenarios >= 2:
                logger.info(f"✓ Multiple scenarios detected: {unique_scenarios}")
                test_results["SCENARIO HISTORY GRAPH"] = "PASS"
                return True
            else:
                logger.warning(f"⚠️ Only {unique_scenarios} unique scenario(s) - need more history")
                return False
        else:
            logger.error(f"✗ History file structure invalid")
            return False
    
    except Exception as e:
        logger.error(f"✗ Failed to read history file: {e}")
        return False


# ============================================================================
# Main Validation
# ============================================================================

def main():
    """Run all validation tests."""
    logger.info("\n" + "="*80)
    logger.info(" "*15 + "GREEN DEVOPS TEST DATA SYSTEM VALIDATION")
    logger.info("="*80 + "\n")
    
    # Check API connectivity first
    if not test_api_connectivity():
        logger.error("\n⚠️ API server is not running!")
        logger.error("Start API server: python scripts/run_live_api.py --system-id test-system --port 5000 --mock")
        return
    
    # Run all tests
    logger.info("\nRunning validation tests...")
    
    test_api_connectivity()
    test_engine3_jobs_endpoint()
    test_engine2_carbon_endpoint()
    test_decision_layer_endpoint()
    test_demo_data_runner()
    test_dashboard_data_integration()
    test_scenario_history()
    
    # Print results
    logger.info("\n" + "="*80)
    logger.info("VALIDATION RESULTS SUMMARY")
    logger.info("="*80 + "\n")
    
    pass_count = 0
    fail_count = 0
    
    for test_name, result in test_results.items():
        status = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
        logger.info(f"{status} {test_name:.<40} {result}")
        
        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
    
    # Final status
    logger.info("\n" + "="*80)
    if fail_count == 0 and pass_count >= 4:
        logger.info("✅ FINAL STATUS: DASHBOARD TEST DATA FLOW COMPLETE ✅")
        logger.info("="*80 + "\n")
        logger.info("Demo system is ready! The dashboard will show:")
        logger.info("  • 5 scenarios cycling every 5 seconds")
        logger.info("  • CPU changes from 20% → 55% → 85% → 90% → 25%")
        logger.info("  • Load levels changing: LOW → NORMAL → HIGH → HIGH → LOW")
        logger.info("  • Pod counts adjusting based on decisions")
        logger.info("  • Carbon savings and job delays updating in real-time")
        logger.info("  • Final action recommendations from Decision Layer")
        logger.info("\nAccess dashboard at: http://localhost:8503\n")
    else:
        logger.info("❌ FINAL STATUS: DASHBOARD TEST DATA FLOW INCOMPLETE ❌")
        logger.info("="*80 + "\n")
        logger.error(f"Failed/Unknown tests: {fail_count}")
        logger.error("\nRequired fixes:")
        if test_results["TEST DATA RUNNER"] != "PASS":
            logger.error("  → Run demo runner: python scripts/run_demo_scenarios.py --duration 60")
        if test_results["SCENARIO HISTORY GRAPH"] != "PASS":
            logger.error("  → Let demo runner generate more history (wait 30+ seconds)")
        logger.error("  → Then run this validation again\n")


if __name__ == "__main__":
    main()
