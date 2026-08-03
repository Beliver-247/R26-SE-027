#!/usr/bin/env python
"""
Green DevOps Unified Dashboard Launcher

Simplifies starting the API and dashboards with correct paths and commands.

Usage:
    python run_dashboard.py --api              # Start API only
    python run_dashboard.py --unified          # Start unified dashboard
    python run_dashboard.py --level 1          # Start Level 1 only
    python run_dashboard.py --level 2          # Start Level 2 only
    python run_dashboard.py --all              # Start everything
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path


def run_api():
    """Start Engine 1 API server."""
    print("\n" + "="*80)
    print("STARTING ENGINE 1 API SERVER")
    print("="*80)
    print("\nAPI running on: http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run(
            [sys.executable, "scripts/run_live_api.py"],
            cwd=Path(__file__).parent
        )
    except KeyboardInterrupt:
        print("\n✓ API stopped")


def run_unified_dashboard():
    """Start unified dashboard."""
    print("\n" + "="*80)
    print("STARTING UNIFIED DASHBOARD")
    print("="*80)
    print("\nDashboard running on: http://localhost:8503")
    print("Use sidebar to switch between:")
    print("  • Overview Dashboard (Level 1)")
    print("  • Technical Dashboard (Level 2)")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "dashboard/unified_app.py", "--server.port", "8503"],
            cwd=Path(__file__).parent
        )
    except KeyboardInterrupt:
        print("\n✓ Dashboard stopped")


def run_level1_dashboard():
    """Start Level 1 (Overview) dashboard."""
    print("\n" + "="*80)
    print("STARTING LEVEL 1 - OVERVIEW DASHBOARD")
    print("="*80)
    print("\nDashboard running on: http://localhost:8501")
    print("Audience: Non-technical (Executives, NOC)")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", "8501"],
            cwd=Path(__file__).parent
        )
    except KeyboardInterrupt:
        print("\n✓ Dashboard stopped")


def run_level2_dashboard():
    """Start Level 2 (Technical) dashboard."""
    print("\n" + "="*80)
    print("STARTING LEVEL 2 - TECHNICAL DASHBOARD")
    print("="*80)
    print("\nDashboard running on: http://localhost:8502")
    print("Audience: Technical (Engineers, Operators)")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "dashboard/technical_app.py", "--server.port", "8502"],
            cwd=Path(__file__).parent
        )
    except KeyboardInterrupt:
        print("\n✓ Dashboard stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Green DevOps Dashboard Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dashboard.py --api              # Start API only
  python run_dashboard.py --unified          # Start unified dashboard (requires API running)
  python run_dashboard.py --level 1          # Start Level 1 dashboard only
  python run_dashboard.py --level 2          # Start Level 2 dashboard only
  python run_dashboard.py --all              # Start everything in separate terminals (recommended)
"""
    )
    
    parser.add_argument("--api", action="store_true", help="Start API server")
    parser.add_argument("--unified", action="store_true", help="Start unified dashboard")
    parser.add_argument("--level", type=int, choices=[1, 2], help="Start specific dashboard level")
    parser.add_argument("--all", action="store_true", help="Show all startup options")
    
    args = parser.parse_args()
    
    # Show help if no arguments
    if not any(vars(args).values()):
        print("\n" + "="*80)
        print("GREEN DEVOPS DASHBOARD LAUNCHER")
        print("="*80)
        print("\nUsage:")
        print("  python run_dashboard.py [OPTIONS]")
        print("\nOptions:")
        print("  --api              Start API server (http://localhost:8000)")
        print("  --unified          Start unified dashboard (http://localhost:8503)")
        print("  --level 1          Start Level 1 - Overview (http://localhost:8501)")
        print("  --level 2          Start Level 2 - Technical (http://localhost:8502)")
        print("  --all              Show all startup options")
        print("\nExamples:")
        print("  python run_dashboard.py --api")
        print("  python run_dashboard.py --unified")
        print("  python run_dashboard.py --level 1")
        print("  python run_dashboard.py --all")
        print("\nNote: To use dashboards, start the API first in a separate terminal!")
        print("="*80 + "\n")
        return
    
    if args.all:
        print("\n" + "="*80)
        print("GREEN DEVOPS DASHBOARD - STARTUP OPTIONS")
        print("="*80)
        
        print("\n📋 OPTION A: Unified Dashboard (Recommended for Mixed Audience)")
        print("-" * 80)
        print("Terminal 1:")
        print("  python run_dashboard.py --api")
        print("\nTerminal 2:")
        print("  python run_dashboard.py --unified")
        print("\nAccess both views at:")
        print("  http://localhost:8503")
        
        print("\n📋 OPTION B: Individual Dashboards")
        print("-" * 80)
        print("Terminal 1:")
        print("  python run_dashboard.py --api")
        print("\nTerminal 2:")
        print("  python run_dashboard.py --level 1")
        print("\nTerminal 3:")
        print("  python run_dashboard.py --level 2")
        print("\nAccess dashboards at:")
        print("  http://localhost:8501  (Overview - Non-technical)")
        print("  http://localhost:8502  (Technical - Engineers)")
        
        print("\n" + "="*80 + "\n")
        return
    
    if args.api:
        run_api()
    elif args.unified:
        run_unified_dashboard()
    elif args.level == 1:
        run_level1_dashboard()
    elif args.level == 2:
        run_level2_dashboard()


if __name__ == "__main__":
    main()
