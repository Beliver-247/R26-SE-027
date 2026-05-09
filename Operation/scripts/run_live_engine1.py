#!/usr/bin/env python3
"""
Live Engine 1 execution script.

Runs Engine 1 on a deployed system, collecting metrics and making predictions.
Demonstrates the complete runtime flow.

Usage:
    python run_live_engine1.py --system-id=my_pod --duration=3600 --mock
"""

import sys
import logging
import argparse
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))

from live_predictor import LivePredictor, LivePredictorFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_live_prediction(
    system_id: str,
    duration_seconds: int = None,
    interval_seconds: int = 30,
    use_mock: bool = False,
    prometheus_url: str = "http://localhost:9090",
    output_file: str = None
):
    """
    Run Engine 1 prediction in live mode.
    
    Args:
        system_id: Kubernetes pod identifier
        duration_seconds: How long to run (None = infinite)
        interval_seconds: Prediction interval (30 sec recommended)
        use_mock: Use mock metrics for testing
        prometheus_url: Prometheus endpoint
        output_file: Save predictions to JSON file
    """
    
    # Initialize predictor
    logger.info(f"Initializing Engine 1 Live Predictor for: {system_id}")
    
    predictor = LivePredictor(
        system_id=system_id,
        prometheus_url=prometheus_url,
        bootstrap_strategy='forward_fill',
        use_mock=use_mock
    )
    
    # Prepare output
    predictions_log = []
    start_time = datetime.utcnow()
    cycle_count = 0
    
    try:
        logger.info(f"Starting prediction loop (duration={duration_seconds}s, interval={interval_seconds}s)")
        logger.info("="*80)
        
        while True:
            # Check duration
            if duration_seconds:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > duration_seconds:
                    logger.info(f"Duration limit reached ({elapsed:.1f}s)")
                    break
            
            cycle_count += 1
            cycle_start = datetime.utcnow()
            
            try:
                # Execute prediction
                logger.info(f"\n[Cycle {cycle_count}] Executing prediction...")
                output = predictor.predict_next_window()
                
                # Log output
                logger.info(
                    f"✓ Prediction result:\n"
                    f"  Timestamp: {output.timestamp}\n"
                    f"  System ID: {output.system_id}\n"
                    f"  Mode: {output.data_source}\n"
                    f"  CPU: {output.predicted_cpu:.2f}% → Load: {output.predicted_load_level}\n"
                    f"  Pods: {output.recommended_pods}\n"
                    f"  Confidence: {output.confidence:.4f}"
                )
                
                # Store prediction
                predictions_log.append(output.to_dict())
                
                # Log mode info
                mode_info = predictor.get_mode_info()
                logger.debug(
                    f"Mode Info: {mode_info['current_mode']}, "
                    f"Records: {mode_info['record_count']}, "
                    f"Retrain Ready: {mode_info['retraining_ready']}"
                )
                
                # Check retraining trigger
                if predictor.mode_manager.should_retrain(mode_info['record_count']):
                    logger.warning(
                        f"⚠ Retraining trigger: {mode_info['record_count']} records "
                        f"(threshold: {predictor.mode_manager.retraining_threshold_records})"
                    )
                
            except Exception as e:
                logger.error(f"Prediction error: {e}", exc_info=True)
            
            # Wait for next interval
            cycle_elapsed = (datetime.utcnow() - cycle_start).total_seconds()
            wait_time = max(0, interval_seconds - cycle_elapsed)
            
            if wait_time > 0:
                logger.debug(f"Waiting {wait_time:.1f}s until next prediction...")
                time.sleep(wait_time)
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    
    finally:
        # Summary
        logger.info("\n" + "="*80)
        logger.info("PREDICTION SESSION SUMMARY")
        logger.info("="*80)
        
        total_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Total cycles: {cycle_count}")
        logger.info(f"Total time: {total_time:.1f}s")
        logger.info(f"Predictions logged: {len(predictions_log)}")
        
        # Final mode info
        final_mode_info = predictor.get_mode_info()
        logger.info(
            f"Final mode: {final_mode_info['current_mode']}\n"
            f"Final records: {final_mode_info['record_count']}\n"
            f"Store stats: {final_mode_info['store_stats']}"
        )
        
        # Save output if requested
        if output_file and predictions_log:
            try:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w') as f:
                    json.dump(predictions_log, f, indent=2, default=str)
                
                logger.info(f"Predictions saved to: {output_path}")
            except Exception as e:
                logger.error(f"Failed to save predictions: {e}")
        
        logger.info("="*80)


def print_mode_info(system_id: str, use_mock: bool = False, prometheus_url: str = "http://localhost:9090"):
    """Print current mode information without running continuous predictions."""
    predictor = LivePredictor(
        system_id=system_id,
        prometheus_url=prometheus_url,
        use_mock=use_mock
    )
    
    info = predictor.get_mode_info()
    
    print("\nEngine 1 Mode Information")
    print("=" * 50)
    print(f"System ID: {info['system_id']}")
    print(f"Current Mode: {info['current_mode']}")
    print(f"Runtime Records: {info['record_count']}")
    print(f"Retrain Ready: {info['retraining_ready']}")
    print(f"\nMode Details:")
    for key, val in info['mode_details'].items():
        print(f"  {key}: {val}")
    print(f"\nStore Statistics:")
    for key, val in info['store_stats'].items():
        if key != 'system_id':
            print(f"  {key}: {val}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='Run Engine 1 Live Predictor on deployed system'
    )
    
    parser.add_argument(
        '--system-id',
        type=str,
        default='my_pod',
        help='Kubernetes pod identifier'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help='Run duration in seconds (None = continuous)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Prediction interval in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock metrics (development mode)'
    )
    
    parser.add_argument(
        '--prometheus-url',
        type=str,
        default='http://localhost:9090',
        help='Prometheus endpoint'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Save predictions to JSON file'
    )
    
    parser.add_argument(
        '--info-only',
        action='store_true',
        help='Print mode info and exit'
    )
    
    args = parser.parse_args()
    
    if args.info_only:
        print_mode_info(
            system_id=args.system_id,
            use_mock=args.mock,
            prometheus_url=args.prometheus_url
        )
    else:
        run_live_prediction(
            system_id=args.system_id,
            duration_seconds=args.duration,
            interval_seconds=args.interval,
            use_mock=args.mock,
            prometheus_url=args.prometheus_url,
            output_file=args.output
        )


if __name__ == '__main__':
    main()
