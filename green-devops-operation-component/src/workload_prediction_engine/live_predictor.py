"""
Live predictor for Engine 1 runtime operation.

Orchestrates the complete flow:
1. Collect metrics from Prometheus
2. Store metrics in runtime store
3. Decide mode (cold-start or runtime)
4. Prepare model input (with bootstrap if needed)
5. Run prediction
6. Return structured output
"""

import logging
import numpy as np
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path

try:
    from .metrics_collector import PrometheusMetricsCollector, MetricsCollectorFactory
    from .runtime_store import RuntimeStore
    from .mode_manager import ModeManager, ModeHistory
    from .bootstrap import BootstrapFactory
    from .predictor import WorkloadPredictor
    from .output_contract import Engine1Output, create_engine1_output
    from .config import (
        MODEL_PATH,
        SCALER_PATH,
        MODEL_VERSION,
        SEQUENCE_LENGTH,
        PREDICTION_WINDOW_SECONDS
    )
except ImportError:
    from metrics_collector import PrometheusMetricsCollector, MetricsCollectorFactory
    from runtime_store import RuntimeStore
    from mode_manager import ModeManager, ModeHistory
    from bootstrap import BootstrapFactory
    from predictor import WorkloadPredictor
    from output_contract import Engine1Output, create_engine1_output
    from config import (
        MODEL_PATH,
        SCALER_PATH,
        MODEL_VERSION,
        SEQUENCE_LENGTH,
        PREDICTION_WINDOW_SECONDS
    )

logger = logging.getLogger(__name__)


class LivePredictor:
    """
    Orchestrate Engine 1 prediction in a live running system.
    
    Handles:
    - Collecting live metrics
    - Maintaining runtime history
    - Mode management (cold-start ↔ runtime)
    - Bootstrap for partial history
    - Model prediction
    - Output generation
    """
    
    def __init__(
        self,
        system_id: str,
        prometheus_url: str = "http://localhost:9090",
        runtime_store_dir: str = "data/runtime_metrics",
        bootstrap_strategy: str = 'forward_fill',
        use_mock: bool = False
    ):
        """
        Initialize live predictor.
        
        Args:
            system_id: Kubernetes pod/system identifier
            prometheus_url: Base URL of Prometheus
            runtime_store_dir: Directory for storing runtime metrics
            bootstrap_strategy: How to handle partial data ('forward_fill', 'linear', 'statistical')
            use_mock: If True, use mock metrics (development/testing)
        """
        self.system_id = system_id
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        if use_mock:
            self.collector = MetricsCollectorFactory.create_mock()
        else:
            self.collector = PrometheusMetricsCollector(
                prometheus_url=prometheus_url,
                system_id=system_id
            )
        
        self.store = RuntimeStore(store_dir=runtime_store_dir)
        self.mode_manager = ModeManager()
        self.mode_history = ModeHistory()
        self.bootstrap = BootstrapFactory.create(bootstrap_strategy)
        
        # Load predictor. Mock mode only affects metrics collection; inference stays real.
        self.use_mock = use_mock
        self.predictor = WorkloadPredictor(MODEL_PATH, SCALER_PATH)
        self.predictor.load_model()
        self.predictor.load_scaler()

        if use_mock:
            self.logger.info("Mock metrics mode enabled - real model inference remains active")
        
        # Track current mode
        self.current_mode = None
        
        self.logger.info(
            f"LivePredictor initialized: {system_id} "
            f"(bootstrap: {bootstrap_strategy}, mock: {use_mock})"
        )
    
    def predict_next_window(self) -> Engine1Output:
        """
        Execute one prediction cycle:
        1. Collect latest metrics
        2. Store metrics
        3. Decide mode
        4. Prepare input sequence
        5. Run prediction
        6. Log prediction to file
        7. Return output
        
        Returns:
            Engine1Output with prediction for next 30 seconds
        """
        # Step 1: Collect latest metrics
        self.logger.debug("Collecting metrics...")
        try:
            new_metrics = self.collector.query_latest_metrics(lookback_minutes=1)
            
            if not new_metrics:
                self.logger.warning("No metrics collected, using empty list")
                new_metrics = []
        except Exception as e:
            self.logger.error(f"Metric collection failed: {e}, using fallback")
            new_metrics = []
        
        # Step 2: Store metrics
        if new_metrics:
            try:
                self.store.append_metrics(self.system_id, new_metrics)
            except Exception as e:
                self.logger.error(f"Failed to store metrics: {e}")
        
        # Step 3: Decide mode
        record_count = self.store.get_record_count(self.system_id)
        new_mode = self.mode_manager.get_mode(record_count)
        
        # Log mode transition with detailed information
        if self.current_mode != new_mode:
            transition_msg = (
                f"Mode switched: {self.current_mode or 'init'} -> {new_mode} at "
                f"{datetime.utcnow().isoformat()}Z "
                f"({record_count} collected records, "
                f"{record_count * 30 // 60} minutes data)"
            )
            self.mode_history.record_transition(
                from_mode=self.current_mode or 'init',
                to_mode=new_mode,
                record_count=record_count
            )
            self.logger.warning(transition_msg)
            self.logger.info(f"[OK] {transition_msg}")
        
        self.current_mode = new_mode
        
        # Step 4: Prepare input sequence
        try:
            sequence = self._prepare_sequence(new_mode, record_count)
        except Exception as e:
            self.logger.error(f"Failed to prepare sequence: {e}")
            # Return a fallback output
            return Engine1Output(
                system_id=self.system_id,
                timestamp=int(datetime.utcnow().timestamp()),
                predicted_cpu=50.0,
                predicted_load_level="NORMAL",
                recommended_pods=2,
                confidence=0.5,
                model_version=MODEL_VERSION,
                data_source="error_fallback"
            )
        
        # Step 5: Run prediction
        try:
            output = self.predictor.predict(
                sequence,
                system_id=self.system_id,
                data_source=new_mode
            )
            
            # Update output with metadata
            output.model_version = MODEL_VERSION
            output.data_source = new_mode
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            output = Engine1Output(
                system_id=self.system_id,
                timestamp=int(datetime.utcnow().timestamp()),
                predicted_cpu=50.0,
                predicted_load_level="NORMAL",
                recommended_pods=2,
                confidence=0.5,
                model_version=MODEL_VERSION,
                data_source="error_fallback"
            )
        
        # Step 6: Log prediction to CSV
        try:
            self.store.append_prediction(
                system_id=self.system_id,
                timestamp=output.timestamp,
                predicted_cpu=output.predicted_cpu,
                predicted_load_level=output.predicted_load_level,
                recommended_pods=output.recommended_pods,
                data_source=new_mode
            )
        except Exception as e:
            self.logger.warning(f"Failed to log prediction to file: {e}")
        
        self.logger.info(
            f"Prediction: CPU={output.predicted_cpu:.2f}% ({output.predicted_load_level}), "
            f"Pods={output.recommended_pods}, Mode={new_mode}, Records={record_count}"
        )
        
        # Step 7: Return output
        return output
    
    def _prepare_sequence(self, mode: str, record_count: int) -> np.ndarray:
        """
        Prepare model input sequence based on current mode.
        
        Args:
            mode: Current mode ('cold_start' or 'runtime')
            record_count: Number of records in runtime store
        
        Returns:
            np.ndarray of shape (12, 2) normalized and ready for model
        """
        if mode == 'runtime':
            # Use latest 12 runtime points
            runtime_metrics = self.store.read_latest(self.system_id, count=12)
            
            if len(runtime_metrics) < 12:
                # Shouldn't happen, but fallback to bootstrap
                self.logger.warning(
                    f"Runtime mode but only {len(runtime_metrics)} records, "
                    f"using bootstrap"
                )
                return self.bootstrap.bootstrap_sequence(runtime_metrics, 12)
            
            # Convert to normalized sequence
            sequence = np.array([
                [m['cpu'], m['memory']] for m in runtime_metrics
            ], dtype=np.float32)
            
            # Normalize
            sequence[:, 0] = sequence[:, 0] / 100.0  # CPU to [0, 1]
            sequence[:, 1] = sequence[:, 1] / 1000.0  # Memory to [0, 1]
            
            return sequence
        
        else:  # cold_start
            # Use available runtime data + bootstrap
            runtime_metrics = self.store.read_latest(self.system_id, count=12)
            return self.bootstrap.bootstrap_sequence(runtime_metrics, 12)
    
    def get_mode_info(self) -> dict:
        """Get current mode information and statistics."""
        record_count = self.store.get_record_count(self.system_id)
        
        info = {
            'system_id': self.system_id,
            'current_mode': self.current_mode or 'not_started',
            'record_count': record_count,
            'mode_details': self.mode_manager.get_mode_info(
                record_count,
                self.current_mode or 'cold_start'
            ),
            'store_stats': self.store.get_stats(self.system_id),
            'retraining_ready': self.mode_manager.should_retrain(record_count),
            'mode_transitions': len(self.mode_history.get_transitions())
        }
        
        return info
    
    def get_retraining_data(self, max_records: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get collected runtime data for retraining.
        
        Creates sequences of shape (N, 12, 2) and targets.
        
        Args:
            max_records: Maximum number of records to use (None = all)
        
        Returns:
            Tuple of (X, y) ready for retraining
        """
        all_metrics = self.store.read_all(self.system_id)
        
        if max_records:
            all_metrics = all_metrics[-max_records:]
        
        if len(all_metrics) < SEQUENCE_LENGTH + 1:
            self.logger.warning(
                "Not enough data for retraining: "
                f"{len(all_metrics)} records, need {SEQUENCE_LENGTH + 1}"
            )
            return None, None
        
        X, y = [], []
        
        # Create sliding windows of 12 + 1 (prediction target)
        for i in range(len(all_metrics) - SEQUENCE_LENGTH):
            window = all_metrics[i:i + SEQUENCE_LENGTH + 1]
            
            # Features: first 12 points
            features = [[m['cpu']/100, m['memory']/1000] for m in window[:-1]]
            # Target: CPU at position 12
            target = window[-1]['cpu'] / 100.0
            
            X.append(features)
            y.append(target)
        
        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.float32)
        
        self.logger.info(
            f"Prepared retraining data: X={X.shape}, y={y.shape}"
        )
        
        return X, y
    
    def clear_runtime_history(self) -> bool:
        """
        Clear all collected runtime data.
        
        Warning: This resets Engine 1 to cold-start mode.
        """
        if self.store.clear_store(self.system_id):
            self.current_mode = None
            self.logger.warning("Runtime history cleared")
            return True
        return False


class LivePredictorFactory:
    """Factory for creating live predictors."""
    
    @staticmethod
    def create_from_env(system_id: str) -> LivePredictor:
        """
        Create predictor from environment variables.
        
        Environment variables:
        - PROMETHEUS_URL: Prometheus endpoint
        - RUNTIME_STORE_DIR: Where to store metrics
        - BOOTSTRAP_STRATEGY: Bootstrap strategy
        - USE_MOCK_METRICS: Force mock mode
        """
        import os
        
        prometheus_url = os.getenv(
            'PROMETHEUS_URL',
            'http://localhost:9090'
        )
        
        runtime_store_dir = os.getenv(
            'RUNTIME_STORE_DIR',
            'data/runtime_metrics'
        )
        
        bootstrap_strategy = os.getenv(
            'BOOTSTRAP_STRATEGY',
            'forward_fill'
        )
        
        use_mock = os.getenv('USE_MOCK_METRICS', '').lower() == 'true'
        
        return LivePredictor(
            system_id=system_id,
            prometheus_url=prometheus_url,
            runtime_store_dir=runtime_store_dir,
            bootstrap_strategy=bootstrap_strategy,
            use_mock=use_mock
        )
