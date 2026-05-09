"""
Complete integration example: End-to-end carbon-aware scaling workflow.

This module demonstrates how to use the API endpoints together to create
a carbon-aware orchestration system that makes optimal scaling decisions.
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MetricSnapshots:
    """Current system metrics."""
    cpu_percent: float
    memory_mb: float
    current_pods: int
    timestamp: str


class CarbonAwareOrchestrator:
    """
    Orchestrates Engine 1, Engine 2, and Engine 3 for carbon-aware scaling.
    
    Workflow:
    1. Collect metrics
    2. Get Engine 1 prediction (workload forecast)
    3. Get Engine 3 analysis (optional job deferral)
    4. Run Engine 2 carbon evaluation
    5. Make scaling decision
    6. Apply recommendation
    """
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize orchestrator.
        
        Args:
            api_base_url: Base URL of the API server
        """
        self.api_url = api_base_url
        self.session = requests.Session()
        self.logger_enabled = True
    
    def log(self, message: str, level: str = "INFO") -> None:
        """Log message."""
        if self.logger_enabled:
            timestamp = datetime.utcnow().isoformat() + "Z"
            print(f"[{timestamp}] {level:8s} {message}")
    
    # ========================================================================
    # STEP 1: METRICS COLLECTION
    # ========================================================================
    
    def collect_metrics(self, system_id: str) -> MetricSnapshots:
        """
        Collect current system metrics.
        
        In production, this would query:
        - Prometheus for CPU/memory metrics
        - Kubernetes API for pod count
        
        Here we simulate with random values.
        """
        # In production, replace with real metric collection
        import random
        
        metrics = MetricSnapshots(
            cpu_percent=random.uniform(20, 90),
            memory_mb=random.uniform(500, 2000),
            current_pods=random.randint(2, 5),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        self.log(f"Metrics collected for {system_id}: "
                f"CPU={metrics.cpu_percent:.1f}%, "
                f"Memory={metrics.memory_mb:.0f}MB, "
                f"Pods={metrics.current_pods}")
        
        return metrics
    
    # ========================================================================
    # STEP 2: ENGINE 1 - WORKLOAD PREDICTION
    # ========================================================================
    
    def get_engine1_prediction(self, system_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workload prediction from Engine 1.
        
        Args:
            system_id: System identifier
        
        Returns:
            Engine 1 output dict or None if error
        """
        try:
            response = self.session.get(
                f"{self.api_url}/predict",
                params={"system_id": system_id},
                timeout=5
            )
            
            if response.status_code != 200:
                self.log(
                    f"Engine 1 prediction failed: {response.status_code}",
                    level="ERROR"
                )
                return None
            
            result = response.json()
            prediction = result["prediction"]
            
            self.log(
                f"Engine 1 prediction: "
                f"CPU={prediction['predicted_cpu_percent']:.1f}%, "
                f"Load={prediction['predicted_load_level']}, "
                f"Pods={prediction['recommended_pods']}"
            )
            
            return prediction
        
        except Exception as e:
            self.log(f"Engine 1 error: {e}", level="ERROR")
            return None
    
    # ========================================================================
    # STEP 3: ENGINE 3 - JOB PRIORITIZATION (OPTIONAL)
    # ========================================================================
    
    def get_engine3_analysis(self, system_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job deferral analysis from Engine 3 (optional).
        
        Args:
            system_id: System identifier
        
        Returns:
            Engine 3 output dict or None if error/unavailable
        """
        # Placeholder for Engine 3 integration
        # In production, query Engine 3's /job/analyze endpoint
        
        self.log("Engine 3 analysis: Not yet implemented (optional)")
        return None
    
    # ========================================================================
    # STEP 4: ENGINE 2 - CARBON EVALUATION
    # ========================================================================
    
    def evaluate_carbon(
        self,
        system_id: str,
        predicted_cpu: float,
        predicted_load_level: str,
        recommended_pods: int,
        current_pods: int,
        engine3_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate carbon impact and get optimization recommendation.
        
        Args:
            system_id: System identifier
            predicted_cpu: Predicted CPU from Engine 1
            predicted_load_level: Predicted load level from Engine 1
            recommended_pods: Recommended pods from Engine 1
            current_pods: Current pod count
            engine3_data: Optional data from Engine 3
        
        Returns:
            Carbon evaluation result or None if error
        """
        try:
            payload = {
                "system_id": system_id,
                "predicted_cpu": predicted_cpu,
                "predicted_load_level": predicted_load_level,
                "recommended_pods": recommended_pods,
                "current_pods": current_pods,
                "prediction_window_seconds": 30
            }
            
            # Add Engine 3 data if available
            if engine3_data:
                if "delayable_jobs" in engine3_data:
                    payload["delayable_jobs"] = engine3_data["delayable_jobs"]
                if "workload_reduction_percent" in engine3_data:
                    payload["workload_reduction_percent"] = \
                        engine3_data["workload_reduction_percent"]
            
            response = self.session.post(
                f"{self.api_url}/carbon/evaluate",
                json=payload,
                timeout=5
            )
            
            if response.status_code != 200:
                self.log(
                    f"Carbon evaluation failed: {response.status_code}",
                    level="ERROR"
                )
                return None
            
            result = response.json()
            decision = result["decision"]
            
            self.log(
                f"Carbon evaluation: "
                f"Action={decision['recommended_action']}, "
                f"Saving={decision['carbon_saving_percent']:.1f}%, "
                f"Time={result.get('evaluation_ms', 'N/A')}ms"
            )
            
            return result
        
        except Exception as e:
            self.log(f"Carbon evaluation error: {e}", level="ERROR")
            return None
    
    # ========================================================================
    # STEP 5: DECISION MAKING
    # ========================================================================
    
    def make_scaling_decision(self, carbon_result: Dict[str, Any]) -> str:
        """
        Extract and validate the scaling decision.
        
        Args:
            carbon_result: Carbon evaluation result
        
        Returns:
            Action to take: scale_up, scale_down, delay_jobs, hybrid, no_action
        """
        action = carbon_result["decision"]["recommended_action"]
        saving = carbon_result["decision"]["carbon_saving_percent"]
        
        self.log(f"Decision: {action} (carbon saving: {saving:.1f}%)")
        
        return action
    
    # ========================================================================
    # STEP 6: EXECUTION
    # ========================================================================
    
    def apply_decision(
        self,
        system_id: str,
        action: str,
        recommended_pods: int,
        current_pods: int
    ) -> bool:
        """
        Apply the recommended decision (scaling or job deferral).
        
        In production, this would:
        - Call Kubernetes API to scale pods
        - Call job scheduler to defer jobs
        
        Args:
            system_id: System identifier
            action: Action to take
            recommended_pods: Target pod count
            current_pods: Current pod count
        
        Returns:
            True if successful
        """
        try:
            if action == "scale_up":
                self.log(
                    f"Applying {action}: {current_pods} → {recommended_pods} pods "
                    f"for {system_id}"
                )
                # In production: kubectl scale deployment system_id --replicas=recommended_pods
                
            elif action == "scale_down":
                self.log(
                    f"Applying {action}: {current_pods} → {recommended_pods} pods "
                    f"for {system_id}"
                )
                # In production: kubectl scale deployment system_id --replicas=recommended_pods
                
            elif action == "delay_jobs":
                self.log(
                    f"Applying {action}: deferring non-critical jobs for {system_id}"
                )
                # In production: call job scheduler API
                
            elif action == "hybrid":
                self.log(
                    f"Applying {action}: scale to {recommended_pods} pods + defer jobs"
                )
                # In production: combine scaling + job deferral
                
            else:  # no_action
                self.log(f"No action needed for {system_id}")
            
            return True
        
        except Exception as e:
            self.log(f"Failed to apply decision: {e}", level="ERROR")
            return False
    
    # ========================================================================
    # COMPLETE WORKFLOW
    # ========================================================================
    
    def optimize_system(self, system_id: str) -> Optional[Dict[str, Any]]:
        """
        Run complete optimization workflow for a system.
        
        Workflow:
        1. Collect metrics
        2. Get Engine 1 prediction
        3. Get Engine 3 analysis (optional)
        4. Run Engine 2 carbon evaluation
        5. Make decision
        6. Apply decision
        
        Args:
            system_id: System identifier
        
        Returns:
            Final decision or None if error
        """
        self.log(f"Starting optimization for {system_id}")
        
        # Step 1: Collect metrics
        metrics = self.collect_metrics(system_id)
        
        # Step 2: Get Engine 1 prediction
        prediction = self.get_engine1_prediction(system_id)
        if not prediction:
            self.log("Skipping optimization: Engine 1 prediction failed", 
                    level="WARN")
            return None
        
        # Step 3: Get Engine 3 analysis (optional)
        engine3_data = self.get_engine3_analysis(system_id)
        
        # Step 4: Run Engine 2 carbon evaluation
        carbon_result = self.evaluate_carbon(
            system_id=system_id,
            predicted_cpu=prediction["predicted_cpu_percent"],
            predicted_load_level=prediction["predicted_load_level"],
            recommended_pods=prediction["recommended_pods"],
            current_pods=metrics.current_pods,
            engine3_data=engine3_data
        )
        
        if not carbon_result:
            self.log("Skipping optimization: Carbon evaluation failed",
                    level="WARN")
            return None
        
        # Step 5: Make decision
        action = self.make_scaling_decision(carbon_result)
        
        # Step 6: Apply decision
        self.apply_decision(
            system_id=system_id,
            action=action,
            recommended_pods=prediction["recommended_pods"],
            current_pods=metrics.current_pods
        )
        
        self.log(f"Optimization complete for {system_id}")
        
        return carbon_result
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def print_scenario_analysis(self, carbon_result: Dict[str, Any]) -> None:
        """Pretty-print scenario analysis."""
        print("\n" + "=" * 80)
        print("CARBON SCENARIO ANALYSIS")
        print("=" * 80)
        
        for scenario in carbon_result["scenarios"]:
            print(f"\n{scenario['name'].upper()}")
            print(f"  Description: {scenario['description']}")
            print(f"  Pods: {scenario.get('pod_count', 'N/A')}")
            print(f"  Energy: {scenario.get('energy_kwh', 0):.6f} kWh")
            print(f"  Carbon: {scenario.get('carbon_gco2', 0):.2f} g CO2")
        
        print(f"\nDECISION: {carbon_result['decision']['recommended_action'].upper()}")
        print(f"Carbon Saving: {carbon_result['decision']['carbon_saving_percent']:.1f}%")
        print("=" * 80 + "\n")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_single_system_optimization():
    """Example: Optimize a single system."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Single System Optimization")
    print("=" * 80 + "\n")
    
    orchestrator = CarbonAwareOrchestrator()
    
    # Optimize system
    result = orchestrator.optimize_system("api-service")
    
    if result:
        orchestrator.print_scenario_analysis(result)


def example_multi_system_optimization():
    """Example: Optimize multiple systems."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Multi-System Optimization")
    print("=" * 80 + "\n")
    
    orchestrator = CarbonAwareOrchestrator()
    systems = ["api-service", "worker-service", "batch-processor"]
    
    results = {}
    for system_id in systems:
        result = orchestrator.optimize_system(system_id)
        if result:
            results[system_id] = result
            time.sleep(0.5)  # Small delay between requests
    
    # Print summary
    if results:
        print("\n" + "=" * 80)
        print("OPTIMIZATION SUMMARY")
        print("=" * 80)
        
        total_carbon_saving = 0
        for system_id, result in results.items():
            saving = result["decision"]["carbon_saving_percent"]
            action = result["decision"]["recommended_action"]
            total_carbon_saving += saving
            print(f"{system_id:20s} → {action:15s} "
                  f"({saving:+6.1f}% carbon)")
        
        avg_saving = total_carbon_saving / len(results)
        print(f"\nAverage carbon saving: {avg_saving:.1f}%")
        print("=" * 80 + "\n")


def example_with_job_deferral():
    """Example: Optimization with job deferral (Engine 3)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Optimization with Job Deferral")
    print("=" * 80 + "\n")
    
    orchestrator = CarbonAwareOrchestrator()
    
    # Manually run Engine 2 with job deferral data
    carbon_result = orchestrator.evaluate_carbon(
        system_id="batch-processor",
        predicted_cpu=65.0,
        predicted_load_level="NORMAL",
        recommended_pods=4,
        current_pods=4,
        engine3_data={
            "delayable_jobs": 25,
            "workload_reduction_percent": 30.0
        }
    )
    
    if carbon_result:
        orchestrator.print_scenario_analysis(carbon_result)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + "GREEN DEVOPS - CARBON-AWARE SCALING ORCHESTRATOR".center(78) + "║")
    print("║" + "Complete Integration Example".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Run examples
    try:
        example_single_system_optimization()
        example_multi_system_optimization()
        example_with_job_deferral()
    except requests.exceptions.ConnectionError:
        print("\nERROR: Cannot connect to API server at http://localhost:8000")
        print("Make sure the API server is running:")
        print("  python scripts/run_live_api.py --system-id test-pod --port 8000")
