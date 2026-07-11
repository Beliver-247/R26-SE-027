"""
Dashboard Demo Data Adapter

Provides functions to read demo scenario data and display it in the dashboard.
This module acts as a bridge between the demo scenario runner and the dashboard.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# ============================================================================
# Configuration
# ============================================================================

DEMO_DIR = Path("data/demo")
DEMO_LATEST_FILE = DEMO_DIR / "latest.json"
DEMO_HISTORY_FILE = DEMO_DIR / "history.csv"
LEGACY_DEMO_LATEST_FILE = DEMO_DIR / "latest_decision.json"
LEGACY_DEMO_HISTORY_FILE = DEMO_DIR / "loop_history.csv"


# ============================================================================
# Demo Data Reading Functions
# ============================================================================

def is_demo_mode_available() -> bool:
    """Check if demo data directory exists."""
    return DEMO_DIR.exists() and (DEMO_LATEST_FILE.exists() or LEGACY_DEMO_LATEST_FILE.exists())


def load_latest_demo_data():
    candidates = [
        Path("data/demo/latest.json"),
        Path("data/demo/latest_decision.json"),
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    path = max(existing, key=lambda candidate: candidate.stat().st_mtime)
    with open(path, "r") as f:
        return json.load(f)


def get_latest_demo_result() -> Optional[Dict[str, Any]]:
    """
    Get the latest demo scenario result.
    
    Returns:
        Dict with latest scenario result or None if not available
    """
    try:
        return load_latest_demo_data()
    except Exception as e:
        print(f"Error reading demo file: {e}")
        return None


def get_demo_history() -> Optional[pd.DataFrame]:
    """
    Get demo scenario history.
    
    Returns:
        DataFrame with scenario history or None if not available
    """
    candidates = [DEMO_HISTORY_FILE, LEGACY_DEMO_HISTORY_FILE]
    existing = [path for path in candidates if path.exists() and path.stat().st_size > 0]
    if not existing:
        return None
    history_file = max(existing, key=lambda candidate: candidate.stat().st_mtime)
    
    try:
        df = pd.read_csv(history_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format="mixed", utc=True)
        return df
    except Exception as e:
        print(f"Error reading history file: {e}")
        return None


def format_demo_display_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format demo result for dashboard display.
    
    Extracts key information for easy dashboard consumption.
    
    Args:
        result: Raw demo scenario result
    
    Returns:
        Formatted display data
    """
    try:
        decision_payload = result.get("steps", {}).get("decision", {}).get("decision", {}) or result.get("decision", {})
        final_action = (
            result.get("final_action")
            or decision_payload.get("final_action")
            or decision_payload.get("action")
            or result.get("decision", {}).get("action", "")
        )
        final_pods = (
            result.get("final_required_pods")
            or decision_payload.get("final_required_pods")
            or decision_payload.get("final_pods")
            or result.get("decision", {}).get("final_pods", 0)
        )
        jobs_to_delay = (
            result.get("jobs_to_delay")
            or len(decision_payload.get("jobs_to_delay", []))
            or result.get("engine3", {}).get("delayable_jobs", 0)
        )
        input_echo = result.get("steps", {}).get("decision", {}).get("input_echo", {})
        engine2_input = result.get("steps", {}).get("engine2", {}).get("input", {})
        current_pods = result.get("current_pods") or input_echo.get("current_pods") or engine2_input.get("current_pods", 0)
        raw_required_pods = (
            result.get("raw_required_pods")
            or input_echo.get("raw_required_pods")
            or engine2_input.get("raw_required_pods")
            or result.get("engine1", {}).get("recommended_pods", 0)
        )

        display = {
            "timestamp": result.get("timestamp", ""),
            "scenario_name": result.get("scenario_name", ""),
            "system_id": result.get("system_id", ""),
            "current_pods": current_pods,
            "raw_required_pods": raw_required_pods,
            "final_required_pods": final_pods,
            "final_action": final_action,
            "jobs_to_delay": jobs_to_delay,
            "carbon_saving": result.get("carbon_saving", result.get("engine2", {}).get("carbon_saving_gco2", 0)),
            "sla_preserved": result.get("sla_preserved", result.get("decision", {}).get("sla_preserved", False)),
            
            # Engine 1 (Prediction)
            "engine1": {
                "predicted_cpu": result.get("predicted_cpu", result.get("engine1", {}).get("predicted_cpu", 0)),
                "predicted_load_level": result.get("load_level", result.get("engine1", {}).get("predicted_load_level", "")),
                "recommended_pods": final_pods or result.get("engine1", {}).get("recommended_pods", 0),
                "raw_required_pods": result.get("raw_required_pods", result.get("engine1", {}).get("recommended_pods", 0)),
                "confidence": result.get("engine1", {}).get("confidence", 0),
            },
            
            # Engine 2 (Carbon)
            "engine2": {
                "carbon_saving_gco2": result.get("steps", {}).get("engine2", {}).get("carbon_saving_gco2", 0),
                "carbon_saving_percent": result.get("steps", {}).get("engine2", {}).get("carbon_saving_percent", 0),
                "recommended_action": result.get("steps", {}).get("engine2", {}).get("recommended_action", ""),
            },
            
            # Engine 3 (Jobs)
            "engine3": {
                "delayable_jobs": result.get("steps", {}).get("engine3", {}).get("delayable_jobs", 0),
                "delayable_job_ids": result.get("steps", {}).get("engine3", {}).get("delayable_job_ids", []),
                "workload_reduction_percent": result.get("steps", {}).get("engine3", {}).get("workload_reduction_percent", 0),
            },
            
            # Decision Layer
            "decision": {
                "action": final_action,
                "final_pods": final_pods,
                "sla_preserved": result.get("steps", {}).get("decision", {}).get("decision", {}).get("sla_preserved", False),
                "reasoning": result.get("steps", {}).get("decision", {}).get("reasoning", {}),
            }
        }
        
        return display
    
    except Exception as e:
        print(f"Error formatting demo data: {e}")
        return {}


# ============================================================================
# Dashboard Integration Helpers
# ============================================================================

def render_demo_mode_indicator(is_demo: bool = False):
    """
    Generate HTML/Markdown for demo mode indicator.
    
    Args:
        is_demo: Whether demo mode is active
    
    Returns:
        Markdown string for Streamlit display
    """
    if is_demo:
        return "🟢 **Live Pipeline (Test Scenarios)** - Engine-processed loop data is active"
    else:
        return "⚪ Production mode"


def get_scenario_explanation(scenario_name: str) -> str:
    """
    Get explanation for a scenario.
    
    Args:
        scenario_name: Name of the scenario
    
    Returns:
        Explanation string
    """
    explanations = {
        "LOW LOAD": "Light workload detected. System can scale down to save resources and reduce carbon emissions.",
        "NORMAL LOAD": "Normal balanced workload. System operating at optimal efficiency.",
        "HIGH LOAD": "Heavy workload detected. System recommends scale-up to maintain SLA.",
        "HIGH LOAD NO DELAY": "Critical workload with no delayable jobs. All jobs must run immediately.",
        "BACK TO LOW LOAD": "Workload reduced. Scale-down opportunity for efficiency and carbon savings."
    }
    return explanations.get(scenario_name, "Scenario running...")


def get_action_description(action: str) -> str:
    """
    Get human-readable description of an action.
    
    Args:
        action: Action name (e.g., "scale_up", "scale_down", "no_action")
    
    Returns:
        Description string
    """
    descriptions = {
        "scale_up": "Increase pod count for performance",
        "scale_down": "Decrease pod count to save resources",
        "hybrid": "Combination of job delay and moderate scaling",
        "no_action": "Maintain current configuration",
    }
    return descriptions.get(action, f"Action: {action}")
