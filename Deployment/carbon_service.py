#!/usr/bin/env python3
"""
carbon_service.py
=================
Watches for deployment completion and automatically generates carbon reports
by combining deployment_tracker.json, profiler_results.json, and strategy info.

Run as a systemd service on your Ubuntu machine:

    sudo systemctl enable carbon-service
    sudo systemctl start carbon-service
"""

import json
import time
import logging
import signal
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict
import threading

# Import your existing carbon modules
from carbon_api import get_carbon_intensity, DEFAULT_ZONE
from carbon_calculator import calculate_total_energy, generate_carbon_report, print_carbon_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("carbon_service")

# ============================================================================
# Configuration
# ============================================================================

WATCH_DIR = Path("/home/hiran")  # Where deployment_last.json and profiler_results.json live
DEPLOYMENT_FILE = WATCH_DIR / "deployment_last.json"
PROFILER_FILE = WATCH_DIR / "profiler_results.json"
CARBON_REPORT_FILE = WATCH_DIR / "carbon_report.json"
HISTORY_DIR = WATCH_DIR / "carbon_reports_history"

# Carbon settings
CARBON_ZONE = "IN-SO"  # Sri Lanka / South Asia

# Strategy-specific carbon profiles
STRATEGY_CARBON_FACTORS = {
    "rolling": {
        "profile": "low_gradual",
        "infra_multiplier": 1.1,  # Overlap during rolling update
        "description": "Gradual replacement with brief overlap"
    },
    "recreate": {
        "profile": "low_burst",
        "infra_multiplier": 1.0,
        "description": "Full stop and restart with downtime"
    },
    "canary": {
        "profile": "medium_transient", 
        "infra_multiplier": 1.2,  # Running both canary and stable
        "description": "Canary deployment with extended dual-running"
    }
}

# ============================================================================
# Carbon Calculator Service
# ============================================================================

class CarbonService:
    def __init__(self):
        self.last_processed = None
        self.running = True
        self.signal_handlers_set = False
        self.strategy_snapshots = {}  # Store carbon snapshots by build number
        
    def get_latest_profiler_data(self) -> Optional[Dict]:
        """Read the latest profiler results."""
        if not PROFILER_FILE.exists():
            logger.debug(f"Waiting for {PROFILER_FILE}...")
            return None
            
        try:
            with open(PROFILER_FILE, 'r') as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read {PROFILER_FILE}: {e}")
            return None
    
    def get_deployment_metadata(self) -> Optional[Dict]:
        """Read deployment metadata from tracker."""
        if not DEPLOYMENT_FILE.exists():
            logger.debug(f"Waiting for {DEPLOYMENT_FILE}...")
            return None
            
        try:
            with open(DEPLOYMENT_FILE, 'r') as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read {DEPLOYMENT_FILE}: {e}")
            return None
    
    def load_strategy_snapshots(self, build_number: str):
        """Load carbon snapshots for a specific build."""
        snapshots = {}
        for phase in ["before", "during", "after", "canary_live", "promoted"]:
            snapshot_file = WATCH_DIR / f"carbon_snapshot_{build_number}_{phase}.json"
            if snapshot_file.exists():
                try:
                    with open(snapshot_file, 'r') as f:
                        snapshots[phase] = json.load(f)
                except Exception as e:
                    logger.debug(f"Could not load snapshot {snapshot_file}: {e}")
        return snapshots
    
    def calculate_strategy_carbon_factors(self, deploy_data: Dict, snapshots: Dict) -> Dict:
        """Calculate carbon-related factors based on deployment strategy."""
        strategy = deploy_data.get("strategy", "rolling")
        carbon_profile = deploy_data.get("carbon_profile", "unknown")
        
        # Get base strategy factors
        factors = STRATEGY_CARBON_FACTORS.get(strategy, {
            "profile": "unknown",
            "infra_multiplier": 1.0,
            "description": "Unknown strategy"
        }).copy()
        
        # Add deploy data
        factors["actual_profile"] = carbon_profile
        factors["strategy"] = strategy
        
        # Calculate infrastructure impact from snapshots
        infra_phases = {}
        for phase, snapshot in snapshots.items():
            infra_phases[phase] = {
                "infra_multiplier": snapshot.get("infra_multiplier", 1.0),
                "timestamp": snapshot.get("timestamp"),
            }
            if "downtime_seconds" in snapshot:
                infra_phases[phase]["downtime_seconds"] = snapshot["downtime_seconds"]
            if "canary_weight" in snapshot:
                infra_phases[phase]["canary_weight"] = snapshot["canary_weight"]
        
        factors["infra_phases"] = infra_phases
        
        # Calculate average infra multiplier
        multipliers = [p.get("infra_multiplier", 1.0) for p in infra_phases.values()]
        factors["avg_infra_multiplier"] = sum(multipliers) / len(multipliers) if multipliers else 1.0
        
        return factors
    
    def should_process(self, profiler_data: Dict) -> bool:
        """Check if this deployment should be processed."""
        # Check if already processed
        end_time = profiler_data.get("end_time")
        if not end_time:
            return False
            
        if self.last_processed == end_time:
            return False
            
        # Check if deployment completed (has samples)
        if profiler_data.get("samples_collected", 0) == 0:
            return False
            
        return True
    
    def save_carbon_report(self, report: Dict, deployment_name: str = None):
        """Save carbon report to disk."""
        # Create history directory
        HISTORY_DIR.mkdir(exist_ok=True)
        
        # Add timestamp to report
        report["computed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Save latest report
        with open(CARBON_REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Saved carbon report to {CARBON_REPORT_FILE}")
        
        # Archive with build number and strategy if available
        if deployment_name:
            archive_name = HISTORY_DIR / f"carbon_{deployment_name}.json"
            with open(archive_name, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Archived report to {archive_name}")
    
    def process_deployment(self, profiler_data: Dict, deploy_data: Dict = None):
        """Process a completed deployment and generate carbon report."""
        logger.info("=" * 60)
        logger.info("Processing new deployment for carbon calculation...")
        
        # Extract strategy info
        job_name = "unknown"
        build_number = "?"
        strategy = "unknown"
        
        if deploy_data:
            job_name = deploy_data.get("job_name", "unknown")
            build_number = deploy_data.get("build_number", "?")
            strategy = deploy_data.get("strategy", "unknown")
            carbon_profile = deploy_data.get("carbon_profile", "unknown")
            
            # Load strategy snapshots
            snapshots = self.load_strategy_snapshots(str(build_number))
            strategy_factors = self.calculate_strategy_carbon_factors(deploy_data, snapshots)
            
            logger.info(f"Strategy: {strategy} | Carbon profile: {carbon_profile}")
            logger.info(f"Strategy factors: {json.dumps(strategy_factors, indent=2)}")
        
        # Prepare metrics dict as expected by carbon_calculator
        metrics = {
            "start_time": profiler_data.get("start_time"),
            "end_time": profiler_data.get("end_time"),
            "duration_minutes": profiler_data.get("duration_minutes", 0),
            "cpu_readings": profiler_data.get("cpu_readings", []),
            "memory_readings": profiler_data.get("memory_readings", []),
            "avg_cpu": profiler_data.get("avg_cpu", 0),
            "avg_memory": profiler_data.get("avg_memory", 0),
            "peak_cpu": profiler_data.get("peak_cpu", 0),
            "peak_memory": profiler_data.get("peak_memory", 0),
            "network_gb": profiler_data.get("network_gb", 0),
            "job_name": job_name,
            "build_number": build_number,
            "strategy": strategy,
        }
        
        # Add strategy carbon factors if available
        if deploy_data:
            metrics["strategy_carbon_factors"] = strategy_factors
        
        # Generate timestamp for carbon intensity (use deployment start time)
        start_time = None
        if profiler_data.get("start_time"):
            try:
                from datetime import datetime
                start_time = datetime.fromisoformat(profiler_data["start_time"].replace(" ", "T"))
            except Exception as e:
                logger.warning(f"Failed to parse start_time: {e}")
        
        # Generate full carbon report
        try:
            report = generate_carbon_report(
                deployment_metrics=metrics,
                zone=CARBON_ZONE,
                timestamp=start_time,
                baseline_metrics=None  # You can load previous report here for comparison
            )
            
            # Add deployment identifier and strategy info
            report["deployment"]["job_name"] = job_name
            report["deployment"]["build_number"] = build_number
            report["deployment"]["strategy"] = strategy
            
            # Add strategy carbon factors to report
            if deploy_data:
                report["strategy_carbon"] = strategy_factors
            
            # Save report
            deployment_name = f"{job_name}-{build_number}-{strategy}"
            self.save_carbon_report(report, deployment_name)
            
            # Print pretty report to logs
            logger.info("\n" + "=" * 60)
            logger.info("🌿 CARBON REPORT GENERATED")
            logger.info("=" * 60)
            logger.info(f"  Job        : {job_name} #{build_number}")
            logger.info(f"  Strategy   : {strategy}")
            logger.info(f"  Duration   : {metrics['duration_minutes']:.1f} min")
            logger.info(f"  Total CO2  : {report['emissions']['total_g_co2']:.2f} g  ({report['emissions']['total_kg_co2']:.4f} kg)")
            logger.info(f"  Intensity  : {report['carbon_intensity']['intensity_gco2_kwh']} gCO2/kWh ({report['carbon_intensity']['source']})")
            logger.info(f"  Energy     : {report['energy']['total_energy_kwh']:.6f} kWh")
            
            if deploy_data:
                logger.info(f"\n  Strategy Carbon Factors:")
                logger.info(f"    Profile: {strategy_factors.get('profile', 'unknown')}")
                logger.info(f"    Avg Infra Multiplier: {strategy_factors.get('avg_infra_multiplier', 1.0)}x")
            
            logger.info(f"\n  Equivalents:")
            logger.info(f"    🚗  {report['equivalences']['driving']['description']}")
            logger.info(f"    📱  {report['equivalences']['phone']['description']}")
            logger.info(f"    🔍  {report['equivalences']['searches']['description']}")
            logger.info("=" * 60)
            
            logger.info(f"✅ Carbon calculation complete for {job_name}#{build_number} ({strategy})")
            
            # Update last processed marker
            self.last_processed = profiler_data.get("end_time")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate carbon report: {e}", exc_info=True)
            return None
    
    def watch_and_process(self):
        """Main loop: watch for new profiler data and process."""
        logger.info("Carbon Service started")
        logger.info(f"Watching for deployment files in: {WATCH_DIR}")
        logger.info(f"  Deployment file: {DEPLOYMENT_FILE}")
        logger.info(f"  Profiler file:   {PROFILER_FILE}")
        logger.info(f"Zone: {CARBON_ZONE}")
        logger.info(f"Supported strategies: {list(STRATEGY_CARBON_FACTORS.keys())}")
        
        # Also check for existing files on startup
        existing_profiler = self.get_latest_profiler_data()
        if existing_profiler and existing_profiler.get("end_time"):
            deploy_data = self.get_deployment_metadata()
            if self.should_process(existing_profiler):
                logger.info("Found existing deployment data, processing...")
                self.process_deployment(existing_profiler, deploy_data)
        
        while self.running:
            try:
                profiler_data = self.get_latest_profiler_data()
                deploy_data = self.get_deployment_metadata()
                
                if profiler_data and self.should_process(profiler_data):
                    self.process_deployment(profiler_data, deploy_data)
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                logger.info("Received stop signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
                time.sleep(10)
    
    def stop(self, *args):
        """Stop the service gracefully."""
        logger.info("Stopping carbon service...")
        self.running = False
    
    def run(self):
        """Run the service with signal handlers."""
        if not self.signal_handlers_set:
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)
            self.signal_handlers_set = True
        self.watch_and_process()


# ============================================================================
# Strategy Comparison Mode
# ============================================================================

def compare_strategies():
    """Compare carbon footprints across different deployment strategies."""
    logger.info("Comparing deployment strategies...")
    
    if not HISTORY_DIR.exists():
        logger.error("No deployment history found")
        return
    
    strategy_reports = {}
    
    for report_file in HISTORY_DIR.glob("carbon_*.json"):
        try:
            with open(report_file, 'r') as f:
                report = json.load(f)
                
            strategy = report.get("deployment", {}).get("strategy", "unknown")
            emissions = report.get("emissions", {}).get("total_g_co2", 0)
            duration = report.get("deployment", {}).get("duration_minutes", 0)
            
            if strategy not in strategy_reports:
                strategy_reports[strategy] = {
                    "reports": [],
                    "total_emissions": 0,
                    "total_duration": 0,
                    "count": 0
                }
            
            strategy_reports[strategy]["reports"].append({
                "file": report_file.name,
                "emissions": emissions,
                "duration": duration
            })
            strategy_reports[strategy]["total_emissions"] += emissions
            strategy_reports[strategy]["total_duration"] += duration
            strategy_reports[strategy]["count"] += 1
            
        except Exception as e:
            logger.warning(f"Failed to read {report_file}: {e}")
    
    if not strategy_reports:
        logger.info("No reports found for comparison")
        return
    
    print("\n" + "=" * 60)
    print("  DEPLOYMENT STRATEGY CARBON COMPARISON")
    print("=" * 60)
    
    for strategy, data in sorted(strategy_reports.items()):
        avg_emissions = data["total_emissions"] / data["count"]
        avg_duration = data["total_duration"] / data["count"]
        
        print(f"\n  Strategy: {strategy}")
        print(f"    Deployments: {data['count']}")
        print(f"    Avg CO2:     {avg_emissions:.4f} g")
        print(f"    Avg Duration: {avg_duration:.2f} min")
        
        # Get strategy factors
        if strategy in STRATEGY_CARBON_FACTORS:
            factors = STRATEGY_CARBON_FACTORS[strategy]
            print(f"    Profile:     {factors['profile']}")
            print(f"    Infra Mult:  {factors['infra_multiplier']}x")
            print(f"    Type:        {factors['description']}")
    
    # Find most carbon-efficient strategy
    best_strategy = min(strategy_reports.items(), 
                       key=lambda x: x[1]["total_emissions"] / x[1]["count"])
    worst_strategy = max(strategy_reports.items(), 
                        key=lambda x: x[1]["total_emissions"] / x[1]["count"])
    
    print(f"\n  🏆 Most Efficient: {best_strategy[0]}")
    print(f"     ({best_strategy[1]['total_emissions']/best_strategy[1]['count']:.4f} g avg)")
    print(f"  ⚠️  Least Efficient: {worst_strategy[0]}")
    print(f"     ({worst_strategy[1]['total_emissions']/worst_strategy[1]['count']:.4f} g avg)")
    
    if best_strategy[1]["count"] > 0 and worst_strategy[1]["count"] > 0:
        savings_percent = (1 - (best_strategy[1]["total_emissions"]/best_strategy[1]["count"]) / 
                          (worst_strategy[1]["total_emissions"]/worst_strategy[1]["count"])) * 100
        print(f"\n  💡 Using {best_strategy[0]} over {worst_strategy[0]} saves ~{savings_percent:.1f}% carbon")
    
    print("=" * 60)


# ============================================================================
# CLI Mode - Process existing files once
# ============================================================================

def process_existing_once():
    """Process existing JSON files once and exit."""
    logger.info("Processing existing deployment data...")
    
    profiler_file = Path("profiler_results.json")
    deployment_file = Path("deployment_last.json")
    
    if not profiler_file.exists():
        logger.error(f"profiler_results.json not found in current directory")
        return
    
    with open(profiler_file, 'r') as f:
        profiler_data = json.load(f)
    
    deploy_data = None
    if deployment_file.exists():
        with open(deployment_file, 'r') as f:
            deploy_data = json.load(f)
    
    service = CarbonService()
    service.process_deployment(profiler_data, deploy_data)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Carbon Calculation Service")
    parser.add_argument("--once", action="store_true",
                       help="Process existing files once and exit")
    parser.add_argument("--compare", action="store_true",
                       help="Compare carbon footprints across strategies")
    parser.add_argument("--watch-dir", type=str, default="/home/hiran",
                       help="Directory to watch for JSON files")
    args = parser.parse_args()
    
    # Update watch directory
    WATCH_DIR = Path(args.watch_dir)
    DEPLOYMENT_FILE = WATCH_DIR / "deployment_last.json"
    PROFILER_FILE = WATCH_DIR / "profiler_results.json"
    CARBON_REPORT_FILE = WATCH_DIR / "carbon_report.json"
    HISTORY_DIR = WATCH_DIR / "carbon_reports_history"
    
    if args.compare:
        compare_strategies()
    elif args.once:
        process_existing_once()
    else:
        service = CarbonService()
        service.run()
