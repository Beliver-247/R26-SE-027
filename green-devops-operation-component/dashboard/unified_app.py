"""
Green DevOps Unified Dashboard

Integrated Level 1 (Overview) and Level 2 (Technical) Dashboards
in a single Streamlit application with sidebar navigation.

Usage:
    streamlit run dashboard/unified_app.py
"""

import streamlit as st
import sys
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app import render_overview
from technical_app import render_technical

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Green DevOps Unified Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# Sidebar Navigation
# ============================================================================

st.sidebar.markdown("# 🟢 Green DevOps Dashboard")
st.sidebar.markdown("---")

dashboard_mode = st.sidebar.radio(
    "Select Dashboard View",
    ["Overview Dashboard", "Technical Dashboard"],
    help="Choose between non-technical overview or technical details"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.caption("**Level 1:** Executive/Non-technical overview")
st.sidebar.caption("- System status cards")
st.sidebar.caption("- Workload metrics")
st.sidebar.caption("- Scaling recommendations")

st.sidebar.markdown("")
st.sidebar.caption("**Level 2:** Technical diagnostics & monitoring")
st.sidebar.caption("- System overview & metrics")
st.sidebar.caption("- Trend analysis & history")
st.sidebar.caption("- Retraining readiness")
st.sidebar.caption("- Backend health monitoring")

st.sidebar.markdown("---")

# ============================================================================
# Session State Initialization (MUST be before any render calls)
# ============================================================================
# Initialize all required session state keys to prevent "has no attribute" errors
# on browser refresh or initial page load

if "api_available" not in st.session_state:
    st.session_state.api_available = None  # None = unchecked, True = available, False = unavailable

if "last_health_check" not in st.session_state:
    st.session_state.last_health_check = 0

if "last_health_data" not in st.session_state:
    st.session_state.last_health_data = None

if "last_prediction_data" not in st.session_state:
    st.session_state.last_prediction_data = None

if "last_decision_data" not in st.session_state:
    st.session_state.last_decision_data = None

if "last_error" not in st.session_state:
    st.session_state.last_error = None

if "auto_refresh_enabled" not in st.session_state:
    st.session_state.auto_refresh_enabled = True

if "cpu_history" not in st.session_state:
    st.session_state.cpu_history = []

if "predicted_cpu_history" not in st.session_state:
    st.session_state.predicted_cpu_history = []

if "timestamps" not in st.session_state:
    st.session_state.timestamps = []

if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []

if "api_status" not in st.session_state:
    st.session_state.api_status = None

if "api_check_time" not in st.session_state:
    st.session_state.api_check_time = 0

if "api_check_interval" not in st.session_state:
    st.session_state.api_check_interval = 30

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0

if "last_demo_timestamp" not in st.session_state:
    st.session_state.last_demo_timestamp = None

if "latest_demo_data" not in st.session_state:
    st.session_state.latest_demo_data = None

if st.session_state.auto_refresh_enabled:
    st_autorefresh(interval=5000, key="demo_loop_refresh")

# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main unified dashboard application."""
    
    try:
        if dashboard_mode == "Overview Dashboard":
            render_overview()
        else:
            render_technical()
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        st.info("Check that the API server is running and accessible at http://localhost:5050")


if __name__ == "__main__":
    main()
