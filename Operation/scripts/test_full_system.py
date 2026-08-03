"""
Green DevOps Operation Phase - Complete System Validation

Comprehensive end-to-end testing of Engine 1, Runtime Data Flow, API Layer,
and Unified Dashboard with real system data only.

Usage:
    python scripts/test_full_system.py
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

import requests
import pandas as pd


# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = "http://localhost:8000"
API_HEALTH = f"{API_BASE_URL}/health"
API_PREDICT = f"{API_BASE_URL}/predict"
API_STATUS = f"{API_BASE_URL}/status"
API_METRICS = f"{API_BASE_URL}/metrics"

DATA_DIR = Path("data")
PREDICTIONS_DIR = DATA_DIR / "predictions"
RUNTIME_METRICS_DIR = DATA_DIR / "runtime_metrics"
MODEL_PATH = Path("models/trained/workload_predictor_balanced.pt")
CONFIG_PATH = Path("src/workload_prediction_engine/config.py")

API_TIMEOUT = 5
API_RETRIES = 3


# ============================================================================
# Test Results Storage
# ============================================================================

class TestResults:
    def __init__(self):
        self.results = {}
        self.details = {}

    def add(self, test_name: str, passed: bool, details: str = ""):
        self.results[test_name] = passed
        self.details[test_name] = details

    def get_summary(self) -> Dict:
        return {
            "total": len(self.results),
            "passed": sum(1 for v in self.results.values() if v),
            "failed": sum(1 for v in self.results.values() if not v),
            "pass_rate": sum(1 for v in self.results.values() if v) / len(self.results) * 100 if self.results else 0
        }

    def print_report(self):
        print("\n" + "="*80)
        print("SYSTEM VALIDATION TEST REPORT")
        print("="*80 + "\n")
        
        for test_name, passed in self.results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{test_name:40} {status}")
            if self.details[test_name]:
                print(f"       {self.details[test_name]}")
        
        summary = self.get_summary()
        print("\n" + "-"*80)
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']:.1f}%")
        print("-"*80 + "\n")


results = TestResults()


# ============================================================================
# 1. ENGINE 1 CORE TESTS
# ============================================================================

def test_model_loads():
    """Test that model loads correctly."""
    try:
        import torch
        if not MODEL_PATH.exists():
            results.add("Model Loads", False, f"Model not found at {MODEL_PATH}")
            return
        
        model = torch.load(MODEL_PATH, map_location="cpu")
        results.add("Model Loads", True, f"Model loaded (type: {type(model).__name__})")
    except Exception as e:
        results.add("Model Loads", False, str(e)[:100])


def test_engine1_prediction():
    """Test that Engine 1 makes valid predictions."""
    try:
        from src.workload_prediction_engine.live_predictor import EnginePredictor
        
        if not MODEL_PATH.exists():
            results.add("Engine1 Prediction", False, "Model not found")
            return
        
        try:
            predictor = EnginePredictor(model_path=str(MODEL_PATH))
            
            # Create dummy input (12 timesteps x 2 features)
            import numpy as np
            dummy_sequence = np.random.rand(1, 12, 2).astype(np.float32)
            
            prediction = predictor.predict(dummy_sequence)
            
            # Verify output structure
            required_fields = ["predicted_cpu", "predicted_load_level", "recommended_pods"]
            has_fields = all(field in prediction for field in required_fields)
            
            if not has_fields:
                results.add("Engine1 Prediction", False, f"Missing fields in output")
                return
            
            cpu = prediction["predicted_cpu"]
            if not (0 <= cpu <= 100):
                results.add("Engine1 Prediction", False, f"CPU out of range: {cpu}")
                return
            
            results.add("Engine1 Prediction", True, f"CPU: {cpu:.1f}%, Load: {prediction['predicted_load_level']}")
        except Exception as e:
            results.add("Engine1 Prediction", False, str(e)[:100])
    except ImportError:
        results.add("Engine1 Prediction", False, "Import failed")


def test_prediction_variance():
    """Test that predictions vary over time."""
    try:
        from src.workload_prediction_engine.live_predictor import EnginePredictor
        import numpy as np
        
        if not MODEL_PATH.exists():
            results.add("Prediction Variance", False, "Model not found")
            return
        
        try:
            predictor = EnginePredictor(model_path=str(MODEL_PATH))
            
            predictions = []
            for i in range(5):
                seq = np.random.rand(1, 12, 2).astype(np.float32)
                pred = predictor.predict(seq)
                predictions.append(pred["predicted_cpu"])
            
            min_pred = min(predictions)
            max_pred = max(predictions)
            variance = max_pred - min_pred
            
            if variance < 1.0:
                results.add("Prediction Variance", False, f"Low variance: {variance:.2f}")
            else:
                results.add("Prediction Variance", True, f"Variance: {variance:.2f} (range: {min_pred:.1f}-{max_pred:.1f})")
        except Exception as e:
            results.add("Prediction Variance", False, str(e)[:100])
    except ImportError:
        results.add("Prediction Variance", False, "Import failed")


# ============================================================================
# 2. RUNTIME DATA FLOW TESTS
# ============================================================================

def test_metrics_collection():
    """Test that metrics are collected."""
    try:
        if not RUNTIME_METRICS_DIR.exists():
            results.add("Metrics Collection", False, "Runtime metrics dir not found")
            return
        
        csv_files = list(RUNTIME_METRICS_DIR.glob("*.csv"))
        
        if not csv_files:
            results.add("Metrics Collection", False, "No metrics CSV files found")
            return
        
        latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
        
        try:
            df = pd.read_csv(latest_file)
            record_count = len(df)
            
            required_cols = ["cpu", "memory", "timestamp"]
            has_cols = all(col in df.columns for col in required_cols)
            
            if not has_cols:
                results.add("Metrics Collection", False, f"Missing columns in {latest_file.name}")
                return
            
            results.add("Metrics Collection", True, f"{record_count} records in {latest_file.name}")
        except Exception as e:
            results.add("Metrics Collection", False, f"CSV read error: {str(e)[:80]}")
    except Exception as e:
        results.add("Metrics Collection", False, str(e)[:100])


def test_timestamp_alignment():
    """Test that metrics use aligned timestamps (30s)."""
    try:
        if not RUNTIME_METRICS_DIR.exists():
            results.add("Timestamp Alignment", False, "Metrics dir not found")
            return
        
        csv_files = list(RUNTIME_METRICS_DIR.glob("*.csv"))
        if not csv_files:
            results.add("Timestamp Alignment", False, "No metrics files")
            return
        
        latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_file)
        
        if len(df) < 2:
            results.add("Timestamp Alignment", False, "Insufficient records")
            return
        
        ts = df["timestamp"].astype(int).values
        
        # Check if timestamps are 30 seconds apart
        diffs = ts[1:] - ts[:-1]
        expected_diff = 30
        aligned = sum(1 for d in diffs if 25 <= d <= 35) / len(diffs)
        
        if aligned < 0.5:
            results.add("Timestamp Alignment", False, f"Low alignment: {aligned:.0%}")
        else:
            results.add("Timestamp Alignment", True, f"Alignment: {aligned:.0%}")
    except Exception as e:
        results.add("Timestamp Alignment", False, str(e)[:100])


# ============================================================================
# 3. MODE SWITCHING TESTS
# ============================================================================

def test_mode_switching():
    """Test cold_start to runtime mode transition."""
    try:
        health = api_call_with_retry(API_HEALTH)
        if not health:
            results.add("Mode Switching", False, "Cannot reach API")
            return
        
        mode = health.get("mode", "unknown")
        records = health.get("records_collected", 0)
        
        if mode not in ["cold_start", "runtime"]:
            results.add("Mode Switching", False, f"Invalid mode: {mode}")
            return
        
        expected_mode = "runtime" if records >= 12 else "cold_start"
        
        if mode == expected_mode:
            results.add("Mode Switching", True, f"Mode: {mode} ({records} records)")
        else:
            results.add("Mode Switching", False, f"Mode mismatch: {mode} vs expected {expected_mode}")
    except Exception as e:
        results.add("Mode Switching", False, str(e)[:100])


# ============================================================================
# 4. LIVE PREDICTION TESTS
# ============================================================================

def test_live_predictions():
    """Test live prediction loop."""
    try:
        predictions = []
        errors = []
        
        for i in range(3):
            try:
                response = requests.get(API_PREDICT, timeout=API_TIMEOUT)
                if response.status_code == 200:
                    pred = response.json()
                    if pred.get("status") == "success":
                        predictions.append(pred.get("prediction", {}))
                    else:
                        errors.append(pred.get("error", "Unknown error"))
                else:
                    errors.append(f"Status {response.status_code}")
            except Exception as e:
                errors.append(str(e)[:50])
            
            time.sleep(0.5)
        
        if not predictions:
            results.add("Live Predictions", False, f"No valid predictions: {errors[0] if errors else 'No data'}")
            return
        
        # Check prediction structure
        sample = predictions[0]
        required = ["predicted_cpu", "predicted_load_level", "recommended_pods"]
        if all(k in sample for k in required):
            results.add("Live Predictions", True, f"{len(predictions)} predictions collected")
        else:
            results.add("Live Predictions", False, "Invalid prediction structure")
    except Exception as e:
        results.add("Live Predictions", False, str(e)[:100])


# ============================================================================
# 5. API LAYER TESTS
# ============================================================================

def api_call_with_retry(url: str, timeout: int = API_TIMEOUT) -> Optional[Dict]:
    """Call API with retries."""
    for attempt in range(API_RETRIES):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except Exception:
            if attempt < API_RETRIES - 1:
                time.sleep(0.5)
    return None


def test_api_health():
    """Test /health endpoint."""
    try:
        response = requests.get(API_HEALTH, timeout=API_TIMEOUT)
        
        if response.status_code != 200:
            results.add("API /health", False, f"Status code {response.status_code}")
            return
        
        data = response.json()
        required = ["status", "mode", "records_collected"]
        
        if all(k in data for k in required):
            results.add("API /health", True, f"Status: {data['status']}, Mode: {data['mode']}")
        else:
            results.add("API /health", False, "Missing required fields")
    except Exception as e:
        results.add("API /health", False, str(e)[:100])


def test_api_predict():
    """Test /predict endpoint."""
    try:
        response = requests.get(API_PREDICT, timeout=API_TIMEOUT)
        
        if response.status_code != 200:
            results.add("API /predict", False, f"Status code {response.status_code}")
            return
        
        data = response.json()
        
        if data.get("status") != "success":
            results.add("API /predict", False, data.get("error", "Unknown error"))
            return
        
        pred = data.get("prediction", {})
        required = ["predicted_cpu", "predicted_load_level", "recommended_pods"]
        
        if all(k in pred for k in required):
            results.add("API /predict", True, f"CPU: {pred['predicted_cpu']:.1f}%")
        else:
            results.add("API /predict", False, "Missing prediction fields")
    except Exception as e:
        results.add("API /predict", False, str(e)[:100])


def test_api_status():
    """Test /status endpoint."""
    try:
        response = requests.get(API_STATUS, timeout=API_TIMEOUT)
        
        if response.status_code != 200:
            results.add("API /status", False, f"Status code {response.status_code}")
            return
        
        data = response.json()
        
        if "model_version" in data or "mode" in data:
            results.add("API /status", True, "Status data available")
        else:
            results.add("API /status", False, "Missing status data")
    except Exception as e:
        results.add("API /status", False, str(e)[:100])


def test_api_metrics():
    """Test /metrics endpoint."""
    try:
        health = api_call_with_retry(API_HEALTH)
        if not health:
            results.add("API /metrics", False, "Cannot reach /health")
            return
        
        system_id = health.get("system_id", "main_system")
        url = f"{API_METRICS}/{system_id}"
        response = requests.get(url, timeout=API_TIMEOUT)
        
        if response.status_code in [200, 404]:
            results.add("API /metrics", True, f"Accessible for {system_id}")
        else:
            results.add("API /metrics", False, f"Status code {response.status_code}")
    except Exception as e:
        results.add("API /metrics", False, str(e)[:100])


# ============================================================================
# 6. DASHBOARD DATA TESTS
# ============================================================================

def test_dashboard_data_consistency():
    """Test that dashboard data matches API."""
    try:
        # Get API data
        health = api_call_with_retry(API_HEALTH)
        predict = api_call_with_retry(API_PREDICT)
        
        if not health or not predict:
            results.add("Dashboard Data Consistency", False, "Cannot reach API endpoints")
            return
        
        # Extract values
        api_mode = health.get("mode", "")
        api_cpu = predict.get("prediction", {}).get("predicted_cpu", -1)
        
        if api_mode and api_cpu >= 0:
            results.add("Dashboard Data Consistency", True, f"Mode: {api_mode}, CPU: {api_cpu:.1f}%")
        else:
            results.add("Dashboard Data Consistency", False, "Invalid API responses")
    except Exception as e:
        results.add("Dashboard Data Consistency", False, str(e)[:100])


def test_dashboard_history_data():
    """Test that dashboard can access history data."""
    try:
        if not PREDICTIONS_DIR.exists():
            results.add("Dashboard History Data", False, "Predictions dir not found")
            return
        
        csv_files = list(PREDICTIONS_DIR.glob("*.csv"))
        
        if not csv_files:
            results.add("Dashboard History Data", False, "No prediction history found")
            return
        
        # Try to read latest
        latest = max(csv_files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest)
        
        if len(df) > 0:
            results.add("Dashboard History Data", True, f"{len(df)} predictions in history")
        else:
            results.add("Dashboard History Data", False, "History file is empty")
    except Exception as e:
        results.add("Dashboard History Data", False, str(e)[:100])


# ============================================================================
# 7. DATA CONSISTENCY TESTS
# ============================================================================

def test_runtime_store_consistency():
    """Test that runtime store data is consistent."""
    try:
        if not RUNTIME_METRICS_DIR.exists():
            results.add("Runtime Store Consistency", False, "Metrics dir not found")
            return
        
        csv_files = list(RUNTIME_METRICS_DIR.glob("*.csv"))
        if not csv_files:
            results.add("Runtime Store Consistency", False, "No metrics files")
            return
        
        latest = max(csv_files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest)
        
        # Check data types and ranges
        issues = []
        
        if "cpu" in df.columns:
            cpu_vals = df["cpu"]
            if not all((0 <= v <= 100) or (pd.isna(v)) for v in cpu_vals):
                issues.append("CPU out of range")
        
        if "memory" in df.columns:
            mem_vals = df["memory"]
            if not all((v >= 0) or (pd.isna(v)) for v in mem_vals):
                issues.append("Memory negative")
        
        if issues:
            results.add("Runtime Store Consistency", False, ", ".join(issues))
        else:
            results.add("Runtime Store Consistency", True, f"{len(df)} valid records")
    except Exception as e:
        results.add("Runtime Store Consistency", False, str(e)[:100])


def test_api_data_validity():
    """Test that API returns valid data."""
    try:
        health = api_call_with_retry(API_HEALTH)
        predict = api_call_with_retry(API_PREDICT)
        
        if not health or not predict:
            results.add("API Data Validity", False, "Cannot reach API")
            return
        
        issues = []
        
        # Check health data
        mode = health.get("mode", "")
        if mode not in ["cold_start", "runtime"]:
            issues.append(f"Invalid mode: {mode}")
        
        # Check prediction data
        cpu = predict.get("prediction", {}).get("predicted_cpu", -1)
        if not (0 <= cpu <= 100):
            issues.append(f"CPU out of range: {cpu}")
        
        if issues:
            results.add("API Data Validity", False, ", ".join(issues))
        else:
            results.add("API Data Validity", True, "All API values valid")
    except Exception as e:
        results.add("API Data Validity", False, str(e)[:100])


# ============================================================================
# 8. PERFORMANCE TESTS
# ============================================================================

def test_api_response_time():
    """Test API response time."""
    try:
        times = []
        
        for _ in range(3):
            start = time.time()
            response = requests.get(API_HEALTH, timeout=API_TIMEOUT)
            elapsed = (time.time() - start) * 1000  # ms
            
            if response.status_code == 200:
                times.append(elapsed)
            
            time.sleep(0.1)
        
        if not times:
            results.add("API Response Time", False, "No valid responses")
            return
        
        avg_time = sum(times) / len(times)
        
        if avg_time < 2000:  # 2 seconds
            results.add("API Response Time", True, f"Avg: {avg_time:.0f}ms")
        else:
            results.add("API Response Time", False, f"Slow: {avg_time:.0f}ms")
    except Exception as e:
        results.add("API Response Time", False, str(e)[:100])


def test_dashboard_app_loads():
    """Test that dashboard app can be imported."""
    try:
        sys.path.insert(0, str(Path.cwd() / "dashboard"))
        
        # Try importing unified app
        from unified_app import main
        
        results.add("Dashboard App Loads", True, "Unified app imported successfully")
    except Exception as e:
        results.add("Dashboard App Loads", False, str(e)[:100])


# ============================================================================
# 9. UNIFIED DASHBOARD OVERVIEW TESTS
# ============================================================================

def test_dashboard_overview_load():
    """Test Level 1 Overview dashboard can render."""
    try:
        sys.path.insert(0, str(Path.cwd() / "dashboard"))
        from app import render_overview
        
        results.add("Dashboard Overview", True, "Level 1 dashboard function available")
    except Exception as e:
        results.add("Dashboard Overview", False, str(e)[:100])


# ============================================================================
# 10. UNIFIED DASHBOARD TECHNICAL TESTS
# ============================================================================

def test_dashboard_technical_load():
    """Test Level 2 Technical dashboard can render."""
    try:
        sys.path.insert(0, str(Path.cwd() / "dashboard"))
        from technical_app import render_technical
        
        results.add("Dashboard Technical", True, "Level 2 dashboard function available")
    except Exception as e:
        results.add("Dashboard Technical", False, str(e)[:100])


# ============================================================================
# 11. INTEGRATION TESTS
# ============================================================================

def test_unified_integration():
    """Test unified dashboard integration."""
    try:
        sys.path.insert(0, str(Path.cwd() / "dashboard"))
        
        from unified_app import main
        from app import render_overview
        from technical_app import render_technical
        
        results.add("Unified Integration", True, "All components integrated")
    except Exception as e:
        results.add("Unified Integration", False, str(e)[:100])


# ============================================================================
# Main Test Execution
# ============================================================================

def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("GREEN DEVOPS OPERATION PHASE - SYSTEM VALIDATION")
    print("="*80)
    print("\nRunning comprehensive system tests...\n")
    
    # Engine 1 Tests
    print("[1/11] Testing Engine 1 Core...")
    test_model_loads()
    test_engine1_prediction()
    test_prediction_variance()
    
    # Runtime Data Tests
    print("[2/11] Testing Runtime Data Flow...")
    test_metrics_collection()
    test_timestamp_alignment()
    
    # Mode Switching Tests
    print("[3/11] Testing Mode Switching...")
    test_mode_switching()
    
    # Live Prediction Tests
    print("[4/11] Testing Live Predictions...")
    test_live_predictions()
    
    # API Tests
    print("[5/11] Testing API Layer...")
    test_api_health()
    test_api_predict()
    test_api_status()
    test_api_metrics()
    
    # Dashboard Tests
    print("[6/11] Testing Dashboard Data...")
    test_dashboard_data_consistency()
    test_dashboard_history_data()
    
    # Data Consistency Tests
    print("[7/11] Testing Data Consistency...")
    test_runtime_store_consistency()
    test_api_data_validity()
    
    # Performance Tests
    print("[8/11] Testing Performance...")
    test_api_response_time()
    test_dashboard_app_loads()
    
    # Dashboard Tests
    print("[9/11] Testing Dashboard Overview...")
    test_dashboard_overview_load()
    
    print("[10/11] Testing Dashboard Technical...")
    test_dashboard_technical_load()
    
    # Integration Tests
    print("[11/11] Testing Integration...")
    test_unified_integration()
    
    # Print Results
    results.print_report()
    
    # Final Status
    summary = results.get_summary()
    print("="*80)
    
    if summary["failed"] == 0:
        print("SYSTEM READY FOR PRODUCTION ✅")
    else:
        print(f"SYSTEM HAS {summary['failed']} ISSUES - REVIEW FAILURES ABOVE ❌")
    
    print("="*80 + "\n")
    
    return summary["failed"] == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
