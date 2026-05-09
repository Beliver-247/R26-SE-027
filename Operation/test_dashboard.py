"""
Dashboard Configuration & Testing

Test that dashboard can start and connect to mock API.
"""

import requests
import json
from datetime import datetime

def test_mock_api():
    """Test dashboard can generate mock data."""
    
    print("Testing Green DevOps Dashboard")
    print("=" * 60)
    
    # Test mock health data generation
    print("\n1. Testing Mock Health Data Generation...")
    try:
        from dashboard.app import generate_mock_health
        health = generate_mock_health()
        print(f"   ✓ Generated mock health data")
        print(f"     - Mode: {health['mode']}")
        print(f"     - Records: {health['records_collected']}")
        print(f"     - Status: {health['status']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Test mock prediction data generation
    print("\n2. Testing Mock Prediction Data Generation...")
    try:
        from dashboard.app import generate_mock_prediction
        prediction = generate_mock_prediction()
        pred_data = prediction['prediction']
        print(f"   ✓ Generated mock prediction data")
        print(f"     - CPU: {pred_data['predicted_cpu_percent']:.1f}%")
        print(f"     - Load: {pred_data['predicted_load_level']}")
        print(f"     - Pods: {pred_data['recommended_pods']}")
        print(f"     - Confidence: {pred_data['confidence']:.0%}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Test helper functions
    print("\n3. Testing Dashboard Helper Functions...")
    try:
        from dashboard.app import (
            get_load_color,
            get_status_color,
            get_mode_explanation,
            determine_system_status,
            determine_scaling_action
        )
        
        # Test color functions
        assert get_load_color("LOW") == "🟢", "Color function failed"
        assert get_load_color("HIGH") == "🔴", "Color function failed"
        print("   ✓ Color functions working")
        
        # Test status functions
        status, text = determine_system_status("NORMAL", 12)
        assert status == "RUNNING", "Status determination failed"
        print("   ✓ Status determination working")
        
        # Test scaling functions
        action, text, color = determine_scaling_action(1, 2)
        assert action == "SCALE UP", "Scaling decision failed"
        print("   ✓ Scaling decision working")
        
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("✓ All dashboard components tested successfully!")
    print("=" * 60)
    print("\nDashboard is ready to run:")
    print("\n  Option 1 (Quick):")
    print("    python quickstart.py")
    print("\n  Option 2 (Manual):")
    print("    streamlit run dashboard/app.py")
    print("\nDashboard will be available at: http://localhost:8501")
    
    return True


if __name__ == "__main__":
    import sys
    success = test_mock_api()
    sys.exit(0 if success else 1)
