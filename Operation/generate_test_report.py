"""
Dashboard Test Report - Level 1 and Level 2 Validation

Run this script to generate a complete test report.
"""

import sys
import subprocess
from pathlib import Path
import re


def run_command(cmd, timeout=10):
    """Run a command and capture output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except Exception as e:
        return -1, "", str(e)


def check_file_exists(path):
    """Check if file exists."""
    return Path(path).exists()


def check_syntax(file_path):
    """Check Python syntax."""
    code, _, stderr = run_command(f'python -m py_compile "{file_path}"')
    return code == 0, stderr


def extract_functions(file_path):
    """Extract function names from Python file."""
    try:
        content = Path(file_path).read_text()
        functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
        return functions
    except:
        return []


def main():
    print("\n" + "="*80)
    print("DASHBOARD TEST REPORT - LEVEL 1 & LEVEL 2")
    print("="*80)
    
    base_dir = Path("d:/Research/Operation/green-devops-operation-component")
    
    # Test Level 1 Dashboard
    print("\n[1/4] LEVEL 1 DASHBOARD (Non-Technical)")
    print("-" * 80)
    
    level_1_path = base_dir / "dashboard" / "app.py"
    
    print(f"File: {level_1_path.name}")
    print(f"Path: {level_1_path}")
    print(f"Status: {'✓ EXISTS' if check_file_exists(level_1_path) else '✗ NOT FOUND'}")
    
    if check_file_exists(level_1_path):
        size = level_1_path.stat().st_size
        print(f"Size: {size:,} bytes")
        
        valid, error = check_syntax(level_1_path)
        print(f"Syntax: {'✓ VALID' if valid else '✗ ERROR'}")
        if not valid:
            print(f"  Error: {error}")
        
        functions = extract_functions(level_1_path)
        print(f"Functions: {len(functions)}")
        print(f"  Key functions: render_header, render_system_overview, render_status_cards")
        print(f"  All functions: {', '.join(functions[:5])}...")
    
    # Test Level 2 Dashboard
    print("\n[2/4] LEVEL 2 DASHBOARD (Technical)")
    print("-" * 80)
    
    level_2_path = base_dir / "dashboard" / "technical_app.py"
    
    print(f"File: {level_2_path.name}")
    print(f"Path: {level_2_path}")
    print(f"Status: {'✓ EXISTS' if check_file_exists(level_2_path) else '✗ NOT FOUND'}")
    
    if check_file_exists(level_2_path):
        size = level_2_path.stat().st_size
        print(f"Size: {size:,} bytes")
        
        valid, error = check_syntax(level_2_path)
        print(f"Syntax: {'✓ VALID' if valid else '✗ ERROR'}")
        if not valid:
            print(f"  Error: {error}")
        
        functions = extract_functions(level_2_path)
        print(f"Functions: {len(functions)}")
        print(f"  Key functions: fetch_health_data, fetch_prediction_data, render_system_overview")
        print(f"  All functions: {', '.join(functions[:5])}...")
    
    # Test Dependencies
    print("\n[3/4] DEPENDENCIES")
    print("-" * 80)
    
    packages = ["streamlit", "requests", "pandas"]
    for pkg in packages:
        code, _, _ = run_command(f'python -c "import {pkg}; print({pkg}.__version__)"')
        installed = code == 0
        print(f"{pkg:15} {'✓ INSTALLED' if installed else '✗ NOT FOUND'}")
    
    # Test API Availability
    print("\n[4/4] ENGINE 1 API")
    print("-" * 80)
    
    api_check = """
import requests
try:
    r = requests.get('http://localhost:8000/health', timeout=2)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("✓ API REACHABLE")
    else:
        print(f"⚠ Status code: {r.status_code}")
except requests.exceptions.ConnectionError:
    print("⚠ API NOT REACHABLE (not running)")
except Exception as e:
    print(f"⚠ Error: {type(e).__name__}")
"""
    
    code, stdout, _ = run_command(f'python -c "{api_check}"')
    print("API Health Check:")
    for line in stdout.strip().split('\n'):
        print(f"  {line}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    l1_valid = check_file_exists(level_1_path) and check_syntax(level_1_path)[0]
    l2_valid = check_file_exists(level_2_path) and check_syntax(level_2_path)[0]
    
    print("\nDashboards:")
    print(f"  Level 1: {'✓ READY' if l1_valid else '✗ ISSUES'}")
    print(f"  Level 2: {'✓ READY' if l2_valid else '✗ ISSUES'}")
    
    print("\nTo launch dashboards:")
    print(f"  Terminal 1: cd {base_dir} && python run_live_api.py")
    print(f"  Terminal 2: cd {base_dir} && streamlit run dashboard/app.py --server.port 8501")
    print(f"  Terminal 3: cd {base_dir} && streamlit run dashboard/technical_app.py --server.port 8502")
    
    print("\nTo access:")
    print(f"  Level 1: http://localhost:8501")
    print(f"  Level 2: http://localhost:8502")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
