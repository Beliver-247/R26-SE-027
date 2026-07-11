#!/usr/bin/env python3
"""
Comprehensive validation test for Engine 2 upgrade.

Tests the new Engine 3 support and raw vs optimized scenario comparison.

Scenarios:
- A: Raw only (no Engine 3 data)
- B: High load + Engine 3 support (SLA protection must work)
- C: Low load + Engine 3 support (optimization allowed)
- D: Medium load + Engine 3 support (balanced)
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from carbon_engine.carbon_engine import CarbonEmissionEngine


def format_section(title: str, char: str = "=") -> str:
    """Format a section header."""
    return f"\n{char * 80}\n{title}\n{char * 80}\n"


def test_scenario_a():
    """
    Scenario A: Raw only (no Engine 3 data)
    
    Engine 2 should:
    - Return raw scenario
    - Show no optimized scenario
    - Calculate energy and carbon correctly
    """
    print(format_section("SCENARIO A: Raw Only (No Engine 3 Data)", "─"))
    
    engine = CarbonEmissionEngine()
    
    result = engine.evaluate(
        predicted_cpu=45.0,
        load_level="NORMAL",
        raw_required_pods=3,
        current_pods=3,
        prediction_window_seconds=30,
        delayable_jobs=None,
        workload_reduction_percent=None
    )
    
    # Verify output structure
    assert "raw_scenario" in result, "Missing raw_scenario in output"
    assert "optimized_scenario" in result, "Missing optimized_scenario in output"
    assert result["optimized_scenario"] is None, "optimized_scenario should be None when no Engine 3 data"
    assert result["raw_scenario"]["required_pods"] == 3, "Raw scenario pods mismatch"
    
    print(f"✓ Raw scenario pods: {result['raw_scenario']['required_pods']}")
    print(f"✓ Raw scenario energy: {result['raw_scenario']['estimated_energy_kwh']:.6f} kWh")
    print(f"✓ Raw scenario carbon: {result['raw_scenario']['estimated_carbon_gco2']:.2f} g CO2")
    print(f"✓ Optimized scenario: {result['optimized_scenario']}")
    print(f"✓ Carbon saving: {result['carbon_saving_gco2']:.2f} g CO2 ({result['carbon_saving_percent']:.1f}%)")
    
    return True


def test_scenario_b():
    """
    Scenario B: High load + Engine 3 support
    
    Engine 2 should:
    - Show both raw (5 pods) and optimized (3 pods) scenarios
    - But SLA protection: final decision must remain safe (≥ 5 pods during HIGH load)
    - Demonstrate that optimized scenario EXISTS but is not selected due to SLA
    
    Input:
    - predicted_cpu = 85%
    - load_level = HIGH
    - raw_required_pods = 5
    - workload_reduction_percent = 0.4 (40% can be delayed)
    Expected:
    - raw scenario = 5 pods
    - optimized scenario = 3 pods (5 * 0.6 = 3)
    - final recommendation = maintain 5 pods (SLA safe)
    """
    print(format_section("SCENARIO B: High Load + Engine 3 Support (SLA Protection)", "─"))
    
    engine = CarbonEmissionEngine()
    
    result = engine.evaluate(
        predicted_cpu=85.0,
        load_level="HIGH",
        raw_required_pods=5,
        current_pods=2,
        prediction_window_seconds=30,
        delayable_jobs=4,
        workload_reduction_percent=0.4
    )
    
    # Verify structures exist
    assert "raw_scenario" in result, "Missing raw_scenario"
    assert "optimized_scenario" in result, "Missing optimized_scenario"
    assert result["optimized_scenario"] is not None, "optimized_scenario should exist when Engine 3 data provided"
    
    raw_pods = result["raw_scenario"]["required_pods"]
    opt_pods = result["optimized_scenario"]["required_pods"]
    final_pods = result["optimized_required_pods"]
    
    print(f"✓ Raw scenario pods: {raw_pods}")
    print(f"✓ Raw scenario carbon: {result['raw_scenario']['estimated_carbon_gco2']:.2f} g CO2")
    print(f"✓ Optimized scenario pods: {opt_pods}")
    print(f"✓ Optimized scenario carbon: {result['optimized_scenario']['estimated_carbon_gco2']:.2f} g CO2")
    print(f"✓ Workload reduction: {result['optimized_scenario']['workload_reduction_percent']:.1%}")
    print(f"✓ Delayable jobs: {result['optimized_scenario']['delayable_jobs']}")
    print(f"✓ Final decision pods: {final_pods}")
    print(f"✓ Action: {result['recommended_action']}")
    
    # Critical checks
    assert raw_pods == 5, f"Raw scenario should be 5 pods, got {raw_pods}"
    assert opt_pods == 3, f"Optimized scenario should be 3 pods (5*0.6), got {opt_pods}"
    assert final_pods >= raw_pods, (
        f"SLA PROTECTION FAILED: Final pods ({final_pods}) < raw pods ({raw_pods}) during HIGH LOAD"
    )
    
    print(f"\n✓ SLA PROTECTION ACTIVE: Final decision ({final_pods} pods) >= raw requirement ({raw_pods} pods)")
    print(f"  Reason: {result['reason']}")
    
    return True


def test_scenario_c():
    """
    Scenario C: Low load + Engine 3 support
    
    Engine 2 should:
    - Allow optimization (no HIGH load protection)
    - Select optimized scenario over raw
    - Show significant carbon savings
    
    Input:
    - predicted_cpu = 20%
    - load_level = LOW
    - raw_required_pods = 2
    - workload_reduction_percent = 0.5 (50% can be delayed)
    Expected:
    - raw scenario = 2 pods
    - optimized scenario = ceil(2 * 0.5) = 1 pod
    - final decision = 1 pod (optimization allowed)
    - carbon savings = 50% + pod reduction benefit
    """
    print(format_section("SCENARIO C: Low Load + Engine 3 Support (Optimization Allowed)", "─"))
    
    engine = CarbonEmissionEngine()
    
    result = engine.evaluate(
        predicted_cpu=20.0,
        load_level="LOW",
        raw_required_pods=2,
        current_pods=2,
        prediction_window_seconds=30,
        delayable_jobs=5,
        workload_reduction_percent=0.5
    )
    
    raw_pods = result["raw_scenario"]["required_pods"]
    opt_pods = result["optimized_scenario"]["required_pods"]
    final_pods = result["optimized_required_pods"]
    
    print(f"✓ Raw scenario pods: {raw_pods}")
    print(f"✓ Raw scenario carbon: {result['raw_scenario']['estimated_carbon_gco2']:.2f} g CO2")
    print(f"✓ Optimized scenario pods: {opt_pods}")
    print(f"✓ Optimized scenario carbon: {result['optimized_scenario']['estimated_carbon_gco2']:.2f} g CO2")
    print(f"✓ Workload reduction: {result['optimized_scenario']['workload_reduction_percent']:.1%}")
    print(f"✓ Final decision pods: {final_pods}")
    print(f"✓ Carbon saving: {result['carbon_saving_gco2']:.2f} g CO2 ({result['carbon_saving_percent']:.1f}%)")
    print(f"✓ Action: {result['recommended_action']}")
    
    # Critical checks
    assert raw_pods == 2, f"Raw scenario should be 2 pods, got {raw_pods}"
    assert opt_pods == 1, f"Optimized scenario should be 1 pod (ceil(2*0.5)), got {opt_pods}"
    assert final_pods <= raw_pods, (
        f"Optimization should be allowed: final ({final_pods}) <= raw ({raw_pods})"
    )
    
    print(f"\n✓ OPTIMIZATION ACTIVE: Final decision ({final_pods} pods) <= raw ({raw_pods}) during LOW LOAD")
    
    return True


def test_scenario_d():
    """
    Scenario D: Medium load + Engine 3 support
    
    Engine 2 should:
    - Allow significant optimization
    - Balance performance and carbon
    
    Input:
    - predicted_cpu = 50%
    - load_level = NORMAL
    - raw_required_pods = 4
    - workload_reduction_percent = 0.3 (30% can be delayed)
    Expected:
    - raw scenario = 4 pods
    - optimized scenario = ceil(4 * 0.7) = 3 pods
    - final decision = 3 pods (optimization beneficial and safe)
    """
    print(format_section("SCENARIO D: Medium Load + Engine 3 Support (Balanced)", "─"))
    
    engine = CarbonEmissionEngine()
    
    result = engine.evaluate(
        predicted_cpu=50.0,
        load_level="NORMAL",
        raw_required_pods=4,
        current_pods=4,
        prediction_window_seconds=30,
        delayable_jobs=8,
        workload_reduction_percent=0.3
    )
    
    raw_pods = result["raw_scenario"]["required_pods"]
    opt_pods = result["optimized_scenario"]["required_pods"]
    final_pods = result["optimized_required_pods"]
    
    print(f"✓ Raw scenario pods: {raw_pods}")
    print(f"✓ Raw scenario carbon: {result['raw_scenario']['estimated_carbon_gco2']:.2f} g CO2")
    print(f"✓ Optimized scenario pods: {opt_pods}")
    print(f"✓ Optimized scenario carbon: {result['optimized_scenario']['estimated_carbon_gco2']:.2f} g CO2")
    print(f"✓ Workload reduction: {result['optimized_scenario']['workload_reduction_percent']:.1%}")
    print(f"✓ Final decision pods: {final_pods}")
    print(f"✓ Carbon saving: {result['carbon_saving_gco2']:.2f} g CO2 ({result['carbon_saving_percent']:.1f}%)")
    print(f"✓ Action: {result['recommended_action']}")
    
    # Critical checks
    assert raw_pods == 4, f"Raw scenario should be 4 pods, got {raw_pods}"
    assert opt_pods == 3, f"Optimized scenario should be 3 pods (ceil(4*0.7)), got {opt_pods}"
    
    print(f"\n✓ BALANCED DECISION: Raw {raw_pods} → Optimized {opt_pods} → Final {final_pods}")
    
    return True


def test_api_compatibility():
    """Test that the API changes are compatible."""
    print(format_section("API Compatibility Check", "─"))
    
    # Test with the new 0-1 float format
    engine = CarbonEmissionEngine()
    
    # This should work with 0-1 float
    result = engine.evaluate(
        predicted_cpu=45.0,
        load_level="NORMAL",
        raw_required_pods=3,
        current_pods=3,
        prediction_window_seconds=30,
        delayable_jobs=5,
        workload_reduction_percent=0.25  # 0-1 float format
    )
    
    print(f"✓ Engine 2 accepts workload_reduction_percent as 0-1 float (0.25 = 25%)")
    print(f"✓ Processed workload reduction: {result['optimized_scenario']['workload_reduction_percent']:.1%}")
    
    # Verify it rejects invalid values
    try:
        result = engine.evaluate(
            predicted_cpu=45.0,
            load_level="NORMAL",
            raw_required_pods=3,
            current_pods=3,
            prediction_window_seconds=30,
            workload_reduction_percent=1.5  # Invalid: > 1.0
        )
        print("✗ Engine 2 should reject workload_reduction_percent > 1.0")
        return False
    except ValueError as e:
        print(f"✓ Engine 2 correctly rejects invalid workload_reduction_percent: {str(e)[:50]}...")
    
    return True


def print_summary(results: dict):
    """Print validation summary."""
    print(format_section("VALIDATION SUMMARY", "="))
    
    print("Test Results:")
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    all_passed = all(results.values())
    
    print(format_section("UPGRADE STATUS", "="))
    
    print("ENGINE 2 RAW SCENARIO SUPPORT: " + ("PASS ✅" if results.get("Scenario A", False) else "FAIL ❌"))
    print("ENGINE 2 ENGINE-3 SUPPORT: " + ("PASS ✅" if all([results.get(f"Scenario {s}", False) for s in "BCD"]) else "FAIL ❌"))
    print("RAW VS OPTIMIZED COMPARISON: " + ("PASS ✅" if all([results.get(f"Scenario {s}", False) for s in "BCD"]) else "FAIL ❌"))
    print("SLA SAFETY PRESERVED: " + ("PASS ✅" if results.get("Scenario B", False) else "FAIL ❌"))
    print("API SUPPORT UPDATED: " + ("PASS ✅" if results.get("API Compatibility", False) else "FAIL ❌"))
    
    print("\nFINAL STATUS:")
    if all_passed:
        print("ENGINE 2 UPGRADE COMPLETE ✅")
        print("\nEngine 2 now supports:")
        print("  ✓ Raw scenario calculation (Engine 1 data only)")
        print("  ✓ Optimized scenario calculation (with Engine 3 workload reduction)")
        print("  ✓ Explicit raw vs optimized scenario comparison")
        print("  ✓ SLA-aware decision with HIGH LOAD protection")
        print("  ✓ 0-1 float workload_reduction_percent format")
        print("  ✓ Clear carbon saving metrics and reasoning")
    else:
        print("ENGINE 2 UPGRADE FAILED ❌")
        print("\nPlease review failed tests above.")
    
    return all_passed


if __name__ == "__main__":
    print(format_section("ENGINE 2 UPGRADE VALIDATION", "="))
    print("Testing Engine 2 with Engine 3 support")
    print("Date: April 18, 2026")
    print("Version: 2.1")
    
    results = {}
    
    try:
        results["Scenario A"] = test_scenario_a()
    except Exception as e:
        print(f"✗ Scenario A failed: {e}")
        results["Scenario A"] = False
    
    try:
        results["Scenario B"] = test_scenario_b()
    except Exception as e:
        print(f"✗ Scenario B failed: {e}")
        results["Scenario B"] = False
    
    try:
        results["Scenario C"] = test_scenario_c()
    except Exception as e:
        print(f"✗ Scenario C failed: {e}")
        results["Scenario C"] = False
    
    try:
        results["Scenario D"] = test_scenario_d()
    except Exception as e:
        print(f"✗ Scenario D failed: {e}")
        results["Scenario D"] = False
    
    try:
        results["API Compatibility"] = test_api_compatibility()
    except Exception as e:
        print(f"✗ API Compatibility test failed: {e}")
        results["API Compatibility"] = False
    
    all_passed = print_summary(results)
    
    sys.exit(0 if all_passed else 1)
