"""
Quick Start Script - Launch Green DevOps Dashboard + API Server

One-command setup for complete Green DevOps Operation System.

Usage:
    python quickstart.py
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def main():
    print("=" * 70)
    print("Green DevOps Operation System - Quick Start")
    print("=" * 70)
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ required")
        sys.exit(1)
    
    # Check for required files
    print("1. Checking dependencies...")
    
    required_files = [
        "scripts/run_live_api.py",
        "dashboard/app.py",
        "src/workload_prediction_engine/live_predictor.py"
    ]
    
    for file in required_files:
        if not Path(file).exists():
            print(f"   ✗ Missing {file}")
            sys.exit(1)
        print(f"   ✓ Found {file}")
    
    print()
    print("2. Installing dependencies...")
    
    # Install API dependencies
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", 
             "fastapi", "uvicorn", "requests"],
            check=True
        )
        print("   ✓ API dependencies installed")
    except subprocess.CalledProcessError:
        print("   ✗ Failed to install API dependencies")
        sys.exit(1)
    
    # Install dashboard dependencies
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", 
             "streamlit", "requests"],
            check=True
        )
        print("   ✓ Dashboard dependencies installed")
    except subprocess.CalledProcessError:
        print("   ✗ Failed to install dashboard dependencies")
        sys.exit(1)
    
    print()
    print("3. Configuration")
    print("   • API Server: http://localhost:8000")
    print("   • Dashboard: http://localhost:8501")
    print("   • Mock Mode: Enabled (auto-fallback)")
    print()
    
    print("4. Starting Services...")
    print()
    
    # Start API server in background
    print("   Starting API Server...")
    api_cmd = [
        sys.executable, "scripts/run_live_api.py",
        "--system-id", "main_system",
        "--mock",  # Use mock mode for easy testing
        "--port", "8000"
    ]
    
    try:
        api_process = subprocess.Popen(
            api_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="."
        )
        print("   ✓ API Server started (PID: {})".format(api_process.pid))
    except Exception as e:
        print(f"   ✗ Failed to start API Server: {e}")
        sys.exit(1)
    
    # Wait for API to initialize
    time.sleep(3)
    
    # Start dashboard
    print("   Starting Dashboard...")
    dashboard_cmd = [
        sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
        "--logger.level=error"
    ]
    
    print()
    print("=" * 70)
    print("✓ All services started successfully!")
    print("=" * 70)
    print()
    print("Dashboard will open in your browser at: http://localhost:8501")
    print()
    print("Press Ctrl+C to stop all services (gracefully closes both)")
    print()
    
    # Open dashboard in browser
    time.sleep(2)
    try:
        webbrowser.open("http://localhost:8501")
    except:
        print("Note: Could not auto-open browser. Please visit http://localhost:8501")
    
    try:
        # Run dashboard (this will block)
        subprocess.run(dashboard_cmd, cwd=".")
    except KeyboardInterrupt:
        print()
        print("\nShutting down...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
        print("✓ Services stopped")


if __name__ == "__main__":
    main()
