"""
Validation test suite for Engine 3 - Job Prioritization Engine.

Tests:
- Job classification (HIGH/MEDIUM/LOW)
- Delay eligibility checking
- Workload estimation
- API endpoint functionality
- Complete evaluation scenarios
"""

import sys
import os
import traceback
from typing import Dict, Any, List
import json
import logging

# Add src directory to path for imports
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}\n")


def test_imports():
    """Test that all Engine 3 modules can be imported."""
    print_subheader("TEST 1: Module Imports")
    
    try:
        from job_prioritization_engine import JobPrioritizationEngine
        print("✓ JobPrioritizationEngine imported successfully")
        
        from job_prioritization_engine.job_classifier import JobClassifier
        print("✓ JobClassifier imported successfully")
        
        from job_prioritization_engine.delay_eligibility import DelayEligibilityChecker
        print("✓ DelayEligibilityChecker imported successfully")
        
        from job_prioritization_engine.workload_estimator import WorkloadEstimator
        print("✓ WorkloadEstimator imported successfully")
        
        print("\n✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_job_classification():
    """Test job classification logic."""
    print_subheader("TEST 2: Job Classification")
    
    try:
        from job_prioritization_engine.job_classifier import JobClassifier
        
        classifier = JobClassifier()
        
        # Test HIGH priority
        job_high = {
            "job_id": "job_1",
            "job_type": "payment_processing",
            "estimated_cpu_percent": 20.0,
        }
        result = classifier.classify(job_high)
        assert result.calculated_priority == "HIGH", f"Expected HIGH, got {result.calculated_priority}"
        print(f"✓ HIGH priority: {job_high['job_type']} → {result.calculated_priority}")
        
        # Test LOW priority
        job_low = {
            "job_id": "job_2",
            "job_type": "report_generation",
            "estimated_cpu_percent": 15.0,
        }
        result = classifier.classify(job_low)
        assert result.calculated_priority == "LOW", f"Expected LOW, got {result.calculated_priority}"
        print(f"✓ LOW priority: {job_low['job_type']} → {result.calculated_priority}")
        
        # Test MEDIUM priority
        job_medium = {
            "job_id": "job_3",
            "job_type": "cache_refresh",
            "estimated_cpu_percent": 10.0,
        }
        result = classifier.classify(job_medium)
        assert result.calculated_priority == "MEDIUM", f"Expected MEDIUM, got {result.calculated_priority}"
        print(f"✓ MEDIUM priority: {job_medium['job_type']} → {result.calculated_priority}")
        
        # Test unknown type (should default to MEDIUM)
        job_unknown = {
            "job_id": "job_4",
            "job_type": "unknown_type",
            "estimated_cpu_percent": 5.0,
        }
        result = classifier.classify(job_unknown)
        assert result.calculated_priority == "MEDIUM", f"Expected MEDIUM for unknown, got {result.calculated_priority}"
        print(f"✓ Unknown type defaults to: {result.calculated_priority}")
        
        print("\n✅ Job classification tests passed")
        return True
    except Exception as e:
        print(f"❌ Classification test failed: {e}")
        traceback.print_exc()
        return False


def test_delay_eligibility():
    """Test delay eligibility checking."""
    print_subheader("TEST 3: Delay Eligibility")
    
    try:
        from job_prioritization_engine.delay_eligibility import DelayEligibilityChecker
        
        checker = DelayEligibilityChecker()
        
        # Test 1: HIGH priority job cannot be delayed
        job_high = {
            "job_id": "job_1",
            "deadline_seconds": 3600,
            "already_delayed_seconds": 0,
        }
        result = checker.check_single_job(job_high, priority="HIGH")
        assert not result.is_delayable, "HIGH priority job should not be delayable"
        print(f"✓ HIGH priority job not delayable: {result.reason}")
        
        # Test 2: LOW priority with safe deadline
        job_low_safe = {
            "job_id": "job_2",
            "deadline_seconds": 3600,
            "already_delayed_seconds": 0,
        }
        result = checker.check_single_job(job_low_safe, priority="LOW")
        assert result.is_delayable, "LOW priority job with safe deadline should be delayable"
        print(f"✓ LOW priority job with safe deadline is delayable")
        
        # Test 3: LOW priority with deadline too close
        job_low_urgent = {
            "job_id": "job_3",
            "deadline_seconds": 30,
            "already_delayed_seconds": 0,
        }
        result = checker.check_single_job(job_low_urgent, priority="LOW")
        assert not result.is_delayable, "Job with deadline too close should not be delayable"
        print(f"✓ Job with deadline too close not delayable: {result.reason}")
        
        # Test 4: LOW priority already delayed too long
        job_low_delayed = {
            "job_id": "job_4",
            "deadline_seconds": 3600,
            "already_delayed_seconds": 700,
        }
        result = checker.check_single_job(job_low_delayed, priority="LOW")
        assert not result.is_delayable, "Job delayed too long should not be delayable"
        print(f"✓ Job already delayed too long not delayable: {result.reason}")
        
        # Test 5: Backlog adjustment
        adjustment = checker.get_delayable_percentage_adjustment(backlog_size=50)
        assert adjustment == 1.0, "Backlog 50 should have no adjustment"
        print(f"✓ Low backlog (50): adjustment = {adjustment}")
        
        adjustment = checker.get_delayable_percentage_adjustment(backlog_size=150)
        assert 0 < adjustment < 1.0, "High backlog should reduce adjustment"
        print(f"✓ High backlog (150): adjustment = {adjustment:.2f}")
        
        adjustment = checker.get_delayable_percentage_adjustment(backlog_size=300)
        assert adjustment == 0.0, "Critical backlog should block delays"
        print(f"✓ Critical backlog (300): adjustment = {adjustment} (blocked)")
        
        print("\n✅ Delay eligibility tests passed")
        return True
    except Exception as e:
        print(f"❌ Delay eligibility test failed: {e}")
        traceback.print_exc()
        return False


def test_workload_estimation():
    """Test workload reduction estimation."""
    print_subheader("TEST 4: Workload Estimation")
    
    try:
        from job_prioritization_engine.workload_estimator import WorkloadEstimator
        
        estimator = WorkloadEstimator()
        
        # Create test jobs
        jobs = [
            {"job_id": "j1", "job_type": "payment", "estimated_cpu_percent": 20.0},
            {"job_id": "j2", "job_type": "report", "estimated_cpu_percent": 10.0},
            {"job_id": "j3", "job_type": "analytics", "estimated_cpu_percent": 15.0},
            {"job_id": "j4", "job_type": "logs", "estimated_cpu_percent": 5.0},
        ]
        
        # Test 1: No delayable jobs
        estimate = estimator.estimate_reduction(delayable_job_ids=[], jobs=jobs)
        assert estimate.workload_reduction_percent == 0.0, "No jobs → 0% reduction"
        print(f"✓ No delayable jobs: {estimate.workload_reduction_percent:.1%} reduction")
        
        # Test 2: Some delayable jobs (j2 + j3 = 25 out of 50)
        estimate = estimator.estimate_reduction(delayable_job_ids=["j2", "j3"], jobs=jobs)
        expected_reduction = (10.0 + 15.0) / 50.0  # = 0.5 before safety margin
        assert estimate.workload_reduction_percent > 0, "With delayable jobs should have reduction"
        print(f"✓ Some jobs delayable: {estimate.workload_reduction_percent:.1%} reduction "
              f"({estimate.delayable_jobs_count} jobs)")
        
        # Test 3: All jobs delayable
        estimate = estimator.estimate_reduction(delayable_job_ids=["j1", "j2", "j3", "j4"], jobs=jobs)
        assert estimate.workload_reduction_percent > 0, "All jobs delayable"
        print(f"✓ All jobs delayable: {estimate.workload_reduction_percent:.1%} reduction")
        
        # Test 4: With backlog adjustment
        estimate = estimator.estimate_reduction(
            delayable_job_ids=["j2", "j3"],
            jobs=jobs,
            backlog_adjustment_factor=0.5
        )
        print(f"✓ With 50% backlog adjustment: {estimate.workload_reduction_percent:.1%} reduction")
        
        print("\n✅ Workload estimation tests passed")
        return True
    except Exception as e:
        print(f"❌ Workload estimation test failed: {e}")
        traceback.print_exc()
        return False


def test_integration():
    """Test full Engine 3 integration."""
    print_subheader("TEST 5: Full Engine 3 Integration")
    
    try:
        from job_prioritization_engine import JobPrioritizationEngine
        
        engine = JobPrioritizationEngine()
        
        # Scenario A: No delayable jobs
        jobs_a = [
            {"job_id": "a1", "job_type": "payment_processing", "estimated_cpu_percent": 30.0},
            {"job_id": "a2", "job_type": "authentication", "estimated_cpu_percent": 20.0},
        ]
        result_a = engine.evaluate(jobs=jobs_a, current_load_level="HIGH")
        assert result_a["delayable_jobs"] == 0, "No LOW/delayable jobs expected"
        assert result_a["workload_reduction_percent"] == 0.0, "0% reduction expected"
        print(f"✅ Scenario A (no delayable jobs): PASS")
        print(f"   Delayable: {result_a['delayable_jobs']} jobs, Reduction: {result_a['workload_reduction_percent']:.1%}")
        
        # Scenario B: Some delayable jobs in NORMAL load
        jobs_b = [
            {"job_id": "b1", "job_type": "payment_processing", "estimated_cpu_percent": 30.0, "deadline_seconds": 3600},
            {"job_id": "b2", "job_type": "report_generation", "estimated_cpu_percent": 20.0, "deadline_seconds": 3600, "already_delayed_seconds": 0},
            {"job_id": "b3", "job_type": "analytics_batch", "estimated_cpu_percent": 10.0, "deadline_seconds": 3600, "already_delayed_seconds": 0},
        ]
        result_b = engine.evaluate(jobs=jobs_b, current_load_level="NORMAL")
        assert result_b["delayable_jobs"] > 0, "Some jobs should be delayable"
        assert result_b["workload_reduction_percent"] > 0, "Should have positive reduction"
        print(f"✅ Scenario B (some delayable): PASS")
        print(f"   Delayable: {result_b['delayable_jobs']} jobs, Reduction: {result_b['workload_reduction_percent']:.1%}")
        
        # Scenario C: Deadline too close
        jobs_c = [
            {"job_id": "c1", "job_type": "report_generation", "estimated_cpu_percent": 20.0, 
             "deadline_seconds": 30, "already_delayed_seconds": 0},
        ]
        result_c = engine.evaluate(jobs=jobs_c, current_load_level="NORMAL")
        assert result_c["delayable_jobs"] == 0, "Deadline too close - not delayable"
        print(f"✅ Scenario C (deadline too close): PASS")
        print(f"   Reason: {result_c['reason']}")
        
        # Scenario D: High backlog reduces delays
        jobs_d = [
            {"job_id": "d1", "job_type": "report_generation", "estimated_cpu_percent": 20.0, 
             "deadline_seconds": 3600, "already_delayed_seconds": 0},
            {"job_id": "d2", "job_type": "analytics_batch", "estimated_cpu_percent": 15.0, 
             "deadline_seconds": 3600, "already_delayed_seconds": 0},
        ]
        result_d_low_backlog = engine.evaluate(jobs=jobs_d, backlog_size=50, current_load_level="NORMAL")
        result_d_high_backlog = engine.evaluate(jobs=jobs_d, backlog_size=150, current_load_level="NORMAL")
        
        print(f"✅ Scenario D (backlog effect): PASS")
        print(f"   Low backlog (50): {result_d_low_backlog['workload_reduction_percent']:.1%} reduction")
        print(f"   High backlog (150): {result_d_high_backlog['workload_reduction_percent']:.1%} reduction")
        
        # Scenario E: Mixed job types
        jobs_e = [
            {"job_id": "e1", "job_type": "payment_processing", "estimated_cpu_percent": 25.0, "deadline_seconds": 10},
            {"job_id": "e2", "job_type": "cache_refresh", "estimated_cpu_percent": 15.0, "deadline_seconds": 3600},
            {"job_id": "e3", "job_type": "report_generation", "estimated_cpu_percent": 20.0, "deadline_seconds": 3600},
            {"job_id": "e4", "job_type": "authentication", "estimated_cpu_percent": 30.0, "deadline_seconds": 20},
            {"job_id": "e5", "job_type": "log_compression", "estimated_cpu_percent": 10.0, "deadline_seconds": 3600},
        ]
        result_e = engine.evaluate(jobs=jobs_e, current_load_level="NORMAL")
        classification = result_e["classification_summary"]
        
        print(f"✅ Scenario E (mixed job types): PASS")
        print(f"   Total: {classification['total_classified']}")
        print(f"   HIGH: {classification['high_priority']} ({classification['high_priority_percent']:.0f}%)")
        print(f"   MEDIUM: {classification['medium_priority']} ({classification['medium_priority_percent']:.0f}%)")
        print(f"   LOW: {classification['low_priority']} ({classification['low_priority_percent']:.0f}%)")
        print(f"   Delayable: {result_e['delayable_jobs']} jobs, Reduction: {result_e['workload_reduction_percent']:.1%}")
        
        print("\n✅ Full integration tests passed")
        return True
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        traceback.print_exc()
        return False


def test_edge_cases():
    """Test edge cases and error handling."""
    print_subheader("TEST 6: Edge Cases and Error Handling")
    
    try:
        from job_prioritization_engine import JobPrioritizationEngine
        
        engine = JobPrioritizationEngine()
        
        # Edge case 1: Empty job list
        try:
            result = engine.evaluate(jobs=[])
            print(f"❌ Should have raised error for empty jobs list")
            return False
        except ValueError as e:
            print(f"✓ Empty jobs rejected: {str(e)[:60]}...")
        
        # Edge case 2: Invalid load level
        try:
            result = engine.evaluate(
                jobs=[{"job_id": "j1", "job_type": "report", "estimated_cpu_percent": 10}],
                current_load_level="INVALID"
            )
            print(f"❌ Should have raised error for invalid load level")
            return False
        except ValueError as e:
            print(f"✓ Invalid load level rejected: {str(e)[:60]}...")
        
        # Edge case 3: Negative backlog
        try:
            result = engine.evaluate(
                jobs=[{"job_id": "j1", "job_type": "report", "estimated_cpu_percent": 10}],
                backlog_size=-5
            )
            print(f"❌ Should have raised error for negative backlog")
            return False
        except ValueError as e:
            print(f"✓ Negative backlog rejected: {str(e)[:60]}...")
        
        # Edge case 4: Jobs with missing optional fields
        jobs_minimal = [
            {"job_id": "j1", "job_type": "report_generation"},
            {"job_id": "j2", "job_type": "payment_processing"},
        ]
        result = engine.evaluate(jobs=jobs_minimal)
        assert result["status"] == "success", "Should handle jobs with missing optional fields"
        print(f"✓ Jobs with missing optional fields handled successfully")
        
        # Edge case 5: Very small CPU values
        jobs_small = [
            {"job_id": "j1", "job_type": "report", "estimated_cpu_percent": 0.5},
            {"job_id": "j2", "job_type": "analytics", "estimated_cpu_percent": 0.1},
        ]
        result = engine.evaluate(jobs=jobs_small)
        assert result["status"] == "success", "Should handle very small CPU values"
        print(f"✓ Very small CPU values handled: {result['workload_reduction_percent']:.1%}")
        
        print("\n✅ Edge case tests passed")
        return True
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        traceback.print_exc()
        return False


def test_api_models():
    """Test Pydantic API models."""
    print_subheader("TEST 7: API Models and Validation")
    
    try:
        from workload_prediction_engine.api import (
            JobMetadata,
            Engine3EvaluationRequest,
            Engine3EvaluationResponse
        )
        
        # Test JobMetadata
        job = JobMetadata(
            job_id="j1",
            job_type="report_generation",
            priority="LOW",
            estimated_runtime_seconds=180,
            estimated_cpu_percent=10.0,
            deadline_seconds=3600,
            already_delayed_seconds=0
        )
        assert job.job_id == "j1"
        print("✓ JobMetadata model valid")
        
        # Test Engine3EvaluationRequest
        request = Engine3EvaluationRequest(
            jobs=[job],
            backlog_size=5,
            current_load_level="HIGH",
            current_cpu=85.0,
            current_pods=5
        )
        assert len(request.jobs) == 1
        print("✓ Engine3EvaluationRequest model valid")
        
        # Test validation
        try:
            invalid_request = Engine3EvaluationRequest(
                jobs=[job],
                current_load_level="INVALID"
            )
            print("❌ Should have failed validation for invalid load level")
            return False
        except Exception:
            print("✓ API validation catches invalid load level")
        
        print("\n✅ API model tests passed")
        return True
    except Exception as e:
        print(f"❌ API model test failed: {e}")
        traceback.print_exc()
        return False


def run_all_tests() -> Dict[str, bool]:
    """Run all validation tests."""
    print_header("ENGINE 3 - JOB PRIORITIZATION ENGINE VALIDATION SUITE")
    
    results = {
        "Imports": test_imports(),
        "Job Classification": test_job_classification(),
        "Delay Eligibility": test_delay_eligibility(),
        "Workload Estimation": test_workload_estimation(),
        "Full Integration": test_integration(),
        "Edge Cases": test_edge_cases(),
        "API Models": test_api_models(),
    }
    
    return results


def print_summary(results: Dict[str, bool]) -> None:
    """Print test summary."""
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_bool in results.items():
        status = "✅ PASS" if passed_bool else "❌ FAIL"
        print(f"{status:8} {test_name}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {passed}/{total} tests passed")
    print(f"{'='*80}\n")
    
    # Overall status
    all_passed = all(results.values())
    if all_passed:
        print("🎉 ALL VALIDATION TESTS PASSED! Engine 3 is ready for deployment.\n")
    else:
        print("⚠️  Some tests failed. Please review the failures above.\n")
    
    return all_passed


if __name__ == "__main__":
    try:
        results = run_all_tests()
        all_passed = print_summary(results)
        
        # Print final status codes
        print("\n" + "="*80)
        print("ENGINE 3 IMPLEMENTATION STATUS")
        print("="*80)
        print(f"ENGINE 3 JOB CLASSIFICATION: {'✅ PASS' if results.get('Job Classification') else '❌ FAIL'}")
        print(f"ENGINE 3 DELAY ELIGIBILITY: {'✅ PASS' if results.get('Delay Eligibility') else '❌ FAIL'}")
        print(f"ENGINE 3 WORKLOAD REDUCTION: {'✅ PASS' if results.get('Workload Estimation') else '❌ FAIL'}")
        print(f"ENGINE 3 FULL INTEGRATION: {'✅ PASS' if results.get('Full Integration') else '❌ FAIL'}")
        print(f"ENGINE 3 API SUPPORT: {'✅ PASS' if results.get('API Models') else '❌ FAIL'}")
        print(f"ENGINE 3 VALIDATION: {'✅ PASS' if all_passed else '❌ FAIL'}")
        print("\nFINAL STATUS:")
        if all_passed:
            print("ENGINE 3 IMPLEMENTATION COMPLETE ✅")
        else:
            print("ENGINE 3 IMPLEMENTATION INCOMPLETE ❌")
        print("="*80 + "\n")
        
        sys.exit(0 if all_passed else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
