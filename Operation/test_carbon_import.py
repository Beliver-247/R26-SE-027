#!/usr/bin/env python3
"""Test carbon engine import."""

import sys
import os

# Add src directory to path like the API does
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Python path:")
for p in sys.path[:5]:
    print(f"  {p}")

try:
    print("\nTrying: from carbon_engine import CarbonEmissionEngine")
    from carbon_engine import CarbonEmissionEngine
    print("✓ Success!")
    engine = CarbonEmissionEngine()
    print(f"✓ Engine created: {engine}")
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()
