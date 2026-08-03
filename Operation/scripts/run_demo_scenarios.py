#!/usr/bin/env python3
"""
Demo Scenario Runner for Green DevOps System.

Simulates realistic workload patterns by calling existing APIs with 5 different scenarios:
1. LOW LOAD - scale down opportunity
2. NORMAL LOAD - balanced operation  
3. HIGH LOAD - scale up required
4. HIGH LOAD NO DELAY - all jobs must run
5. BACK TO LOW LOAD - optimization opportunity

This runner does NOT modify engine logic, only drives it with test inputs via APIs.
Results are stored for dashboard consumption.

Usage:
    python scripts/run_demo_scenarios.py --api-url http://localhost:5000 --interval 5 --duration 300
"""

import requests
import json
import time
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import csv

# ============================================================================
# Configuration
# ============================================================================

# Demo data directory
DEMO_DIR = Path("data/demo")
DEMO_DIR.mkdir(parents=True, exist_ok=True)

# Output files
DEMO_HISTORY_FILE = DEMO_DIR / "demo_history.csv"
DEMO_LATEST_FILE = DEMO_DIR / "latest_decision.json"
DEMO_SCENARIOS_FILE = DEMO_DIR / "scenarios.json"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Demo Scenario Definitions
# ============================================================================

DEMO_SCENARIOS = [
    {
        "id": 1,
        "name": "LOW LOAD",
        "description": "Light workload - scale down opportunity",
        "predicted_cpu": 20,
        "predicted_load_level": "LOW",
        "current_pods": 3,
        "recommended_pods": 1,
        "jobs": [
            {
                "job_id": "job_low_1",
                "job_type": "report_generation",
                "priority": "LOW",
                "estimated_runtime_seconds": 180,
                "estimated_cpu_percent": 5.0,
                "deadline_seconds": 3600,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_low_2",
                "job_type": "data_cleanup",
                "priority": "LOW",
                "estimated_runtime_seconds": 120,
                "estimated_cpu_percent": 3.0,
                "deadline_seconds": 7200,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_low_3",
                "job_type": "analytics",
                "priority": "LOW",
                "estimated_runtime_seconds": 300,
                "estimated_cpu_percent": 4.0,
                "deadline_seconds": 7200,
                "already_delayed_seconds": 0
            }
        ]
    },
    {
        "id": 2,
        "name": "NORMAL LOAD",
        "description": "Balanced workload - standard operation",
        "predicted_cpu": 55,
        "predicted_load_level": "NORMAL",
        "current_pods": 3,
        "recommended_pods": 3,
        "jobs": [
            {
                "job_id": "job_norm_1",
                "job_type": "background_sync",
                "priority": "HIGH",
                "estimated_runtime_seconds": 60,
                "estimated_cpu_percent": 15.0,
                "deadline_seconds": 300,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_norm_2",
                "job_type": "cache_update",
                "priority": "MEDIUM",
                "estimated_runtime_seconds": 120,
                "estimated_cpu_percent": 8.0,
                "deadline_seconds": 900,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_norm_3",
                "job_type": "maintenance",
                "priority": "LOW",
                "estimated_runtime_seconds": 180,
                "estimated_cpu_percent": 5.0,
                "deadline_seconds": 3600,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_norm_4",
                "job_type": "indexing",
                "priority": "LOW",
                "estimated_runtime_seconds": 240,
                "estimated_cpu_percent": 6.0,
                "deadline_seconds": 7200,
                "already_delayed_seconds": 0
            }
        ]
    },
    {
        "id": 3,
        "name": "HIGH LOAD",
        "description": "Heavy workload - scale up required",
        "predicted_cpu": 85,
        "predicted_load_level": "HIGH",
        "current_pods": 2,
        "recommended_pods": 5,
        "jobs": [
            {
                "job_id": "job_high_1",
                "job_type": "payment_processing",
                "priority": "HIGH",
                "estimated_runtime_seconds": 10,
                "estimated_cpu_percent": 25.0,
                "deadline_seconds": 30,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_high_2",
                "job_type": "user_request",
                "priority": "HIGH",
                "estimated_runtime_seconds": 5,
                "estimated_cpu_percent": 20.0,
                "deadline_seconds": 10,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_high_3",
                "job_type": "data_import",
                "priority": "MEDIUM",
                "estimated_runtime_seconds": 120,
                "estimated_cpu_percent": 15.0,
                "deadline_seconds": 600,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_high_4",
                "job_type": "report_generation",
                "priority": "LOW",
                "estimated_runtime_seconds": 180,
                "estimated_cpu_percent": 10.0,
                "deadline_seconds": 3600,
                "already_delayed_seconds": 0
            }
        ]
    },
    {
        "id": 4,
        "name": "HIGH LOAD NO DELAY",
        "description": "Critical workload - no jobs can be delayed",
        "predicted_cpu": 90,
        "predicted_load_level": "HIGH",
        "current_pods": 3,
        "recommended_pods": 5,
        "jobs": [
            {
                "job_id": "job_crit_1",
                "job_type": "payment_processing",
                "priority": "HIGH",
                "estimated_runtime_seconds": 10,
                "estimated_cpu_percent": 25.0,
                "deadline_seconds": 15,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_crit_2",
                "job_type": "transaction_settlement",
                "priority": "HIGH",
                "estimated_runtime_seconds": 15,
                "estimated_cpu_percent": 30.0,
                "deadline_seconds": 20,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_crit_3",
                "job_type": "user_facing_api",
                "priority": "HIGH",
                "estimated_runtime_seconds": 5,
                "estimated_cpu_percent": 22.0,
                "deadline_seconds": 10,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_crit_4",
                "job_type": "monitoring",
                "priority": "HIGH",
                "estimated_runtime_seconds": 20,
                "estimated_cpu_percent": 15.0,
                "deadline_seconds": 30,
                "already_delayed_seconds": 0
            }
        ]
    },
    {
        "id": 5,
        "name": "BACK TO LOW LOAD",
        "description": "Workload reduced - another scale down opportunity",
        "predicted_cpu": 25,
        "predicted_load_level": "LOW",
        "current_pods": 5,
        "recommended_pods": 1,
        "jobs": [
            {
                "job_id": "job_final_1",
                "job_type": "cleanup",
                "priority": "LOW",
                "estimated_runtime_seconds": 200,
                "estimated_cpu_percent": 4.0,
                "deadline_seconds": 3600,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_final_2",
                "job_type": "archiving",
                "priority": "LOW",
                "estimated_runtime_seconds": 180,
                "estimated_cpu_percent": 5.0,
                "deadline_seconds": 7200,
                "already_delayed_seconds": 0
            },
            {
                "job_id": "job_final_3",
                "job_type": "optimization",
                "priority": "LOW",
                "estimated_runtime_seconds": 240,
                "estimated_cpu_percent": 3.0,
                "deadline_seconds": 7200,
                "already_delayed_seconds": 0
            }
        ]
    }
]

# ============================================================================
# Demo Scenario Runner
# ============================================================================

class DemoScenarioRunner:
    """Runs demo scenarios through the Green DevOps API system."""
    
    def __init__(self, api_url: str = "http://localhost:5000", system_id: str = "demo-system"):
        """
        Initialize the demo scenario runner.
        
        Args:
            api_url: Base URL of the Green DevOps API
            system_id: System identifier for demo scenarios
        """
        self.api_url = api_url
        self.system_id = system_id
        self.scenario_index = 0
        self.history = []
        
        logger.info(f"Demo Scenario Runner initialized")
        logger.info(f"  API URL: {api_url}")
        logger.info(f"  System ID: {system_id}")
        logger.info(f"  Demo Data Dir: {DEMO_DIR.absolute()}")
    
    def run_scenario(self, scenario: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Run a single demo scenario through the API pipeline.
        
        Steps:
        1. Call Engine 3 (Jobs) endpoint
        2. Call Engine 2 (Carbon) endpoint with Engine 3 output
        3. Call Decision Layer endpoint with Engine 1/2/3 outputs
        4. Store results
        
        Args:
            scenario: Scenario definition dict
        
        Returns:
            Complete scenario result or None if failed
        """
        logger.info("\n" + "="*80)
        logger.info(f"SCENARIO {scenario['id']}: {scenario['name']}")
        logger.info("="*80)
        logger.info(f"Description: {scenario['description']}")
        
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "system_id": self.system_id,
            "steps": {}
        }
        
        # Step 1: Engine 3 - Job Evaluation
        # ────────────────────────────────────────────────────────────────────────
        logger.info("\n[Step 1] Engine 3: Job Prioritization Evaluation")
        logger.info("-" * 80)
        
        engine3_output = self._call_jobs_evaluate(scenario)
        if not engine3_output:
            logger.error("Engine 3 evaluation failed")
            return None
        
        result["steps"]["engine3"] = engine3_output
        
        # Step 2: Engine 2 - Carbon Evaluation
        # ────────────────────────────────────────────────────────────────────────
        logger.info("\n[Step 2] Engine 2: Carbon Emission Evaluation")
        logger.info("-" * 80)
        
        engine2_output = self._call_carbon_evaluate(scenario, engine3_output)
        if not engine2_output:
            logger.error("Engine 2 evaluation failed")
            return None
        
        result["steps"]["engine2"] = engine2_output
        
        # Step 3: Engine 1 - Prediction (Simulated)
        # ────────────────────────────────────────────────────────────────────────
        logger.info("\n[Step 3] Engine 1: Prediction (Simulated)")
        logger.info("-" * 80)
        
        engine1_output = self._create_engine1_output(scenario)
        result["steps"]["engine1"] = engine1_output
        logger.info(f"✓ Engine 1 Output created")
        logger.info(f"  Predicted CPU: {engine1_output['prediction']['predicted_cpu']}%")
        logger.info(f"  Load Level: {engine1_output['prediction']['predicted_load_level']}")
        logger.info(f"  Recommended Pods: {engine1_output['prediction']['recommended_pods']}")
        
        # Step 4: Decision Layer - Final Decision
        # ────────────────────────────────────────────────────────────────────────
        logger.info("\n[Step 4] Decision Layer: Final Decision")
        logger.info("-" * 80)
        
        decision_output = self._call_decision_evaluate(
            scenario, engine1_output, engine2_output, engine3_output
        )
        if not decision_output:
            logger.error("Decision Layer evaluation failed")
            return None
        
        result["steps"]["decision"] = decision_output
        
        # Summary
        # ────────────────────────────────────────────────────────────────────────
        logger.info("\n[SUMMARY]")
        logger.info("="*80)
        decision = decision_output.get("decision", {})
        logger.info(f"Final Action: {decision.get('action', 'N/A')}")
        logger.info(f"Final Pod Count: {decision.get('final_pods', 'N/A')}")
        logger.info(f"SLA Preserved: {decision.get('sla_preserved', 'N/A')}")
        logger.info(f"Jobs Delayed: {engine3_output.get('delayable_jobs', 0)}")
        logger.info(f"Carbon Saving: {engine2_output.get('carbon_saving_gco2', 0):.1f} g CO2")
        
        return result
    
    def _call_jobs_evaluate(self, scenario: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call Engine 3 /jobs/evaluate endpoint."""
        try:
            url = f"{self.api_url}/jobs/evaluate"
            payload = {
                "jobs": scenario["jobs"],
                "backlog_size": len(scenario["jobs"]),
                "current_load_level": scenario["predicted_load_level"],
                "current_cpu": scenario["predicted_cpu"],
                "current_pods": scenario["current_pods"]
            }
            
            logger.info(f"Calling: POST {url}")
            logger.info(f"  Jobs: {len(scenario['jobs'])}")
            logger.info(f"  CPU: {scenario['predicted_cpu']}%")
            logger.info(f"  Load: {scenario['predicted_load_level']}")
            
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            
            output = response.json()
            logger.info(f"✓ Engine 3 Response: {response.status_code}")
            logger.info(f"  Delayable Jobs: {output.get('delayable_jobs', 0)}")
            logger.info(f"  Workload Reduction: {output.get('workload_reduction_percent', 0)*100:.1f}%")
            
            return output
        
        except Exception as e:
            logger.error(f"✗ Engine 3 call failed: {e}")
            return None
    
    def _call_carbon_evaluate(
        self, scenario: Dict[str, Any], engine3_output: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call Engine 2 /carbon/evaluate endpoint."""
        try:
            url = f"{self.api_url}/carbon/evaluate"
            payload = {
                "system_id": self.system_id,
                "predicted_cpu": scenario["predicted_cpu"],
                "predicted_load_level": scenario["predicted_load_level"],
                "recommended_pods": scenario["recommended_pods"],
                "current_pods": scenario["current_pods"],
                "prediction_window_seconds": 30,
                "delayable_jobs": engine3_output.get("delayable_jobs", 0),
                "workload_reduction_percent": engine3_output.get("workload_reduction_percent", 0.0)
            }
            
            logger.info(f"Calling: POST {url}")
            logger.info(f"  Current Pods: {scenario['current_pods']}")
            logger.info(f"  Recommended Pods: {scenario['recommended_pods']}")
            
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            
            output = response.json()
            logger.info(f"✓ Engine 2 Response: {response.status_code}")
            logger.info(f"  Carbon Saving: {output.get('carbon_saving_gco2', 0):.1f} g CO2")
            logger.info(f"  Recommended Action: {output.get('recommended_action', 'N/A')}")
            
            return output
        
        except Exception as e:
            logger.error(f"✗ Engine 2 call failed: {e}")
            return None
    
    def _call_decision_evaluate(
        self,
        scenario: Dict[str, Any],
        engine1_output: Dict[str, Any],
        engine2_output: Dict[str, Any],
        engine3_output: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call Decision Layer /decision/evaluate endpoint."""
        try:
            url = f"{self.api_url}/decision/evaluate"
            payload = {
                "system_id": self.system_id,
                "current_pods": scenario["current_pods"],
                "engine1_output": engine1_output,
                "engine2_output": engine2_output,
                "engine3_output": engine3_output
            }
            
            logger.info(f"Calling: POST {url}")
            
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            
            output = response.json()
            logger.info(f"✓ Decision Layer Response: {response.status_code}")
            decision = output.get("decision", {})
            logger.info(f"  Action: {decision.get('action', 'N/A')}")
            logger.info(f"  Final Pods: {decision.get('final_pods', 'N/A')}")
            
            return output
        
        except Exception as e:
            logger.error(f"✗ Decision Layer call failed: {e}")
            return None
    
    def _create_engine1_output(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Create simulated Engine 1 output based on scenario."""
        return {
            "system_id": self.system_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prediction_window_seconds": 30,
            "prediction": {
                "predicted_cpu": scenario["predicted_cpu"],
                "predicted_load_level": scenario["predicted_load_level"],
                "recommended_pods": scenario["recommended_pods"],
                "confidence": 0.85 + (0.15 * (1.0 - abs(scenario["predicted_cpu"] - 50) / 50))
            },
            "data_source": "demo"
        }
    
    def save_results(self, result: Dict[str, Any]) -> None:
        """Save scenario results to files."""
        try:
            # Save latest decision
            with open(DEMO_LATEST_FILE, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"✓ Saved latest result to {DEMO_LATEST_FILE}")
            
            # Append to history CSV
            self._append_history_csv(result)
            
            # Store in memory
            self.history.append(result)
        
        except Exception as e:
            logger.error(f"✗ Failed to save results: {e}")
    
    def _append_history_csv(self, result: Dict[str, Any]) -> None:
        """Append scenario result to history CSV."""
        try:
            decision = result["steps"]["decision"].get("decision", {})
            engine2 = result["steps"]["engine2"]
            engine3 = result["steps"]["engine3"]
            
            row = {
                "timestamp": result["timestamp"],
                "scenario_name": result["scenario_name"],
                "predicted_cpu": result["steps"]["engine1"]["prediction"]["predicted_cpu"],
                "load_level": result["steps"]["engine1"]["prediction"]["predicted_load_level"],
                "current_pods": result.get("steps", {}).get("engine1", {}).get("current_pods", 0),
                "recommended_pods": result["steps"]["engine1"]["prediction"]["recommended_pods"],
                "final_pods": decision.get("final_pods", 0),
                "final_action": decision.get("action", "N/A"),
                "sla_preserved": decision.get("sla_preserved", False),
                "jobs_delayed": engine3.get("delayable_jobs", 0),
                "carbon_saving_gco2": engine2.get("carbon_saving_gco2", 0.0),
                "carbon_saving_percent": engine2.get("carbon_saving_percent", 0.0)
            }
            
            # Write CSV header if file doesn't exist
            file_exists = DEMO_HISTORY_FILE.exists() and DEMO_HISTORY_FILE.stat().st_size > 0
            
            with open(DEMO_HISTORY_FILE, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
            
            logger.info(f"✓ Appended to history: {DEMO_HISTORY_FILE}")
        
        except Exception as e:
            logger.error(f"✗ Failed to write history CSV: {e}")
    
    def run_continuous(self, interval: int = 5, duration: int = None) -> None:
        """
        Run scenarios continuously.
        
        Args:
            interval: Seconds between scenario runs
            duration: Total duration in seconds (None = infinite)
        """
        start_time = time.time()
        run_count = 0
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting continuous scenario runs")
        logger.info(f"Interval: {interval}s")
        logger.info(f"Duration: {duration if duration else 'infinite'}")
        logger.info(f"{'='*80}")
        
        try:
            while True:
                # Check duration
                if duration and (time.time() - start_time) >= duration:
                    logger.info(f"\nDuration limit reached ({duration}s). Stopping.")
                    break
                
                # Run scenario
                scenario = DEMO_SCENARIOS[self.scenario_index % len(DEMO_SCENARIOS)]
                result = self.run_scenario(scenario)
                
                if result:
                    self.save_results(result)
                    run_count += 1
                
                # Move to next scenario
                self.scenario_index += 1
                
                # Wait for next run
                if duration and (time.time() - start_time) < duration:
                    logger.info(f"\nWaiting {interval}s before next scenario...")
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("\n\nInterrupted by user")
        
        finally:
            logger.info(f"\n{'='*80}")
            logger.info(f"Demo runner completed")
            logger.info(f"Scenarios run: {run_count}")
            logger.info(f"History file: {DEMO_HISTORY_FILE}")
            logger.info(f"Latest result: {DEMO_LATEST_FILE}")
            logger.info(f"{'='*80}\n")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Green DevOps demo scenarios through the API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run scenarios continuously every 5 seconds for 5 minutes
  python scripts/run_demo_scenarios.py --duration 300 --interval 5
  
  # Run with custom API URL
  python scripts/run_demo_scenarios.py --api-url http://api.example.com:5000
  
  # Run indefinitely
  python scripts/run_demo_scenarios.py
        """
    )
    
    parser.add_argument(
        "--api-url",
        default="http://localhost:5000",
        help="Base URL of Green DevOps API (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--system-id",
        default="demo-system",
        help="System identifier for demo scenarios (default: demo-system)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Seconds between scenario runs (default: 5)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Total duration in seconds (default: infinite)"
    )
    
    args = parser.parse_args()
    
    # Create and run runner
    runner = DemoScenarioRunner(
        api_url=args.api_url,
        system_id=args.system_id
    )
    
    runner.run_continuous(
        interval=args.interval,
        duration=args.duration
    )


if __name__ == "__main__":
    main()
