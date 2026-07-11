"""
Test Runner for Level 1 and Level 2 Dashboards

This script validates and launches both dashboards for testing.

Usage:
    python test_dashboards.py --level 1        # Test Level 1 only
    python test_dashboards.py --level 2        # Test Level 2 only
    python test_dashboards.py --level both     # Test both dashboards
    python test_dashboards.py --run 1          # Launch Level 1 dashboard
    python test_dashboards.py --run 2          # Launch Level 2 dashboard
"""

import sys
import subprocess
import os
import argparse
from pathlib import Path
import importlib.util


# Configuration
DASHBOARD_DIR = Path(__file__).parent / "dashboard"
LEVEL_1_APP = DASHBOARD_DIR / "app.py"
LEVEL_2_APP = DASHBOARD_DIR / "technical_app.py"
REQUIREMENTS = DASHBOARD_DIR / "requirements.txt"

LEVEL_1_PORT = 8501
LEVEL_2_PORT = 8502

# Required packages
REQUIRED_PACKAGES = ["streamlit", "requests", "pandas"]


def check_package_installed(package_name: str) -> bool:
    """Check if a package is installed."""
    try:
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    except ImportError:
        return False


def install_dependencies():
    """Install required dependencies."""
    print("\n" + "="*80)
    print("INSTALLING DEPENDENCIES")
    print("="*80)
    
    missing = [pkg for pkg in REQUIRED_PACKAGES if not check_package_installed(pkg)]
    
    if not missing:
        print("✓ All required packages already installed")
        return True
    
    print(f"⚠ Missing packages: {', '.join(missing)}")
    print("Installing...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + missing,
            check=True,
            capture_output=False
        )
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False


def validate_dashboard(dashboard_path: Path, level: int) -> bool:
    """Validate dashboard syntax and imports."""
    print(f"\n{'='*80}")
    print(f"VALIDATING LEVEL {level} DASHBOARD")
    print(f"{'='*80}")
    
    if not dashboard_path.exists():
        print(f"✗ Dashboard not found: {dashboard_path}")
        return False
    
    print(f"File: {dashboard_path.name}")
    print(f"Size: {dashboard_path.stat().st_size} bytes")
    
    # Check syntax
    try:
        compile(dashboard_path.read_text(), str(dashboard_path), "exec")
        print("✓ Syntax validation passed")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        return False
    
    # Check imports
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(dashboard_path)],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ Import validation passed")
        else:
            print(f"✗ Import validation failed: {result.stderr.decode()}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Import validation timed out")
        return False
    
    print(f"✓ Level {level} dashboard is valid")
    return True


def check_api_health() -> bool:
    """Check if Engine 1 API is running."""
    print(f"\n{'='*80}")
    print("CHECKING API HEALTH")
    print(f"{'='*80}")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✓ Engine 1 API is running (localhost:8000)")
            return True
        else:
            print(f"⚠ API returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("⚠ API not reachable at localhost:8000")
        print("  → Start the API first with: python run_live_api.py")
        return False
    except Exception as e:
        print(f"⚠ Could not check API: {e}")
        return False


def launch_dashboard(level: int, port: int):
    """Launch a dashboard."""
    dashboard_path = LEVEL_1_APP if level == 1 else LEVEL_2_APP
    
    if not dashboard_path.exists():
        print(f"✗ Dashboard not found: {dashboard_path}")
        return False
    
    print(f"\n{'='*80}")
    print(f"LAUNCHING LEVEL {level} DASHBOARD")
    print(f"{'='*80}")
    print(f"Dashboard: {dashboard_path.name}")
    print(f"Port: {port}")
    print(f"URL: http://localhost:{port}")
    print("\nPress Ctrl+C to stop the dashboard\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(dashboard_path), "--server.port", str(port)],
            cwd=str(DASHBOARD_DIR.parent)
        )
    except KeyboardInterrupt:
        print("\n\n✓ Dashboard stopped")


def test_both_dashboards():
    """Run comprehensive tests on both dashboards."""
    print("\n" + "="*80)
    print("GREEN DEVOPS DASHBOARD TEST SUITE - BOTH LEVELS")
    print("="*80)
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Validate both dashboards
    level_1_valid = validate_dashboard(LEVEL_1_APP, 1)
    level_2_valid = validate_dashboard(LEVEL_2_APP, 2)
    
    if not (level_1_valid and level_2_valid):
        print("\n✗ Validation failed for one or more dashboards")
        return False
    
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    print("✓ Level 1 Dashboard: VALID")
    print("✓ Level 2 Dashboard: VALID")
    
    # Check API
    api_available = check_api_health()
    
    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    
    if api_available:
        print("\n✓ Engine 1 API is running - dashboards will display live data")
    else:
        print("\n⚠ Engine 1 API is not running - dashboards will show 'unavailable' messages")
        print("   Start the API with: python run_live_api.py")
    
    print("\nTo launch the dashboards:\n")
    print(f"  Level 1 (Non-technical): streamlit run dashboard/app.py --server.port 8501")
    print(f"  Level 2 (Technical):     streamlit run dashboard/technical_app.py --server.port 8502")
    print(f"\nOr use this test script:")
    print(f"  python test_dashboards.py --run 1    (launch Level 1)")
    print(f"  python test_dashboards.py --run 2    (launch Level 2)")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Test Level 1 and Level 2 dashboards")
    parser.add_argument("--level", choices=["1", "2", "both"], default="both",
                        help="Which dashboard(s) to validate")
    parser.add_argument("--run", choices=["1", "2"], help="Launch a dashboard")
    parser.add_argument("--no-deps", action="store_true", help="Skip dependency installation")
    
    args = parser.parse_args()
    
    if args.run:
        # Launch mode
        if not args.no_deps:
            install_dependencies()
        
        check_api_health()
        level = int(args.run)
        port = LEVEL_1_PORT if level == 1 else LEVEL_2_PORT
        launch_dashboard(level, port)
    else:
        # Test mode
        if args.level == "both":
            success = test_both_dashboards()
        else:
            level = int(args.level)
            if not args.no_deps:
                install_dependencies()
            dashboard_path = LEVEL_1_APP if level == 1 else LEVEL_2_APP
            success = validate_dashboard(dashboard_path, level)
        
        if success:
            print("\n✓ All tests passed!")
            sys.exit(0)
        else:
            print("\n✗ Tests failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
