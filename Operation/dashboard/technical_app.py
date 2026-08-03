"""
Green DevOps Technical Dashboard - Level 2

Real-time technical monitoring for Engine 1 Workload Prediction Engine.
Displays live data from API endpoints, runtime storage, and log files.

IMPORTANT: This dashboard uses REAL DATA ONLY.
No hardcoded values or simulations. If a source is unavailable,
a clear error message is displayed instead of fake data.

Usage:
    streamlit run technical_app.py

Configuration:
    Adjust API_BASE_URL to point to your Engine 1 API server
"""

import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Optional, Dict, List, Tuple
import logging
from streamlit_autorefresh import st_autorefresh

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = "http://localhost:5050"
DATA_DIR = Path("data")
PREDICTIONS_DIR = DATA_DIR / "predictions"
RUNTIME_METRICS_DIR = DATA_DIR / "runtime_metrics"
CONFIG_PATH = Path("src/workload_prediction_engine/config.py")

# Auto-refresh interval
REFRESH_INTERVAL = 8  # seconds

# API Endpoints
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
PREDICT_ENDPOINT = f"{API_BASE_URL}/predict"
STATUS_ENDPOINT = f"{API_BASE_URL}/status"
METRICS_ENDPOINT = f"{API_BASE_URL}/metrics"

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Engine 1 Technical Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .tech-card {
        background-color: #1e1e1e;
        color: #e0e0e0;
        padding: 15px;
        border-radius: 5px;
        border-left: 3px solid #0066cc;
        font-family: monospace;
        font-size: 13px;
    }
    .status-ok {
        color: #28a745;
    }
    .status-warning {
        color: #ffc107;
    }
    .status-error {
        color: #dc3545;
    }
    .metric-label {
        font-size: 12px;
        color: #999;
        margin: 0;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #00ff00;
        margin: 0;
    }
    .source-label {
        font-size: 11px;
        color: #666;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# Session State Management
# ============================================================================

# Initialize all required session state keys to prevent "has no attribute" errors
if "api_available" not in st.session_state:
    st.session_state.api_available = None

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

if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if "api_status" not in st.session_state:
    st.session_state.api_status = None

if "api_check_time" not in st.session_state:
    st.session_state.api_check_time = 0

if "api_check_interval" not in st.session_state:
    st.session_state.api_check_interval = 30

# ============================================================================
# Auto-Refresh Configuration
# ============================================================================
# Trigger auto-refresh every 5 seconds
if st.session_state.auto_refresh_enabled:
    st_autorefresh(
        interval=5000,  # 5 seconds
        key="technical_dashboard_auto_refresh",
        debounce=False
    )

# ============================================================================
# Real Data Fetching Functions
# ============================================================================

def fetch_health_data() -> Optional[Dict]:
    """
    Fetch health status from Engine 1 API.
    
    Returns:
        Dict with health data or None if unavailable
    """
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None


def fetch_prediction_data() -> Optional[Dict]:
    """
    Fetch latest prediction from Engine 1 API.
    
    Returns:
        Dict with prediction data or None if unavailable
    """
    try:
        response = requests.get(PREDICT_ENDPOINT, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None


def fetch_status_data() -> Optional[Dict]:
    """
    Fetch detailed status from Engine 1 API.
    
    Returns:
        Dict with status data or None if unavailable
    """
    try:
        response = requests.get(STATUS_ENDPOINT, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None


def fetch_metrics_data(system_id: str) -> Optional[Dict]:
    """
    Fetch metrics summary for a system.
    
    Args:
        system_id: System identifier
    
    Returns:
        Dict with metrics data or None if unavailable
    """
    try:
        response = requests.get(f"{METRICS_ENDPOINT}/{system_id}", timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None


def load_prediction_history(system_id: str, limit: int = 50) -> pd.DataFrame:
    """
    Load prediction history from CSV storage.
    
    Args:
        system_id: System identifier
        limit: Max number of records to load
    
    Returns:
        DataFrame with prediction history or empty DataFrame if not available
    """
    try:
        csv_path = PREDICTIONS_DIR / f"{system_id}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            # Return most recent records
            return df.tail(limit).reset_index(drop=True)
    except Exception as e:
        pass
    return pd.DataFrame()


def load_runtime_metrics_history(system_id: str, limit: int = 50) -> pd.DataFrame:
    """
    Load runtime metrics history from runtime store.
    
    Args:
        system_id: System identifier
        limit: Max number of records to load
    
    Returns:
        DataFrame with runtime metrics or empty DataFrame if not available
    """
    try:
        csv_path = RUNTIME_METRICS_DIR / f"{system_id}_runtime_metrics.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            # Return most recent records
            return df.tail(limit).reset_index(drop=True)
    except Exception as e:
        pass
    return pd.DataFrame()


def get_config_values() -> Dict:
    """
    Extract configuration values from config.py.
    
    Returns:
        Dict with parsed config values
    """
    config = {}
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                content = f.read()
            
            # Extract key values
            for line in content.split('\n'):
                if '=' in line and not line.strip().startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        key = key.split()[-1].strip()
                        value = value.split('#')[0].strip()
                        
                        # Parse common config keys
                        if key == "PREDICTION_WINDOW_SECONDS":
                            config['prediction_window'] = int(value)
                        elif key == "SEQUENCE_LENGTH":
                            config['sequence_length'] = int(value)
                        elif key == "MODEL_VERSION":
                            config['model_version'] = value.strip('"\'')
                        elif key == "MODEL_PATH":
                            config['model_path'] = value.strip('"\'')
                    except:
                        continue
    except Exception as e:
        pass
    
    return config


def check_api_health() -> Tuple[bool, str]:
    """
    Check if API is reachable.
    
    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=3)
        if response.status_code == 200:
            return True, "API reachable"
        else:
            return False, f"API returned {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "API timeout"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_data_sources() -> Dict:
    """
    Check availability of data sources.
    
    Returns:
        Dict with status of each data source
    """
    sources = {
        "predictions_dir": PREDICTIONS_DIR.exists(),
        "runtime_metrics_dir": RUNTIME_METRICS_DIR.exists(),
        "config_file": CONFIG_PATH.exists(),
    }
    return sources


# ============================================================================
# UI Header
# ============================================================================

def render_header():
    """Render dashboard header."""
    st.markdown("# ⚙️ Green DevOps Technical Dashboard")
    st.markdown("### Engine 1 Runtime Monitoring and Diagnostics")
    st.markdown("---")


# ============================================================================
# System Overview Section
# ============================================================================

def render_system_overview():
    """Render system overview cards with real data."""
    st.markdown("## System Overview")
    
    # Fetch data
    health_data = fetch_health_data()
    status_data = fetch_status_data()
    config = get_config_values()
    
    if not health_data:
        st.error("❌ Cannot fetch system health - API unavailable")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Extract real data
    system_status = health_data.get("status", "unknown")
    current_mode = health_data.get("mode", "unknown")
    record_count = health_data.get("records_collected", 0)
    model_version = health_data.get("model_version", "unknown")
    
    with col1:
        st.metric("API Status", "✓ OK" if system_status == "healthy" else "✗ ERROR")
        st.caption(f"System: {system_status}")
    
    with col2:
        st.metric("Mode", current_mode.upper())
        st.caption(f"Phase: {'Learning' if current_mode == 'cold_start' else 'Production'}")
    
    with col3:
        st.metric("Records", record_count)
        st.caption(f"Runtime history size")
    
    with col4:
        st.metric("Model", model_version)
        st.caption(f"Version: {model_version}")
    
    # Additional info row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        window = config.get("prediction_window", "N/A")
        st.metric("Timestep", f"{window}s" if isinstance(window, int) else window)
        st.caption("Prediction window")
    
    with col2:
        seq_len = config.get("sequence_length", "N/A")
        st.metric("Sequence", seq_len)
        st.caption("Input sequence length")
    
    with col3:
        if status_data and "retraining" in status_data:
            retrain_ready = status_data["retraining"].get("ready", False)
            st.metric("Retrain Ready", "✓ YES" if retrain_ready else "✗ NO")
        else:
            st.metric("Retrain Ready", "? UNKNOWN")
        st.caption("Retraining status")
    
    with col4:
        timestamp = health_data.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                age = datetime.now(dt.tzinfo) - dt
                seconds = int(age.total_seconds())
                st.metric("Data Age", f"{seconds}s")
            except:
                st.metric("Data Age", "? ERROR")
        else:
            st.metric("Data Age", "? UNKNOWN")
        st.caption("Time since last update")
    
    st.markdown("---")


# ============================================================================
# Current Prediction Panel
# ============================================================================

def render_current_prediction():
    """Render current prediction with real data."""
    st.markdown("## Current Prediction")
    
    pred_data = fetch_prediction_data()
    
    if not pred_data or pred_data.get("status") != "success":
        st.error("❌ Cannot fetch current prediction - API unavailable")
        return
    
    prediction = pred_data.get("prediction", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cpu = prediction.get("predicted_cpu_percent", -1)
        st.metric("Predicted CPU", f"{cpu:.1f}%" if cpu >= 0 else "N/A")
        st.caption("Next 30-second forecast")
    
    with col2:
        load = prediction.get("predicted_load_level", "UNKNOWN")
        st.metric("Load Level", load)
        color = "🟢" if load == "LOW" else "🟡" if load == "NORMAL" else "🔴"
        st.caption(f"Status: {color} {load}")
    
    with col3:
        pods = prediction.get("recommended_pods", -1)
        st.metric("Recommended Pods", pods if pods > 0 else "N/A")
        st.caption("Scaling recommendation")
    
    with col4:
        confidence = prediction.get("confidence", -1)
        if confidence >= 0:
            st.metric("Confidence", f"{confidence:.2f}")
        else:
            st.metric("Confidence", "N/A")
        st.caption("Prediction quality score")
    
    # Additional prediction details
    col1, col2 = st.columns(2)
    
    with col1:
        source = prediction.get("data_source", "unknown")
        st.caption(f"**Data Source**: {source}")
    
    with col2:
        timestamp = prediction.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(str(timestamp) if not timestamp.endswith('Z') else timestamp.replace('Z', '+00:00'))
                st.caption(f"**Prediction Time**: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                st.caption(f"**Prediction Time**: {timestamp}")
    
    st.markdown("---")


# ============================================================================
# Runtime Metrics Panel
# ============================================================================

def render_runtime_metrics():
    """Render runtime metrics collection status."""
    st.markdown("## Runtime Metrics")
    
    # Try to get system ID from health data
    health_data = fetch_health_data()
    system_id = health_data.get("system_id", "main_system") if health_data else "main_system"
    
    # Load runtime metrics
    metrics_df = load_runtime_metrics_history(system_id, limit=12)
    
    if metrics_df.empty:
        st.warning("⚠️ No runtime metrics data available yet")
        return
    
    # Display latest metrics
    col1, col2, col3, col4 = st.columns(4)
    
    latest = metrics_df.iloc[-1]
    
    with col1:
        cpu = latest.get("cpu", -1)
        st.metric("Latest CPU", f"{float(cpu):.1f}%" if cpu != -1 else "N/A")
        st.caption("Most recent measurement")
    
    with col2:
        mem = latest.get("memory", -1)
        if mem != -1:
            # Convert memory to MB if in bytes
            if mem > 1000:
                mem_mb = mem / 1024 / 1024
                st.metric("Latest Memory", f"{mem_mb:.1f} MB")
            else:
                st.metric("Latest Memory", f"{mem:.1f} MB")
        else:
            st.metric("Latest Memory", "N/A")
        st.caption("Most recent measurement")
    
    with col3:
        ts = latest.get("timestamp", "")
        if ts:
            try:
                ts_int = int(ts)
                dt = datetime.fromtimestamp(ts_int)
                st.metric("Collection Time", dt.strftime("%H:%M:%S"))
            except:
                st.metric("Collection Time", "N/A")
        else:
            st.metric("Collection Time", "N/A")
        st.caption("When data was collected")
    
    with col4:
        count = len(metrics_df)
        st.metric("Records Stored", count)
        st.caption("Total in runtime store")
    
    # Show metrics table
    if len(metrics_df) > 0:
        st.subheader("Recent Metrics (Latest 12)")
        
        display_df = metrics_df[["timestamp", "cpu", "memory"]].copy()
        
        # Convert timestamps if possible
        if "timestamp" in display_df.columns:
            try:
                display_df["timestamp"] = display_df["timestamp"].apply(
                    lambda x: datetime.fromtimestamp(int(x)).strftime("%H:%M:%S") if x else "N/A"
                )
            except:
                pass
        
        st.dataframe(display_df, use_container_width=True)
    
    st.markdown("---")


# ============================================================================
# Trend Charts
# ============================================================================

def render_trend_charts():
    """Render trend charts with real data."""
    st.markdown("## Trend Analysis")
    
    health_data = fetch_health_data()
    system_id = health_data.get("system_id", "main_system") if health_data else "main_system"
    
    # Load both metrics and predictions
    metrics_df = load_runtime_metrics_history(system_id, limit=100)
    pred_df = load_prediction_history(system_id, limit=100)
    
    if metrics_df.empty and pred_df.empty:
        st.warning("⚠️ No historical data available for trends")
        return
    
    col1, col2 = st.columns(2)
    
    # CPU Trend Chart
    with col1:
        if not metrics_df.empty:
            st.subheader("CPU Usage Trend")
            
            chart_data = metrics_df[["timestamp", "cpu"]].copy()
            
            # Use timestamp as index if possible
            if "timestamp" in chart_data.columns:
                try:
                    chart_data["timestamp"] = pd.to_datetime(
                        chart_data["timestamp"].apply(
                            lambda x: datetime.fromtimestamp(int(x)) if x else None
                        )
                    )
                    chart_data = chart_data.set_index("timestamp")
                except:
                    chart_data = chart_data.set_index(range(len(chart_data)))
            
            st.line_chart(chart_data["cpu"] if "cpu" in chart_data else chart_data)
        else:
            st.info("ℹ️ No CPU history data available")
    
    # Prediction Trend Chart
    with col2:
        if not pred_df.empty:
            st.subheader("Predicted CPU Trend")
            
            pred_chart = pred_df[["timestamp", "predicted_cpu"]].copy()
            
            if "predicted_cpu" not in pred_chart.columns:
                st.warning("Predicted CPU column not found")
            else:
                # Try to set timestamp as index
                try:
                    pred_chart["timestamp"] = pd.to_numeric(pred_chart["timestamp"], errors="coerce")
                    pred_chart = pred_chart.dropna()
                except:
                    pass
                
                st.line_chart(pred_chart["predicted_cpu"] if "predicted_cpu" in pred_chart else pred_chart)
        else:
            st.info("ℹ️ No prediction history available")
    
    st.markdown("---")


# ============================================================================
# Prediction Diagnostics
# ============================================================================

def render_diagnostics():
    """Render prediction diagnostics panel."""
    st.markdown("## Prediction Diagnostics")
    
    health_data = fetch_health_data()
    status_data = fetch_status_data()
    config = get_config_values()
    
    if not health_data:
        st.error("❌ Cannot fetch diagnostics - API unavailable")
        return
    
    col1, col2, col3 = st.columns(3)
    
    # Mode diagnostics
    with col1:
        st.subheader("Mode Analysis")
        current_mode = health_data.get("mode", "unknown")
        records = health_data.get("records_collected", 0)
        
        mode_info = []
        mode_info.append(f"Current Mode: **{current_mode.upper()}**")
        
        if current_mode == "cold_start":
            mode_info.append("Status: 🟡 Using bootstrap values")
            mode_info.append(f"Records: {records}/12 needed for runtime")
        else:
            mode_info.append("Status: 🟢 Using actual runtime data")
            mode_info.append(f"Records: {records} (>= 12)")
        
        for info in mode_info:
            st.caption(info)
    
    # Sequence diagnostics
    with col2:
        st.subheader("Sequence Configuration")
        seq_len = config.get("sequence_length", "N/A")
        window = config.get("prediction_window", "N/A")
        
        seq_info = []
        seq_info.append(f"Sequence Length: **{seq_len}**")
        seq_info.append(f"Timestep: **{window}s**")
        if isinstance(seq_len, int) and isinstance(window, int):
            total_window = seq_len * window
            seq_info.append(f"Total Window: {total_window}s")
        
        for info in seq_info:
            st.caption(info)
    
    # Data readiness
    with col3:
        st.subheader("Runtime Readiness")
        
        records = health_data.get("records_collected", 0)
        ready_for_runtime = records >= 12
        
        if ready_for_runtime:
            st.success(f"✓ Runtime Ready ({records} records)")
        else:
            st.warning(f"⚠ Cold-Start Mode ({records}/12 records)")
        
        if status_data and "retraining" in status_data:
            threshold = status_data["retraining"].get("records_threshold", 2880)
            retrain_ready = status_data["retraining"].get("ready", False)
            
            st.caption(f"Retrain threshold: {threshold} records")
            if retrain_ready:
                st.caption("✓ Ready for retraining")
            else:
                st.caption(f"⊘ {threshold - records} records until retrain")
    
    st.markdown("---")


# ============================================================================
# Runtime Storage Status
# ============================================================================

def render_storage_status():
    """Render runtime storage status."""
    st.markdown("## Runtime Storage Status")
    
    sources = check_data_sources()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status = "✓ EXISTS" if sources["predictions_dir"] else "✗ NOT FOUND"
        st.caption(f"Predictions: {status}")
        st.caption(f"Path: `{PREDICTIONS_DIR}`")
    
    with col2:
        status = "✓ EXISTS" if sources["runtime_metrics_dir"] else "✗ NOT FOUND"
        st.caption(f"Metrics: {status}")
        st.caption(f"Path: `{RUNTIME_METRICS_DIR}`")
    
    with col3:
        status = "✓ FOUND" if sources["config_file"] else "✗ NOT FOUND"
        st.caption(f"Config: {status}")
        st.caption(f"Path: `{CONFIG_PATH}`")
    
    st.markdown("---")


# ============================================================================
# Prediction History Table
# ============================================================================

def render_prediction_history():
    """Render recent predictions table with real data."""
    st.markdown("## Prediction History")
    
    health_data = fetch_health_data()
    system_id = health_data.get("system_id", "main_system") if health_data else "main_system"
    
    pred_df = load_prediction_history(system_id, limit=30)
    
    if pred_df.empty:
        st.warning("⚠️ No prediction history available")
        return
    
    st.subheader(f"Recent Predictions for: `{system_id}`")
    
    # Select columns to display
    display_cols = []
    if "timestamp" in pred_df.columns:
        display_cols.append("timestamp")
    if "predicted_cpu" in pred_df.columns:
        display_cols.append("predicted_cpu")
    if "predicted_load_level" in pred_df.columns:
        display_cols.append("predicted_load_level")
    if "recommended_pods" in pred_df.columns:
        display_cols.append("recommended_pods")
    if "data_source" in pred_df.columns:
        display_cols.append("data_source")
    
    if display_cols:
        display_df = pred_df[display_cols].copy()
        
        # Format timestamp column
        if "timestamp" in display_df.columns:
            try:
                display_df["timestamp"] = display_df["timestamp"].apply(
                    lambda x: datetime.fromtimestamp(int(x)).strftime("%Y-%m-%d %H:%M:%S") if x else "N/A"
                )
            except:
                pass
        
        # Format CPU column
        if "predicted_cpu" in display_df.columns:
            try:
                display_df["predicted_cpu"] = display_df["predicted_cpu"].apply(
                    lambda x: f"{float(x):.2f}%" if x else "N/A"
                )
            except:
                pass
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.error("Could not parse prediction data columns")
    
    st.markdown("---")


# ============================================================================
# Alerts and Warnings Panel
# ============================================================================

def render_alerts():
    """Render alerts and warnings based on real system state."""
    st.markdown("## Alerts & Warnings")
    
    alerts = []
    warnings = []
    errors = []
    
    # Check API health
    api_ok, api_msg = check_api_health()
    if not api_ok:
        errors.append(f"🔴 API Unavailable: {api_msg}")
    else:
        alerts.append("🟢 API Available")
    
    # Check data sources
    sources = check_data_sources()
    if not sources["predictions_dir"]:
        warnings.append(f"⚠️ Predictions directory not found: {PREDICTIONS_DIR}")
    if not sources["runtime_metrics_dir"]:
        warnings.append(f"⚠️ Runtime metrics directory not found: {RUNTIME_METRICS_DIR}")
    if not sources["config_file"]:
        warnings.append(f"⚠️ Config file not found: {CONFIG_PATH}")
    
    # Check mode and records
    health_data = fetch_health_data()
    if health_data:
        mode = health_data.get("mode", "")
        records = health_data.get("records_collected", 0)
        
        if mode == "cold_start" and records < 5:
            warnings.append(f"⚠️ Cold-start mode: Only {records} records collected (needs 12 for runtime)")
        
        if records == 0:
            errors.append("🔴 No runtime records collected yet")
    
    # Check predictions
    pred_data = fetch_prediction_data()
    if not pred_data:
        errors.append("🔴 Cannot fetch predictions from API")
    
    # Display alerts
    if errors:
        st.error("### Errors")
        for error in errors:
            st.write(error)
    
    if warnings:
        st.warning("### Warnings")
        for warning in warnings:
            st.write(warning)
    
    if alerts:
        st.success("### Alerts")
        for alert in alerts:
            st.write(alert)
    
    if not (errors or warnings or alerts):
        st.success("✓ No issues detected - System operating normally")
    
    st.markdown("---")


# ============================================================================
# API/Backend Health Panel
# ============================================================================

def render_backend_health():
    """Render API and backend health status."""
    st.markdown("## Backend Health")
    
    col1, col2, col3 = st.columns(3)
    
    # API Health
    with col1:
        st.subheader("API Endpoint")
        api_ok, api_msg = check_api_health()
        
        if api_ok:
            st.success(f"✓ Reachable")
        else:
            st.error(f"✗ {api_msg}")
        
        st.caption(f"`{API_BASE_URL}`")
    
    # Data Storage
    with col2:
        st.subheader("Data Storage")
        sources = check_data_sources()
        
        all_available = all(sources.values())
        
        if all_available:
            st.success(f"✓ All sources available")
        else:
            missing = [k for k, v in sources.items() if not v]
            st.warning(f"⚠ Missing: {len(missing)}/{len(sources)}")
        
        for key, value in sources.items():
            symbol = "✓" if value else "✗"
            st.caption(f"{symbol} {key}")
    
    # Endpoint Status
    with col3:
        st.subheader("Endpoints")
        
        endpoints_status = {
            "/health": HEALTH_ENDPOINT,
            "/predict": PREDICT_ENDPOINT,
            "/status": STATUS_ENDPOINT,
            "/metrics": METRICS_ENDPOINT,
        }
        
        for endpoint, url in endpoints_status.items():
            try:
                response = requests.head(url, timeout=2)
                status = "✓" if response.status_code < 400 else "✗"
            except:
                status = "✗"
            
            st.caption(f"{status} {endpoint}")
    
    st.markdown("---")


# ============================================================================
# Main Dashboard
# ============================================================================
# Dashboard Rendering
# ============================================================================

def render_technical():
    """Render Level 2 Technical Dashboard.
    
    This dashboard is for technical users and shows:
    - System Overview (4 tabs)
    - Runtime Metrics & Trends
    - Diagnostics & Retraining Status
    - Backend Health & API Status
    """
    render_header()
    
    # Create tabs for organization
    tab1, tab2, tab3, tab4 = st.tabs([
        "System Overview",
        "Metrics & Trends",
        "Diagnostics",
        "Backend Status"
    ])
    
    with tab1:
        render_system_overview()
        render_current_prediction()
    
    with tab2:
        render_runtime_metrics()
        render_trend_charts()
        render_prediction_history()
    
    with tab3:
        render_diagnostics()
        render_storage_status()
        render_alerts()
    
    with tab4:
        render_backend_health()
    
    # Auto-refresh indicator and control
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        current_time = time.time()
        time_since = current_time - st.session_state.last_refresh
        st.caption(f"Last refresh: {time_since:.1f}s ago | Updates every 5s (health check every 30s)")
    
    with col2:
        if st.button("🔄 Refresh Now"):
            st.session_state.last_refresh = 0
            st.rerun()
    
    # Auto-refresh logic (safe time-based approach)
    current_time = time.time()
    if (current_time - st.session_state.last_refresh) > 5:
        st.session_state.last_refresh = current_time
        st.rerun()


def main():
    """Main entry point.
    
    Sets up page config and renders the technical dashboard.
    Used when running as standalone: streamlit run dashboard/technical_app.py
    """
    render_technical()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    main()
