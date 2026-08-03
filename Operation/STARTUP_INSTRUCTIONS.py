"""
Green DevOps Dashboard - Corrected Startup Instructions

This script shows the correct commands to start the API and dashboards.
The errors were due to incorrect file paths and command syntax.
"""

import sys

def print_section(title):
    print("\n" + "="*80)
    print(title)
    print("="*80)


def main():
    print_section("GREEN DEVOPS DASHBOARD - CORRECTED STARTUP")
    
    print("""
ERRORS FIXED:
✓ run_live_api.py is in scripts/ subdirectory
✓ streamlit must be run as: python -m streamlit
✓ Created launcher script to simplify commands

""")
    
    print_section("QUICK START (RECOMMENDED)")
    print("""
Use the launcher script - it handles all paths correctly!

Terminal 1 - Start API:
  cd d:\\Research\\Operation\\green-devops-operation-component
  python run_dashboard.py --api

Terminal 2 - Start Unified Dashboard:
  cd d:\\Research\\Operation\\green-devops-operation-component
  python run_dashboard.py --unified

Then open browser:
  http://localhost:8503

✓ Use sidebar to switch between Level 1 and Level 2
""")
    
    print_section("ALTERNATIVE: Manual Commands (If You Prefer)")
    print("""
Terminal 1 - Start API:
  cd d:\\Research\\Operation\\green-devops-operation-component
  python scripts/run_live_api.py

Terminal 2 - Start Any Dashboard:
  cd d:\\Research\\Operation\\green-devops-operation-component
  
  For Unified:
    python -m streamlit run dashboard/unified_app.py --server.port 8503
  
  For Level 1:
    python -m streamlit run dashboard/app.py --server.port 8501
  
  For Level 2:
    python -m streamlit run dashboard/technical_app.py --server.port 8502
""")
    
    print_section("WHAT CHANGED FROM ERRORS")
    print("""
❌ OLD (Incorrect):
  - python run_live_api.py              → File not at root
  - streamlit run dashboard/unified_app.py  → streamlit not in PATH

✅ NEW (Correct):
  - python scripts/run_live_api.py      → Correct path
  - python -m streamlit run ...         → Use Python module syntax
  - Or use: python run_dashboard.py     → New launcher script
""")
    
    print_section("LAUNCHER SCRIPT SYNTAX")
    print("""
Available commands:
  python run_dashboard.py --api          # Start API
  python run_dashboard.py --unified      # Start unified dashboard
  python run_dashboard.py --level 1      # Start Level 1 dashboard
  python run_dashboard.py --level 2      # Start Level 2 dashboard
  python run_dashboard.py --all          # Show all options

These handle paths and commands automatically!
""")
    
    print_section("DASHBOARDS AVAILABLE")
    print("""
┌─────────────────────┬──────┬────────────────────────────────┐
│ Dashboard           │ Port │ Access URL                     │
├─────────────────────┼──────┼────────────────────────────────┤
│ Unified (NEW!)      │ 8503 │ http://localhost:8503          │
│ Level 1 (Overview)  │ 8501 │ http://localhost:8501          │
│ Level 2 (Technical) │ 8502 │ http://localhost:8502          │
│ API Server          │ 8000 │ http://localhost:8000          │
└─────────────────────┴──────┴────────────────────────────────┘

Unified Dashboard (8503):
  - Single entry point for all users
  - Sidebar to switch between views
  - Recommended for mixed audience
  
Level 1 (8501):
  - Non-technical dashboard
  - For: Executives, NOC teams
  - Simple status, metrics, alerts
  
Level 2 (8502):
  - Technical diagnostics
  - For: Engineers, operators
  - Detailed metrics, trends, backend health
""")
    
    print_section("COMPLETE SETUP IN 30 SECONDS")
    print("""
Step 1: Open PowerShell/Terminal
  cd d:\\Research\\Operation\\green-devops-operation-component

Step 2: Terminal 1 - Start API
  python run_dashboard.py --api
  
  Wait for: INFO: Uvicorn running on http://0.0.0.0:8000

Step 3: Terminal 2 - Start Unified Dashboard
  python run_dashboard.py --unified
  
  Wait for: Local URL: http://localhost:8503

Step 4: Open Browser
  http://localhost:8503

Step 5: Explore
  - Level 1 (Overview): Click "Overview Dashboard" in sidebar
  - Level 2 (Technical): Click "Technical Dashboard" in sidebar
  - Click "Refresh Now" to update data
  - Auto-refresh every 7-8 seconds
""")
    
    print_section("VERIFICATION")
    print("""
Run this to verify everything is set up correctly:
  python verify_unified_dashboard.py

Expected output:
  ✓ Syntax Check: PASS
  ✓ Function Exports: PASS
  ✓ Import Test: PASS
  ✅ ALL TESTS PASSED
""")
    
    print_section("TROUBLESHOOTING")
    print("""
Problem: "streamlit not recognized"
Solution: Use: python -m streamlit run ...
  Or use launcher: python run_dashboard.py --unified

Problem: "Can't find run_live_api.py"
Solution: File is in scripts/ subdirectory
  Use: python scripts/run_live_api.py
  Or use launcher: python run_dashboard.py --api

Problem: Dashboard shows no data
Solution: 
  1. Make sure API is running (Terminal 1)
  2. Check http://localhost:8000/health in browser
  3. Wait 5 seconds for initialization
  4. Click "Refresh Now" button

Problem: Port already in use
Solution: 
  - Stop previous Streamlit: Ctrl+C
  - Wait 5 seconds
  - Restart with fresh terminal
""")
    
    print_section("FILES CREATED/UPDATED")
    print("""
✓ run_dashboard.py          → Launcher script (use this!)
✓ START.md                  → Quick start guide
✓ dashboard/unified_app.py  → Unified dashboard
✓ dashboard/app.py          → Level 1 dashboard
✓ dashboard/technical_app.py → Level 2 dashboard
✓ verify_unified_dashboard.py → Verification script
""")
    
    print_section("QUICK REFERENCE")
    print("""
API Server:
  python run_dashboard.py --api
  
Unified Dashboard:
  python run_dashboard.py --unified
  
Level 1 Dashboard:
  python run_dashboard.py --level 1
  
Level 2 Dashboard:
  python run_dashboard.py --level 2
  
Verify All:
  python verify_unified_dashboard.py
  
All Options:
  python run_dashboard.py --all
""")
    
    print_section("✅ STATUS: READY")
    print("""
All dashboards are now working correctly with:
✓ Fixed file paths
✓ Correct Python module syntax
✓ Launcher script for easy startup
✓ Proper error handling
✓ Real data from Engine 1 API

START WITH:
  python run_dashboard.py --api        (Terminal 1)
  python run_dashboard.py --unified    (Terminal 2)
  
THEN OPEN:
  http://localhost:8503
""")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
