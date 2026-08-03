"""
Engine 1 integration layer and orchestrator.

Coordinates the complete End-to-End Engine 1 workload prediction pipeline:
- Data preparation from cold-start or runtime sources
- Model inference
- Output generation for downstream engines
- Retraining coordination
"""

import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

import numpy as np

try:
    from .predictor import WorkloadPredictor
    from .runtime_adapter import RuntimeAdapter
    from .output_contract import Engine1Output, Engine1Request, create_engine1_output
    from .retraining import RetrainingManager
    from .config import (
        MODEL_PATH,
        SCALER_PATH,
        DATA_SOURCE_COLD_START,
        DATA_SOURCE_RUNTIME,
        MODEL_VERSION,
        SEQUENCE_LENGTH
    )
except ImportError:
    from predictor import WorkloadPredictor
    from runtime_adapter import RuntimeAdapter
    from output_contract import Engine1Output, Engine1Request, create_engine1_output
    from retraining import RetrainingManager
    from config import (
        MODEL_PATH,
        SCALER_PATH,
        DATA_SOURCE_COLD_START,
        DATA_SOURCE_RUNTIME,
        MODEL_VERSION,
        SEQUENCE_LENGTH
    )

logger = logging.getLogger(__name__)


class Engine1Orchestrator:
    """
    Complete Engine 1 workload prediction orchestrator.
    
    Responsibilities:
    - Initialize prediction components
    - Coordinate runtime and cold-start modes
    - Handle retraining decisions
    - Format output for next engines
    - Support both batch and real-time inference
    """
    
    def __init__(self, model_path: str = MODEL_PATH, scaler_path: str = SCALER_PATH):
        """
        Initialize Engine 1 orchestrator.
        
        Args:
            model_path: Path to trained model
            scaler_path: Path to scaler
        """
        self.predictor = WorkloadPredictor(model_path, scaler_path)
        self.adapter = RuntimeAdapter()
        self.retraining_manager = RetrainingManager(model_path)
        
        # Load model and scaler
        self.predictor.load_model()
        self.predictor.load_scaler()
        
        logger.info("Engine1Orchestrator initialized and ready")
    
    def predict_from_cold_start(
        self,
        system_id: str,
        test_data_path: Optional[str] = None
    ) -> Engine1Output:
        """
        Generate prediction using cold-start mode (pre-trained model, test data).
        
        Used at initial deployment when no runtime history exists.
        
        Args:
            system_id: Target system
            test_data_path: Optional path to test data CSV
        
        Returns:
            Engine1Output ready for next engines
        """
        logger.info(f"Cold-start prediction for system: {system_id}")
        
        # Prepare sequence
        if test_data_path:
            sequence = self.adapter.prepare_sequence_from_csv(
                test_data_path,
                system_id,
                normalize=True,
                scaler_cpu=self.predictor.scalers.get('global_cpu')
            )
        else:
            # Use synthetic test data
            sequence = self.adapter.create_test_sequence()
        
        # Run prediction
        output = self.predictor.predict(
            sequence,
            system_id=system_id,
            data_source=DATA_SOURCE_COLD_START
        )
        
        return output
    
    def predict_from_runtime(
        self,
        request: Engine1Request,
        prometheus_data: Optional[list] = None,
        use_normalization: bool = True
    ) -> Engine1Output:
        """
        Generate prediction using runtime metrics (Prometheus or collected data).
        
        Used during normal operation after deployment.
        
        Args:
            request: Engine1Request with system_id and data
            prometheus_data: Optional Prometheus API response
            use_normalization: Whether to normalize using stored scaler
        
        Returns:
            Engine1Output ready for next engines
        """
        logger.info(f"Runtime prediction for system: {request.system_id}")
        
        # Request validation
        request.validate()
        
        # Convert request sequence to numpy
        sequence = np.array(request.workload_sequence, dtype=np.float32)
        
        # Validate sequence
        self.adapter.validate_sequence(sequence)
        
        # Run prediction
        output = self.predictor.predict(
            sequence,
            system_id=request.system_id,
            data_source=DATA_SOURCE_RUNTIME
        )
        
        # Update retraining tracker
        self.retraining_manager.samples_collected += 1
        
        # Check if retraining is needed
        if self.retraining_manager.should_retrain(
            self.retraining_manager.samples_collected
        ):
            logger.info("Retraining triggered - will schedule fine-tuning")
            # TODO: Queue retraining job for background worker
        
        return output
    
    def batch_predict(
        self,
        sequences: np.ndarray,
        system_id: str,
        data_source: str = DATA_SOURCE_RUNTIME
    ) -> list:
        """
        Predict for multiple sequences.
        
        Args:
            sequences: Array of shape (batch_size, 12, 2)
            system_id: System identifier
            data_source: "cold_start" or "runtime"
        
        Returns:
            List of Engine1Output objects
        """
        logger.info(f"Batch prediction: {len(sequences)} sequences for {system_id}")
        
        outputs = self.predictor.predict_multiple(
            sequences,
            system_id=system_id,
            data_source=data_source
        )
        
        return outputs
    
    def get_prediction_summary(self, output: Engine1Output) -> Dict:
        """
        Format Engine1Output for logging/debugging.
        
        Args:
            output: Engine1Output instance
        
        Returns:
            Summary dictionary
        """
        return {
            'system_id': output.system_id,
            'predicted_cpu': f"{output.predicted_cpu:.2f}%",
            'predicted_load_level': output.predicted_load_level,
            'recommended_pods': output.recommended_pods,
            'data_source': output.data_source,
            'confidence': f"{output.confidence:.4f}" if output.confidence else None,
            'timestamp': output.timestamp
        }


# Convenience functions for FastAPI integration

def initialize_engine1():
    """Initialize Engine 1 orchestrator (singleton pattern for FastAPI)."""
    try:
        engine = Engine1Orchestrator()
        logger.info("Engine 1 ready for serving")
        return engine
    except Exception as e:
        logger.error(f"Failed to initialize Engine 1: {e}")
        raise


def predict_workload(
    system_id: str,
    workload_sequence: list,
    data_source: str = "runtime"
) -> Dict:
    """
    FastAPI-friendly prediction endpoint.
    
    Args:
        system_id: System identifier
        workload_sequence: List of [cpu, memory] pairs (length 12)
        data_source: "cold_start" or "runtime"
    
    Returns:
        Prediction output as dictionary
    """
    engine = Engine1Orchestrator()
    
    request = Engine1Request(
        system_id=system_id,
        timestamp=None,  # Will use current time
        workload_sequence=workload_sequence,
        data_source=data_source
    )
    
    output = engine.predict_from_runtime(request)
    return output.to_dict()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    logger.info("="*80)
    logger.info("ENGINE 1 ORCHESTRATOR - INTEGRATION TEST")
    logger.info("="*80)
    
    try:
        # Initialize
        engine = Engine1Orchestrator()
        
        # Test 1: Cold-start
        logger.info("\nTest 1: Cold-start prediction")
        output1 = engine.predict_from_cold_start("system_01")
        logger.info(f"Output: {engine.get_prediction_summary(output1)}")
        
        # Test 2: Runtime prediction
        logger.info("\nTest 2: Runtime prediction")
        test_seq = np.array([
            [0.2, 0.3], [0.22, 0.32], [0.24, 0.34], [0.26, 0.36],
            [0.28, 0.38], [0.3, 0.4], [0.32, 0.42], [0.34, 0.44],
            [0.36, 0.46], [0.38, 0.48], [0.4, 0.5], [0.42, 0.52]
        ], dtype=np.float32)
        
        request = Engine1Request(
            system_id="system_02",
            timestamp="2026-04-15T10:00:00Z",
            workload_sequence=test_seq.tolist(),
            data_source="runtime"
        )
        
        output2 = engine.predict_from_runtime(request)
        logger.info(f"Output: {engine.get_prediction_summary(output2)}")
        
        logger.info("\n" + "="*80)
        logger.info("INTEGRATION TEST COMPLETE")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
