"""
Unified Dashboard Verification Script

Verifies that the refactoring was successful and all dashboards work.
"""

import sys
import subprocess
from pathlib import Path


def test_imports():
    """Test that all render functions can be imported."""
    print("\n" + "="*80)
    print("TESTING IMPORTS")
    print("="*80)
    
    tests = [
        ("dashboard.app", "render_overview"),
        ("dashboard.technical_app", "render_technical"),
        ("dashboard.unified_app", "main"),
    ]
    
    all_passed = True
    
    for module, func in tests:
        try:
            mod = __import__(module, fromlist=[func])
            if hasattr(mod, func):
                print(f"✓ {module}.{func}")
            else:
                print(f"✗ {module}.{func} - Function not found")
                all_passed = False
        except ImportError as e:
            print(f"✗ {module} - Import failed: {e}")
            all_passed = False
    
    return all_passed


def test_syntax():
    """Test Python syntax of all dashboards."""
    print("\n" + "="*80)
    print("TESTING SYNTAX")
    print("="*80)
    
    files = [
        "dashboard/app.py",
        "dashboard/technical_app.py",
        "dashboard/unified_app.py",
    ]
    
    all_passed = True
    
    for file in files:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", file],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                size = Path(file).stat().st_size
                print(f"✓ {file:40} ({size:,} bytes)")
            else:
                print(f"✗ {file} - Syntax error: {result.stderr.decode()}")
                all_passed = False
        except subprocess.TimeoutExpired:
            print(f"✗ {file} - Compilation timeout")
            all_passed = False
        except Exception as e:
            print(f"✗ {file} - Error: {e}")
            all_passed = False
    
    return all_passed


def test_functions_exist():
    """Verify that render functions are exported."""
    print("\n" + "="*80)
    print("TESTING FUNCTION EXPORTS")
    print("="*80)
    
    try:
        # Test Level 1
        from dashboard.app import render_overview, main
        print("✓ dashboard.app exports: render_overview(), main()")
        
        # Test Level 2
        from dashboard.technical_app import render_technical, main as technical_main
        print("✓ dashboard.technical_app exports: render_technical(), main()")
        
        # Test Unified
        from dashboard.unified_app import main as unified_main
        print("✓ dashboard.unified_app exports: main()")
        
        return True
    except Exception as e:
        print(f"✗ Export test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "="*80)
    print("UNIFIED DASHBOARD VERIFICATION")
    print("="*80)
    
    sys.path.insert(0, str(Path.cwd()))
    
    results = {
        "Syntax Check": test_syntax(),
        "Function Exports": test_functions_exist(),
        "Import Test": test_imports(),
    }
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:30} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Dashboards are ready")
        print("\nQuick Start:")
        print("  Terminal 1: python run_live_api.py")
        print("  Terminal 2: streamlit run dashboard/unified_app.py --server.port 8503")
        print("\nOr run individual dashboards:")
        print("  streamlit run dashboard/app.py --server.port 8501")
        print("  streamlit run dashboard/technical_app.py --server.port 8502")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
    
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
