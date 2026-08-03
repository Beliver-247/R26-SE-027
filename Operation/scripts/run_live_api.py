"""
Run Engine 1 API server with live prediction.

Combines:
- Live predictor: Continuous metrics collection and prediction
- FastAPI: REST endpoints for prediction and health status

Usage:
    python run_live_api.py --system-id my_pod --duration 3600 --port 8000
"""

import argparse
import logging
import logging.config
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from threading import Thread

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "workload_prediction_engine"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import Engine 1 components
try:
    from src.workload_prediction_engine.live_predictor import LivePredictor
    from src.workload_prediction_engine.api import create_api_app
    from src.workload_prediction_engine.config import validate_config, LOG_LEVEL
except ImportError as e:
    print(f"ERROR: Failed to import Engine 1 modules: {e}")
    print("Ensure workload_prediction_engine modules are available in src/")
    sys.exit(1)

# Import Engine 2 (Carbon Emission Engine)
try:
    from carbon_engine import CarbonEmissionEngine
except ImportError as e:
    print(f"ERROR: Failed to import Engine 2 (Carbon Emission Engine) modules: {e}")
    print("Ensure carbon_engine modules are available in src/carbon_engine/")
    CarbonEmissionEngine = None


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure logging with both file and console handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filename': f'logs/engine1_api_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            '': {
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': True
            }
        }
    }
    
    logging.config.dictConfig(log_config)
    return logging.getLogger(__name__)


def run_prediction_loop(
    predictor: LivePredictor,
    api_instance,
    duration_seconds: int = None,
    interval_seconds: int = 30,
    logger: logging.Logger = None
) -> None:
    """
    Run continuous prediction loop in background.
    
    Updates API with latest predictions at regular intervals.
    
    Args:
        predictor: LivePredictor instance
        api_instance: Engine1API instance
        duration_seconds: How long to run (None = infinite)
        interval_seconds: Interval between predictions (default 30s)
        logger: Logger instance
    """
    if not logger:
        logger = logging.getLogger(__name__)
    
    start_time = time.time()
    cycle_count = 0
    
    logger.info(f"Starting prediction loop: interval={interval_seconds}s")
    
    try:
        while True:
            try:
                # Run prediction
                cycle_count += 1
                prediction = predictor.predict_next_window()
                
                # Update API's last prediction
                api_instance.last_prediction = prediction
                
                logger.debug(
                    f"Cycle {cycle_count}: CPU={prediction.predicted_cpu:.1f}%, "
                    f"Load={prediction.predicted_load_level}, "
                    f"Pods={prediction.recommended_pods}"
                )
                
                # Check if we should stop
                if duration_seconds is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= duration_seconds:
                        logger.info(
                            f"Duration reached: {elapsed:.0f}s "
                            f"({cycle_count} predictions)"
                        )
                        break
                
                # Wait before next cycle
                time.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Prediction cycle failed: {e}")
                # Continue on error
                time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        logger.info(f"Stopped by user after {cycle_count} predictions")
    except Exception as e:
        logger.error(f"Prediction loop crashed: {e}")


def main():
    """Main entry point for API server."""
    parser = argparse.ArgumentParser(
        description="Engine 1 API Server with Live Prediction"
    )
    
    parser.add_argument(
        '--system-id',
        required=True,
        help='System/pod identifier'
    )
    
    parser.add_argument(
        '--prometheus-url',
        default='http://localhost:9090',
        help='Prometheus endpoint (default: http://localhost:9090)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='API port (default: 8000)'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='API host (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Prediction interval in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        help='Run duration in seconds (default: infinite)'
    )
    
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock metrics (development mode)'
    )
    
    parser.add_argument(
        '--bootstrap-strategy',
        default='forward_fill',
        choices=['forward_fill', 'linear', 'statistical'],
        help='Bootstrap strategy for cold-start'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    logger.info("=" * 60)
    logger.info("Engine 1 API Server Starting")
    logger.info("=" * 60)
    
    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
    
    # Initialize predictor
    logger.info(f"Initializing predictor for system: {args.system_id}")
    
    try:
        predictor = LivePredictor(
            system_id=args.system_id,
            prometheus_url=args.prometheus_url,
            bootstrap_strategy=args.bootstrap_strategy,
            use_mock=args.mock
        )
        logger.info(f"[OK] Predictor initialized")
    except Exception as e:
        logger.error(f"Failed to initialize predictor: {e}")
        sys.exit(1)
    
    # Initialize Carbon Emission Engine (Engine 2)
    carbon_engine = None
    if CarbonEmissionEngine:
        try:
            carbon_engine = CarbonEmissionEngine()
            logger.info("[OK] Carbon Emission Engine (Engine 2) initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Carbon Engine: {e}")
            logger.warning("Continuing without Engine 2 - carbon evaluation endpoint will not be available")
    else:
        logger.warning("Carbon Emission Engine not available - skipping initialization")
    
    # Create API app
    logger.info("Creating FastAPI application")
    try:
        app = create_api_app(
            live_predictor=predictor,
            carbon_engine=carbon_engine,
            title=f"Engine 1 API - {args.system_id}",
            debug=args.log_level == 'DEBUG'
        )
        logger.info(f"[OK] API created")
    except Exception as e:
        logger.error(f"Failed to create API: {e}")
        sys.exit(1)
    
    # Get the actual API instance so the background loop updates the same
    # last_prediction object read by GET /predict.
    api_instance = getattr(app.state, "engine1_api", None)
    if not api_instance:
        logger.error("Could not find Engine1API instance on app.state.engine1_api")
        sys.exit(1)
    
    # Start prediction loop in background thread
    logger.info("Starting background prediction loop")
    
    pred_thread = Thread(
        target=run_prediction_loop,
        args=(predictor, api_instance, args.duration, args.interval, logger),
        daemon=True
    )
    pred_thread.start()
    logger.info(f"[OK] Prediction loop running (interval={args.interval}s)")
    
    # Start API server
    logger.info(f"Starting API server on {args.host}:{args.port}")
    logger.info("Endpoints available:")
    logger.info(f"  GET  http://{args.host}:{args.port}/health")
    logger.info(f"  GET  http://{args.host}:{args.port}/predict")
    logger.info(f"  POST http://{args.host}:{args.port}/predict/run")
    logger.info(f"  GET  http://{args.host}:{args.port}/status")
    logger.info(f"  GET  http://{args.host}:{args.port}/docs (Swagger UI)")
    
    try:
        import uvicorn
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower()
        )
    except ImportError:
        logger.error("uvicorn not installed. Install with: pip install uvicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
