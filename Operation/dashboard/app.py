"""
Green DevOps Operation System - Level 1 Overview Dashboard

Non-technical user dashboard for real-time monitoring of Engine 1 workload predictions.
Connects to Engine 1 API for live data with graceful fallback to mock mode.

Supports demo/test data mode when run_demo_scenarios.py is active.

Usage:
    streamlit run dashboard/app.py
"""

import streamlit as st
import requests
import json
from datetime import datetime
import time
from collections import deque
import random
from streamlit_autorefresh import st_autorefresh
from demo_adapter import (
    is_demo_mode_available,
    get_latest_demo_result,
    get_demo_history,
    load_latest_demo_data,
    format_demo_display_data,
    render_demo_mode_indicator,
    get_scenario_explanation,
    get_action_description
)

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = "http://localhost:5050"
API_HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
API_PREDICT_ENDPOINT = f"{API_BASE_URL}/predict"
REFRESH_INTERVAL = 7  # seconds

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Green DevOps Dashboard",
    page_icon="ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã…Â ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-card {
        background-color: #d4edda;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
    }
    .warning-card {
        background-color: #fff3cd;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
    }
    .error-card {
        background-color: #f8d7da;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
    }
    .big-number {
        font-size: 48px;
        font-weight: bold;
        color: #1f77b4;
    }
    .normal-text {
        font-size: 18px;
        color: #333;
    }
    .pipeline-header {
        background: #0f172a;
        color: #f8fafc;
        padding: 24px 28px;
        border-radius: 8px;
        border: 1px solid #1e293b;
        margin-bottom: 18px;
    }
    .pipeline-mode {
        display: inline-block;
        background: #2563eb;
        color: white;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.04em;
        padding: 6px 10px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .pipeline-scenario {
        font-size: 40px;
        font-weight: 800;
        line-height: 1.1;
        margin: 2px 0 10px 0;
    }
    .pipeline-subrow {
        display: flex;
        flex-wrap: wrap;
        gap: 18px;
        color: #cbd5e1;
        font-size: 16px;
    }
    .section-title {
        font-size: 22px;
        font-weight: 750;
        margin: 26px 0 12px 0;
        color: #0f172a;
    }
    .decision-panel {
        padding: 22px 24px;
        border-radius: 8px;
        border: 1px solid #dbe4ef;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
        margin-bottom: 16px;
    }
    .decision-action {
        font-size: 34px;
        font-weight: 850;
        line-height: 1.1;
        margin-bottom: 10px;
    }
    .action-up { color: #dc2626; }
    .action-down { color: #16a34a; }
    .action-hybrid { color: #2563eb; }
    .action-stable { color: #64748b; }
    .reason-text {
        color: #334155;
        font-size: 16px;
        margin-bottom: 14px;
    }
    .mini-kpi-row {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
    }
    .mini-kpi {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 14px;
    }
    .mini-label {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 3px;
    }
    .mini-value {
        color: #0f172a;
        font-size: 21px;
        font-weight: 750;
    }
    .change-strip {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
        min-height: 92px;
    }
    .change-title {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 8px;
    }
    .change-value {
        color: #0f172a;
        font-size: 22px;
        font-weight: 750;
    }
    .flow-panel {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e3a8a;
        border-radius: 8px;
        padding: 14px 16px;
        margin-top: 16px;
    }
    @media (max-width: 900px) {
        .pipeline-scenario { font-size: 30px; }
        .mini-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# Session State Management (for data caching)
# ============================================================================

if "cpu_history" not in st.session_state:
    st.session_state.cpu_history = deque(maxlen=20)

if "predicted_cpu_history" not in st.session_state:
    st.session_state.predicted_cpu_history = deque(maxlen=20)

if "timestamps" not in st.session_state:
    st.session_state.timestamps = deque(maxlen=20)

if "api_available" not in st.session_state:
    st.session_state.api_available = None  # None = unchecked, True = available, False = unavailable

if "last_health_data" not in st.session_state:
    st.session_state.last_health_data = None

if "last_prediction_data" not in st.session_state:
    st.session_state.last_prediction_data = None

if "api_check_time" not in st.session_state:
    st.session_state.api_check_time = 0

if "api_check_interval" not in st.session_state:
    st.session_state.api_check_interval = 30  # Check health every 30 seconds

if "auto_refresh_enabled" not in st.session_state:
    st.session_state.auto_refresh_enabled = True

# ============================================================================
# Auto-Refresh Configuration
# ============================================================================
# Trigger auto-refresh every 5 seconds (3000ms for safety margin)
if st.session_state.auto_refresh_enabled:
    st_autorefresh(
        interval=5000,  # 5 seconds
        key="dashboard_auto_refresh",
        debounce=False
    )

# ============================================================================
# API Communication Functions
# ============================================================================

def fetch_health_data():
    """Fetch system health status from API with caching and smart intervals."""
    current_time = time.time()
    
    # Check if we should attempt API call (interval-based - every 30 seconds)
    if (st.session_state.api_available is None or 
        (current_time - st.session_state.api_check_time > st.session_state.api_check_interval)):
        
        try:
            response = requests.get(API_HEALTH_ENDPOINT, timeout=3)
            if response.status_code == 200:
                data = response.json()
                st.session_state.api_available = True
                st.session_state.last_health_data = data
                st.session_state.api_check_time = current_time
                return data
            else:
                st.session_state.api_available = False
                st.session_state.api_check_time = current_time
                # Return cached data on HTTP error
                return st.session_state.last_health_data if st.session_state.last_health_data else {}
        except Exception as e:
            st.session_state.api_available = False
            st.session_state.api_check_time = current_time
            # Return cached data on connection error
            return st.session_state.last_health_data if st.session_state.last_health_data else {}
    
    # Return cached data if API check was recent (within 30s)
    return st.session_state.last_health_data if st.session_state.last_health_data else {}


def fetch_prediction_data():
    """Fetch latest prediction from API with caching (every refresh)."""
    # Always attempt to fetch prediction on each refresh if API may be available
    if st.session_state.api_available is not False:
        try:
            response = requests.get(API_PREDICT_ENDPOINT, timeout=3)
            if response.status_code == 200:
                data = response.json()
                st.session_state.last_prediction_data = data
                return data
            else:
                # Return cached data on HTTP error
                return st.session_state.last_prediction_data if st.session_state.last_prediction_data else {}
        except Exception as e:
            # Return cached data on connection error
            return st.session_state.last_prediction_data if st.session_state.last_prediction_data else {}
    
    # Return cached data if API known to be unavailable
    return st.session_state.last_prediction_data if st.session_state.last_prediction_data else {}


# ============================================================================
# Mock Data Generation (Fallback when API unavailable)
# ============================================================================

def generate_mock_health():
    """Generate mock health data."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system_id": "demo_system",
        "mode": random.choice(["cold_start", "runtime"]),
        "records_collected": random.randint(5, 100),
        "model_version": "balanced",
        "data_source": random.choice(["cold_start", "runtime"]),
        "retraining_ready": False
    }


def generate_mock_prediction():
    """Generate mock prediction data."""
    cpu = random.uniform(10, 80)
    
    # Determine load level based on CPU
    if cpu < 30:
        load_level = "LOW"
    elif cpu < 70:
        load_level = "NORMAL"
    else:
        load_level = "HIGH"
    
    # Calculate pod recommendation
    if load_level == "LOW":
        pods = 1
    elif load_level == "NORMAL":
        pods = random.choice([1, 2])
    else:
        pods = random.choice([2, 3])
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prediction": {
            "system_id": "demo_system",
            "predicted_cpu_percent": round(cpu, 2),
            "predicted_load_level": load_level,
            "recommended_pods": pods,
            "confidence": round(random.uniform(0.85, 1.0), 2),
            "data_source": "cold_start" if random.random() > 0.7 else "runtime",
            "model_version": "balanced"
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================

def get_status_color(status):
    """Return color based on status."""
    if status == "RUNNING":
        return "ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¢"
    elif status == "WARNING":
        return "ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¡"
    else:
        return "ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´"


def get_load_color(load_level):
    """Return color indicator for load level."""
    if load_level == "LOW":
        return "ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¢"
    elif load_level == "NORMAL":
        return "ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¡"
    else:
        return "ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´"


def get_mode_explanation(mode):
    """Return user-friendly explanation of mode."""
    if mode == "cold_start":
        return "Learning Phase - System is still collecting initial data"
    else:
        return "Normal Operation - System is running with observed data"


def determine_system_status(load_level, records):
    """Determine overall system status."""
    if records < 3:
        return "RUNNING", "ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Initializing"
    elif load_level == "HIGH":
        return "WARNING", "ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â High Load"
    else:
        return "RUNNING", "ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“ Normal"


def determine_scaling_action(current_pods, recommended_pods):
    """Determine scaling action needed."""
    if recommended_pods > current_pods:
        return "SCALE UP", "ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â¼ Add Pods", "#dc3545"
    elif recommended_pods < current_pods:
        return "SCALE DOWN", "ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â½ Remove Pods", "#ffc107"
    else:
        return "NO CHANGE", "ÃƒÂ¢Ã…Â¾Ã‚Â¡ÃƒÂ¯Ã‚Â¸Ã‚Â Keep Current", "#28a745"


# ============================================================================
# Live Pipeline Dashboard Helpers
# ============================================================================

def safe_float(value, default=0.0):
    """Convert API/demo values to float without breaking the dashboard."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    """Convert API/demo values to int without breaking the dashboard."""
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def count_jobs(value):
    """Return a display-safe delayed job count."""
    if isinstance(value, list):
        return len(value)
    return safe_int(value)


def format_dashboard_time(timestamp):
    """Format ISO timestamps into a panel-friendly local time."""
    if not timestamp:
        return "N/A"
    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return str(timestamp)

def get_previous_history_row(history_df):
    """Use the row before the latest point for metric deltas."""
    if history_df is None or history_df.empty or len(history_df) < 2:
        return None
    return history_df.sort_values("timestamp").iloc[-2]


def get_action_class(action):
    """Return CSS class for final decision action."""
    normalized = str(action or "").lower()
    if normalized == "scale_up":
        return "action-up"
    if normalized == "scale_down":
        return "action-down"
    if normalized == "hybrid":
        return "action-hybrid"
    return "action-stable"


def describe_decision_action(action):
    """User-friendly action wording for the decision panel."""
    normalized = str(action or "").lower()
    descriptions = {
        "scale_up": "Increase capacity to protect service performance",
        "scale_down": "Reduce capacity to save energy and carbon",
        "hybrid": "Balance pod scaling with safe job delay",
        "no_action": "Keep the current operating state",
    }
    return descriptions.get(normalized, get_action_description(normalized))


def change_indicator(previous, current):
    """Return previous/current display text and scaling direction."""
    if previous is None:
        return "N/A", current, "Stable", "-"
    if current > previous:
        return previous, current, "Scaling Up", "UP"
    if current < previous:
        return previous, current, "Scaling Down", "DOWN"
    return previous, current, "Stable", "-"

def render_live_pipeline_dashboard(demo_result):
    """Render the professional live pipeline dashboard from latest.json/history.csv."""
    demo_data = format_demo_display_data(demo_result)
    history_df = get_demo_history()
    previous = get_previous_history_row(history_df)

    scenario_name = demo_data.get("scenario_name") or "LIVE PIPELINE"
    timestamp = demo_data.get("timestamp") or demo_result.get("timestamp")
    last_updated = format_dashboard_time(timestamp)
    fetch_health_data()
    api_healthy = st.session_state.api_available is not False
    health_label = "Healthy" if api_healthy else "API Check Pending"

    predicted_cpu = safe_float(demo_data.get("engine1", {}).get("predicted_cpu"))
    load_level = str(demo_data.get("engine1", {}).get("predicted_load_level") or "N/A").upper()
    current_pods = safe_int(demo_data.get("current_pods"))
    final_pods = safe_int(demo_data.get("final_required_pods"))
    final_action = str(demo_data.get("final_action") or "no_action").lower()
    jobs_delayed = count_jobs(demo_data.get("jobs_to_delay"))

    decision_step = demo_result.get("steps", {}).get("decision", {})
    decision_payload = decision_step.get("decision", {})
    engine2_step = demo_result.get("steps", {}).get("engine2", {})
    engine3_step = demo_result.get("steps", {}).get("engine3", {})
    reason = (
        decision_step.get("reasoning", {}).get("reason")
        or engine2_step.get("reason")
        or describe_decision_action(final_action)
    )
    carbon_percent = safe_float(
        engine2_step.get("carbon_saving_percent", decision_payload.get("carbon_saving_percent", 0))
    )
    carbon_gco2 = safe_float(
        engine2_step.get("carbon_saving_gco2", decision_payload.get("carbon_saving_gco2", demo_data.get("carbon_saving", 0)))
    )
    workload_reduction = safe_float(engine3_step.get("workload_reduction_percent", demo_data.get("engine3", {}).get("workload_reduction_percent", 0))) * 100
    sla_status = "Protected" if decision_payload.get("sla_preserved", demo_data.get("sla_preserved")) else "Optimized"

    previous_cpu = safe_float(previous.get("predicted_cpu")) if previous is not None and "predicted_cpu" in previous else None
    previous_current_pods = safe_int(previous.get("current_pods")) if previous is not None and "current_pods" in previous else None
    previous_final_pods = safe_int(previous.get("final_pods")) if previous is not None and "final_pods" in previous else None
    previous_action = str(previous.get("final_action")) if previous is not None and "final_action" in previous else "N/A"
    previous_jobs = safe_int(previous.get("delayable_jobs")) if previous is not None and "delayable_jobs" in previous else None
    previous_carbon = safe_float(previous.get("carbon_saving_percent")) if previous is not None and "carbon_saving_percent" in previous else None
    previous_load = str(previous.get("load_level")).upper() if previous is not None and "load_level" in previous else "N/A"

    cpu_delta = None if previous_cpu is None else f"{predicted_cpu - previous_cpu:+.1f}%"
    current_pods_delta = None if previous_current_pods is None else current_pods - previous_current_pods
    final_pods_delta = None if previous_final_pods is None else final_pods - previous_final_pods
    load_delta = "stable" if previous_load == load_level else f"{previous_load} -> {load_level}"

    with st.container(border=True):
        st.caption("LIVE PIPELINE MODE")
        st.markdown(f"## Scenario: {scenario_name}")
        status_col1, status_col2, status_col3 = st.columns([2, 1, 1])
        with status_col1:
            st.markdown("**Live Pipeline (Test Scenarios)**")
        with status_col2:
            st.markdown(f"**Last Update:** {last_updated}")
        with status_col3:
            st.markdown(f"**Status:** {health_label}")

    st.markdown("<div class='section-title'>Real-Time Metrics</div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("CPU %", f"{predicted_cpu:.1f}%", delta=cpu_delta)
    with col2:
        st.metric("Load Level", load_level, delta=load_delta)
    with col3:
        st.metric("Current Pods", current_pods, delta=current_pods_delta)
    with col4:
        st.metric("Final Pods", final_pods, delta=final_pods_delta)

    st.markdown("<div class='section-title'>Decision Panel</div>", unsafe_allow_html=True)
    action_status = st.error if final_action == "scale_up" else st.success if final_action == "scale_down" else st.info
    with st.container(border=True):
        action_status(f"ACTION: {final_action.replace('_', ' ').upper()}")
        st.markdown(f"**Reason:** {reason}")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("SLA Status", sla_status)
        with kpi2:
            st.metric("Jobs Delayed", jobs_delayed)
        with kpi3:
            st.metric("Carbon Saving", f"{carbon_percent:.1f}%")
        with kpi4:
            st.metric("Carbon Saved", f"{carbon_gco2:.2f} gCO2")

    st.markdown("<div class='section-title'>Visual Change Indicators</div>", unsafe_allow_html=True)
    pods_prev, pods_now, pods_direction, pods_icon = change_indicator(previous_final_pods, final_pods)
    cpu_prev = "N/A" if previous_cpu is None else f"{previous_cpu:.1f}%"
    jobs_prev = "N/A" if previous_jobs is None else previous_jobs
    carbon_prev = "N/A" if previous_carbon is None else f"{previous_carbon:.1f}%"
    change1, change2, change3, change4 = st.columns(4)
    with change1:
        with st.container(border=True):
            st.caption("Pods")
            st.markdown(f"### {pods_prev} -> {pods_now} {pods_icon}")
            st.markdown(pods_direction)
    with change2:
        with st.container(border=True):
            st.caption("Decision")
            st.markdown(f"### {previous_action} -> {final_action}")
            st.markdown(describe_decision_action(final_action))
    with change3:
        with st.container(border=True):
            st.caption("CPU")
            st.markdown(f"### {cpu_prev} -> {predicted_cpu:.1f}%")
            st.markdown(f"{load_level} load signal")
    with change4:
        with st.container(border=True):
            st.caption("Jobs / Carbon")
            st.markdown(f"### {jobs_prev} -> {jobs_delayed} jobs")
            st.markdown(f"{carbon_prev} -> {carbon_percent:.1f}% saving")

    st.markdown("<div class='section-title'>Real-Time Charts</div>", unsafe_allow_html=True)
    if history_df is not None and not history_df.empty:
        chart_df = history_df.sort_values("timestamp").tail(80).copy()
        chart_df = chart_df.set_index("timestamp")

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown("**CPU Over Time**")
            if "predicted_cpu" in chart_df.columns:
                st.line_chart(chart_df[["predicted_cpu"]], height=220)
        with chart_col2:
            st.markdown("**Pods Over Time**")
            pod_cols = [col for col in ["current_pods", "final_pods"] if col in chart_df.columns]
            if pod_cols:
                st.line_chart(chart_df[pod_cols], height=220)

        st.markdown("**Carbon Saving Over Time**")
        if "carbon_saving_percent" in chart_df.columns:
            st.line_chart(chart_df[["carbon_saving_percent"]], height=220)
    else:
        st.info("Waiting for loop history data from data/demo/history.csv.")

    st.info(
        "How system works: Prediction -> Job Analysis -> Carbon Optimization -> "
        f"Final Decision -> Dashboard. Current workload reduction from job analysis: {workload_reduction:.1f}%."
    )

    with st.sidebar:
        st.markdown("### Live Controls")
        auto_refresh_enabled = st.checkbox(
            "Auto Refresh",
            value=st.session_state.auto_refresh_enabled,
            key="auto_refresh_control_live"
        )
        st.session_state.auto_refresh_enabled = auto_refresh_enabled
        st.caption("Updates every 5 seconds from data/demo/latest.json and data/demo/history.csv.")


# ============================================================================
# Auto-Refresh Control (Non-intrusive time-based refresh)
# ============================================================================

def trigger_auto_refresh():
    """
    Trigger dashboard refresh based on time intervals.
    Uses session state to manage timing without infinite loops.
    
    Refresh strategy:
    - Health check: Every 30 seconds
    - Data fetch: Every 5 seconds (if API available)
    """
    if not st.session_state.auto_refresh_enabled:
        return
    
    current_time = time.time()
    last_refresh = st.session_state.get("last_refresh", 0)
    
    # Refresh every 5 seconds for data updates
    if (current_time - last_refresh) > 5:
        st.session_state.last_refresh = current_time
        st.rerun()


# ============================================================================
# Dashboard Rendering
# ============================================================================

def render_overview():
    """Render Level 1 Overview Dashboard.
    
    This dashboard is for non-technical users and shows:
    - System Status Cards
    - Workload Metrics
    - Scaling Recommendations
    - CPU Trend Chart
    - Alerts & Notifications
    
    Supports demo/test data mode when run_demo_scenarios.py is active.
    """
    # Check for demo mode first and refresh session state from latest.json.
    latest_demo = load_latest_demo_data()
    if latest_demo:
        latest_ts = latest_demo.get("timestamp")
        if latest_ts != st.session_state.get("last_demo_timestamp"):
            st.session_state.last_demo_timestamp = latest_ts
            st.session_state.latest_demo_data = latest_demo
            st.session_state.last_prediction_data = latest_demo
            st.session_state.last_decision_data = latest_demo.get("decision", {})

    demo_mode = latest_demo is not None or is_demo_mode_available()
    demo_result = st.session_state.get("latest_demo_data") if demo_mode else None
    if demo_result is None and demo_mode:
        demo_result = get_latest_demo_result()

    if demo_result:
        render_live_pipeline_dashboard(demo_result)
        return
    
    # Header
    st.markdown("# ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¢ Green DevOps System Dashboard")
    st.markdown("### Real-Time System Monitoring")
    
    # Show demo mode indicator if active
    if demo_mode and demo_result:
        st.info(render_demo_mode_indicator(True))
        demo_data = format_demo_display_data(demo_result)
        
        # Display scenario name and explanation
        scenario_name = demo_data.get("scenario_name", "")
        st.caption(f"Loop Scenario: {scenario_name or 'N/A'}")
        st.caption(f"Last Updated: {demo_data.get('timestamp', 'N/A')}")
        if scenario_name:
            st.markdown(f"#### ÃƒÂ°Ã…Â¸Ã…Â½Ã‚Â¬ Current Scenario: **{scenario_name}**")
            st.markdown(f"_{get_scenario_explanation(scenario_name)}_")
            st.markdown("---")
        
        # Use demo data for display
        health_data = generate_mock_health()  # Keep baseline for compatibility
        health_data["timestamp"] = demo_data.get("timestamp", health_data["timestamp"])
        prediction_data = {
            "prediction": {
                "predicted_cpu_percent": demo_data["engine1"]["predicted_cpu"],
                "predicted_load_level": demo_data["engine1"]["predicted_load_level"],
                "recommended_pods": demo_data["engine1"]["recommended_pods"],
                "raw_required_pods": demo_data["engine1"]["raw_required_pods"],
                "current_pods": demo_data["current_pods"],
                "final_required_pods": demo_data["final_required_pods"],
                "final_action": demo_data["final_action"],
                "jobs_to_delay": demo_data["jobs_to_delay"],
                "carbon_saving": demo_data["carbon_saving"],
                "sla_preserved": demo_data["sla_preserved"],
                "confidence": demo_data["engine1"]["confidence"]
            }
        }
        using_demo = True
    else:
        # Fetch data from API or use mock
        health_data = fetch_health_data()
        prediction_data = fetch_prediction_data()
        using_demo = False
        
        # Determine if we need to use mock data
        if health_data is None:
            health_data = generate_mock_health()
        
        if prediction_data is None:
            prediction_data = generate_mock_prediction()
    
    # Show API status indicator
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if using_demo:
            st.success("ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¢ **Demo Test Data Mode** - Engine logic processing synthetic scenarios")
        elif st.session_state.api_available is True:
            st.success("ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¢ **Live Mode** - Connected to API")
        elif st.session_state.api_available is False:
            st.warning("ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¡ **Cached Mode** - Using cached data (API unavailable)")
        else:
            st.info("ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Âµ Checking API connection...")
    
    with col3:
        auto_refresh_enabled = st.checkbox(
            "Auto Refresh",
            value=st.session_state.auto_refresh_enabled,
            key="auto_refresh_control"
        )
        st.session_state.auto_refresh_enabled = auto_refresh_enabled
    
    st.markdown("---")
    
    # ========================================================================
    # Section 1: System Status Cards (Top Row)
    # ========================================================================
    st.markdown("### System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Extract data
    mode = health_data.get("mode", "unknown")
    records = health_data.get("records_collected", 0)
    data_source = health_data.get("data_source", "unknown")
    timestamp_str = health_data.get("timestamp", "")
    
    # Determine system status
    prediction = prediction_data.get("prediction", {})
    load_level = prediction.get("predicted_load_level", "NORMAL")
    system_status, status_text = determine_system_status(load_level, records)
    
    # Card 1: System Status
    with col1:
        st.metric(
            "System Status",
            get_status_color(system_status),
            status_text
        )
    
    # Card 2: Mode
    with col2:
        mode_friendly = "Cold Start" if mode == "cold_start" else "Runtime"
        st.metric(
            "Mode",
            mode_friendly,
            get_mode_explanation(mode)
        )
    
    # Card 3: Last Updated (value hidden)
    with col3:
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            time_ago = datetime.now(dt.tzinfo) - dt
            minutes = int(time_ago.total_seconds() / 60)
            seconds = int(time_ago.total_seconds() % 60)
            
            time_text = f"{minutes}m {seconds}s ago" if minutes > 0 else f"{seconds}s ago"
        except:
            time_text = "N/A"
        
        st.metric("Last Updated", time_text)
    
    # Card 4: Data Source
    with col4:
        source_friendly = "Cold Start" if data_source == "cold_start" else "Runtime"
        st.metric("Data Source", source_friendly, f"{records} records collected")
    
    # ========================================================================
    # Section 2: Current & Predicted Workload (Large Cards)
    # ========================================================================
    st.markdown("---")
    st.markdown("### Current & Predicted Workload")
    
    col1, col2, col3 = st.columns(3)
    
    predicted_cpu = prediction.get("predicted_cpu_percent", 0)
    confidence = prediction.get("confidence", 0)
    
    # Estimate current CPU (slightly lower than predicted for demo)
    current_cpu = max(0, predicted_cpu - random.uniform(0, 10))
    
    # Add to history
    st.session_state.cpu_history.append(current_cpu)
    st.session_state.predicted_cpu_history.append(predicted_cpu)
    st.session_state.timestamps.append(datetime.now().strftime("%H:%M:%S"))
    
    # Card 1: Current CPU (visible)
    with col1:
        st.markdown(f"""
            <div class='metric-card'>
                <p style='color: #666; font-size: 14px; margin: 0;'>Current CPU Usage</p>
                <p class='big-number'>{current_cpu:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Card 2: Predicted CPU (visible)
    with col2:
        st.markdown(f"""
            <div class='metric-card'>
                <p style='color: #666; font-size: 14px; margin: 0;'>Predicted CPU (30 seconds)</p>
                <p class='big-number'>{predicted_cpu:.1f}%</p>
                <p style='color: #999; font-size: 12px; margin: 0;'>Confidence: {confidence:.0%}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Card 3: Load Level (visible)
    with col3:
        color_icon = get_load_color(load_level)
        st.markdown(f"""
            <div class='metric-card'>
                <p style='color: #666; font-size: 14px; margin: 0;'>Load Level</p>
                <p class='big-number'>{color_icon} {load_level}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================================================
    # Section 3: Scaling Recommendation
    # ========================================================================
    st.markdown("---")
    st.markdown("### Scaling Recommendation")
    
    current_pods = prediction.get("current_pods", 1)
    recommended_pods = prediction.get("final_required_pods", prediction.get("recommended_pods", 1))
    action, action_text, action_color = determine_scaling_action(current_pods, recommended_pods)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Pods", current_pods)
    
    with col2:
        st.metric("Recommended Pods", recommended_pods)
    
    with col3:
        # Highlight the action needed
        action_display = f"{action_text}\n{action}"
        if action == "SCALE UP":
            st.error(action_text)
            st.metric("Action", action)
        elif action == "SCALE DOWN":
            st.warning(action_text)
            st.metric("Action", action)
        else:
            st.success(action_text)
            st.metric("Action", action)
    
    # ========================================================================
    # Section 4: CPU Trend Chart
    # ========================================================================
    st.markdown("---")
    st.markdown("### CPU Usage Trend")
    
    if len(st.session_state.cpu_history) > 0:
        # Prepare data for chart
        chart_data = {
            "Time": list(st.session_state.timestamps),
            "Current CPU": list(st.session_state.cpu_history),
            "Predicted CPU": list(st.session_state.predicted_cpu_history)
        }
        
        st.line_chart(
            data={
                "Current CPU (%)": list(st.session_state.cpu_history),
                "Predicted CPU (%)": list(st.session_state.predicted_cpu_history)
            }
        )
    
    # ========================================================================
    # Section 5: Alerts
    # ========================================================================
    st.markdown("---")
    st.markdown("### Alerts & Notifications")
    
    alerts = []
    
    # Check for high load
    if load_level == "HIGH":
        alerts.append(("error", f"ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´ High Load Detected - CPU at {predicted_cpu:.1f}%"))
    
    # Check if scaling recommended
    if recommended_pods != current_pods:
        if recommended_pods > current_pods:
            alerts.append(("warning", f"ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Scaling Recommended - Increase to {recommended_pods} pods"))
        else:
            alerts.append(("warning", f"ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Scaling Recommended - Decrease to {recommended_pods} pods"))
    
    # Check if system is initializing
    if records < 5:
        alerts.append(("info", f"ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¹ÃƒÂ¯Ã‚Â¸Ã‚Â System Initializing - {records} records collected"))
    
    # If no alerts
    if not alerts:
        st.success("ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“ System Running Normally - No Issues Detected")
    else:
        for alert_type, alert_text in alerts:
            if alert_type == "error":
                st.error(alert_text)
            elif alert_type == "warning":
                st.warning(alert_text)
            else:
                st.info(alert_text)
    
    # ========================================================================
    # Section 6: Demo Data Insights (if in demo mode)
    # ========================================================================
    if using_demo and demo_result:
        st.markdown("---")
        st.markdown("### ÃƒÂ°Ã…Â¸Ã…Â½Ã‚Â¬ Demo Scenario Analysis")
        
        demo_data = format_demo_display_data(demo_result)
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Engine 3 - Jobs
        with col1:
            st.metric(
                "Jobs Delayed",
                demo_data["engine3"]["delayable_jobs"],
                f"{demo_data['engine3']['workload_reduction_percent']*100:.0f}% reduction"
            )
        
        # Engine 2 - Carbon
        with col2:
            st.metric(
                "Carbon Saved",
                f"{demo_data['engine2']['carbon_saving_gco2']:.1f}g",
                f"{demo_data['engine2']['carbon_saving_percent']:.0f}% reduction"
            )
        
        # Decision - Final Action
        with col3:
            action_text = get_action_description(demo_data["decision"]["action"])
            st.metric(
                "Final Action",
                demo_data["decision"]["action"],
                action_text
            )
        
        # Decision - SLA
        with col4:
            sla_status = "ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¢ Protected" if demo_data["decision"]["sla_preserved"] else "ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´ At Risk"
            st.metric(
                "SLA Status",
                sla_status,
                f"Final: {demo_data['decision']['final_pods']} pods"
            )

        history_df = get_demo_history()
        if history_df is not None and not history_df.empty:
            st.markdown("### Loop History")
            chart_cols = [col for col in ["predicted_cpu", "current_pods", "final_pods"] if col in history_df.columns]
            if chart_cols:
                st.line_chart(history_df.tail(50).set_index("timestamp")[chart_cols])
            action_cols = [col for col in ["timestamp", "scenario_name", "final_action", "current_pods", "final_pods"] if col in history_df.columns]
            if action_cols:
                st.dataframe(history_df.tail(10)[action_cols], use_container_width=True, hide_index=True)
    
    # ========================================================================
    # Data Update Status
    # ========================================================================
    st.markdown("---")
    st.caption("ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã…Â  Updates every 5 seconds | Health check every 30 seconds | No manual refresh needed")


def main():
    """Main entry point.
    
    Sets up page config and renders the overview dashboard.
    Used when running as standalone: streamlit run dashboard/app.py
    """
    render_overview()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    main()
