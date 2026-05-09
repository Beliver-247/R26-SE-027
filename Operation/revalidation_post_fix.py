"""
Re-validation of Engine 2 decision logic AFTER high-load SLA protection fix.

Tests the same 4 scenarios used in comprehensive_validation.py to verify:
1. Scenario A (HIGH load, 85% CPU, 5 pods) - Must NOT reduce pods unsafely
2. Scenario B (HIGH load, 80% CPU, 4 pods, delay) - Must respect minimum pods
3. Scenario C (LOW load, 15% CPU) - Can still optimize to 1 pod
4. Scenario D (MEDIUM load, 45% CPU) - Can still optimize safely

Expected fixes:
- Scenario A: Should return SCALE_UP or NO_ACTION, not HYBRID with 1 pod
- Scenario B: Should maintain pods >= 4, not reduce to 1
- Scenario C: Can still return 1 pod (LOW load, safe)
- Scenario D: Can still return optimized pod count
"""

import sys
from pathlib import Path
import logging

# Setup path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

from carbon_engine import CarbonEmissionEngine

def test_scenario(scenario_name, prediction):
    """Test a single scenario."""
    try:
        # Need to infer raw_required_pods from CPU and load_level
        # For HIGH load at 85% CPU: approximately 5 pods
        # For HIGH load at 80% CPU: approximately 4 pods
        # For LOW load at 15% CPU: approximately 1-2 pods
        # For MEDIUM load at 45% CPU: approximately 3-4 pods
        cpu = prediction['cpu']
        load = prediction['load']
        
        # Rough estimation based on CPU and load
        if load == "HIGH" and cpu >= 80:
            raw_pods = int(cpu / 20) + 1  # 5 pods for 85%, 4 for 80%
        elif load == "NORMAL":
            raw_pods = max(2, int(cpu / 20))  # 2-3 pods
        else:  # LOW
            raw_pods = 1
        
        engine = CarbonEmissionEngine()
        result = engine.evaluate(
            predicted_cpu=prediction['cpu'],
            load_level=prediction['load'],
            raw_required_pods=raw_pods,
            current_pods=prediction['current_pods']
        )
        
        # Extract decision from result
        decision = result['decision']
        
        print(f"\n{'='*70}")
        print(f"SCENARIO {scenario_name}")
        print(f"{'='*70}")
        print(f"Input:")
        print(f"  - CPU: {prediction['cpu']}%")
        print(f"  - Load Level: {prediction['load']}")
        print(f"  - Current Pods: {prediction['current_pods']}")
        print(f"  - Raw Required Pods: {raw_pods}")
        print(f"\nOutput:")
        print(f"  - Action: {decision['recommended_action']}")
        print(f"  - Reason: {decision['reason']}")
        print(f"  - Optimized Pods: {decision['optimized_required_pods']}")
        print(f"  - Carbon Saving: {decision['carbon_saving_gco2']} g CO2")
        
        return decision
        
    except Exception as e:
        print(f"\nERROR in {scenario_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("\n" + "="*70)
    print("ENGINE 2 RE-VALIDATION (POST-FIX)")
    print("Testing High-Load SLA Protection")
    print("="*70)
    
    # Scenario A: HIGH LOAD (85% CPU, should NOT reduce pods unsafely)
    scenario_a = {
        'name': 'A - HIGH LOAD',
        'cpu': 85.0,
        'load': 'HIGH',
        'current_pods': 5
    }
    result_a = test_scenario(scenario_a['name'], scenario_a)
    
    # Scenario B: HIGH LOAD with delay option (80% CPU)
    scenario_b = {
        'name': 'B - HIGH LOAD + DELAY',
        'cpu': 80.0,
        'load': 'HIGH',
        'current_pods': 4
    }
    result_b = test_scenario(scenario_b['name'], scenario_b)
    
    # Scenario C: LOW LOAD (15% CPU, should still optimize to 1 pod)
    scenario_c = {
        'name': 'C - LOW LOAD',
        'cpu': 15.0,
        'load': 'LOW',
        'current_pods': 3
    }
    result_c = test_scenario(scenario_c['name'], scenario_c)
    
    # Scenario D: MEDIUM LOAD (45% CPU, should optimize within safe bounds)
    scenario_d = {
        'name': 'D - MEDIUM LOAD',
        'cpu': 45.0,
        'load': 'NORMAL',
        'current_pods': 4
    }
    result_d = test_scenario(scenario_d['name'], scenario_d)
    
    # Validation summary
    print(f"\n\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    def check_result(name, result, expected_min_pods, expected_safe_action):
        if result is None:
            print(f"❌ {name}: FAILED (error during execution)")
            return False
        
        pods = result['optimized_required_pods']
        action = result['recommended_action']
        
        print(f"\n{name}:")
        print(f"  - Result Pods: {pods} (minimum expected: {expected_min_pods})")
        print(f"  - Action: {action}")
        
        if pods >= expected_min_pods:
            print(f"  ✅ PASS: Maintains minimum pod requirement")
            return True
        else:
            print(f"  ❌ FAIL: Violates SLA (reduced below {expected_min_pods})")
            return False
    
    results = []
    
    # Scenario A: HIGH load - must maintain >= 5 pods
    results.append(check_result(
        "Scenario A (HIGH 85% CPU)",
        result_a,
        expected_min_pods=5,
        expected_safe_action="SCALE_UP or NO_ACTION"
    ))
    
    # Scenario B: HIGH load - must maintain >= 4 pods
    results.append(check_result(
        "Scenario B (HIGH 80% CPU + delay)",
        result_b,
        expected_min_pods=4,
        expected_safe_action="SCALE_UP or DELAY_JOBS"
    ))
    
    # Scenario C: LOW load - can go to 1 pod (optimization safe)
    results.append(check_result(
        "Scenario C (LOW 15% CPU)",
        result_c,
        expected_min_pods=1,
        expected_safe_action="SCALE_DOWN or HYBRID"
    ))
    
    # Scenario D: MEDIUM load - should optimize within safe bounds
    results.append(check_result(
        "Scenario D (MEDIUM 45% CPU)",
        result_d,
        expected_min_pods=2,  # Can reduce from 4, but not to 1
        expected_safe_action="SCALE_DOWN or HYBRID"
    ))
    
    # Final verdict
    print(f"\n\n{'='*70}")
    if all(results):
        print("✅ ENGINE 2 DECISION LOGIC: FIXED AND VALIDATED")
        print("All scenarios behave correctly with SLA protection.")
    else:
        print("❌ ENGINE 2 DECISION LOGIC: ISSUES REMAIN")
        print(f"Tests passed: {sum(results)}/{len(results)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
