#!/usr/bin/env python
"""
Green DevOps - Unified Dashboard Quick Reference

This file provides quick commands and information about all three dashboards.
"""

DASHBOARDS = {
    "Level 1 - Overview Dashboard": {
        "file": "dashboard/app.py",
        "port": "8501",
        "audience": "Non-technical (Executives, NOC)",
        "url": "http://localhost:8501",
        "command": "streamlit run dashboard/app.py --server.port 8501",
        "sections": [
            "System Status Cards (4 metrics)",
            "Workload Metrics (3 large cards)",
            "Scaling Recommendations",
            "CPU Trend Chart",
            "Alerts & Notifications"
        ]
    },
    "Level 2 - Technical Dashboard": {
        "file": "dashboard/technical_app.py",
        "port": "8502",
        "audience": "Technical (Engineers, Operators)",
        "url": "http://localhost:8502",
        "command": "streamlit run dashboard/technical_app.py --server.port 8502",
        "sections": [
            "System Overview (4 tabs)",
            "Metrics & Trends",
            "Diagnostics",
            "Backend Health"
        ]
    },
    "Unified Dashboard": {
        "file": "dashboard/unified_app.py",
        "port": "8503",
        "audience": "All users (Sidebar to switch)",
        "url": "http://localhost:8503",
        "command": "streamlit run dashboard/unified_app.py --server.port 8503",
        "features": [
            "Sidebar navigation",
            "Switch between views in one app",
            "Reduced code duplication",
            "Single entry point"
        ]
    }
}

if __name__ == "__main__":
    print("\n" + "="*80)
    print("GREEN DEVOPS - UNIFIED DASHBOARD QUICK REFERENCE")
    print("="*80)
    
    print("\n[1] START ENGINE 1 API SERVER (Required for all dashboards)")
    print("    python run_live_api.py")
    print("    → Wait for: INFO: Uvicorn running on http://0.0.0.0:8000")
    
    print("\n[2] CHOOSE YOUR DASHBOARD")
    print("-" * 80)
    
    for name, info in DASHBOARDS.items():
        print(f"\n{name}")
        print(f"  File:     {info['file']}")
        print(f"  Port:     {info['port']}")
        print(f"  Audience: {info['audience']}")
        print(f"  URL:      {info['url']}")
        print(f"  Command:  {info['command']}")
        
        key = "sections" if "sections" in info else "features"
        if key in info:
            print(f"  {key.capitalize()}:")
            for item in info[key]:
                print(f"    • {item}")
    
    print("\n" + "="*80)
    print("QUICK START OPTIONS")
    print("="*80)
    
    print("\nOPTION A: Run Individual Dashboards (Lightweight)")
    print("  Terminal 1: python run_live_api.py")
    print("  Terminal 2: streamlit run dashboard/app.py --server.port 8501")
    print("  Terminal 3: streamlit run dashboard/technical_app.py --server.port 8502")
    print("  → Access: http://localhost:8501 or http://localhost:8502")
    
    print("\nOPTION B: Run Unified Dashboard (Single Entry Point)")
    print("  Terminal 1: python run_live_api.py")
    print("  Terminal 2: streamlit run dashboard/unified_app.py --server.port 8503")
    print("  → Access: http://localhost:8503")
    print("  → Use sidebar to switch between views")
    
    print("\nOPTION C: Run All Three (Development/Comparison)")
    print("  Terminal 1: python run_live_api.py")
    print("  Terminal 2: streamlit run dashboard/app.py --server.port 8501")
    print("  Terminal 3: streamlit run dashboard/technical_app.py --server.port 8502")
    print("  Terminal 4: streamlit run dashboard/unified_app.py --server.port 8503")
    
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    print("\nRun verification script:")
    print("  python verify_unified_dashboard.py")
    print("\nExpected output:")
    print("  ✓ Syntax Check: PASS")
    print("  ✓ Function Exports: PASS")
    print("  ✓ Import Test: PASS")
    print("  ✅ ALL TESTS PASSED")
    
    print("\n" + "="*80)
    print("DOCUMENTATION")
    print("="*80)
    print("\nGuides available:")
    print("  • UNIFIED_DASHBOARD_GUIDE.md - Full integration guide")
    print("  • UNIFIED_DASHBOARD_COMPLETE.md - Refactoring summary")
    print("  • DASHBOARD_TEST_QUICKSTART.md - Testing procedures")
    print("  • TESTING_DASHBOARDS.md - Detailed test instructions")
    
    print("\n" + "="*80)
    print("KEY COMMANDS")
    print("="*80)
    print("\n# Verify everything works")
    print("python verify_unified_dashboard.py")
    
    print("\n# Run unified dashboard")
    print("streamlit run dashboard/unified_app.py --server.port 8503")
    
    print("\n# Run individual dashboards")
    print("streamlit run dashboard/app.py --server.port 8501")
    print("streamlit run dashboard/technical_app.py --server.port 8502")
    
    print("\n# Start API (required)")
    print("python run_live_api.py")
    
    print("\n" + "="*80)
    print("✅ STATUS: Ready for deployment")
    print("="*80 + "\n")
