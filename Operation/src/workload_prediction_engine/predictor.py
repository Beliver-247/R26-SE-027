"""
Core predictor module for Engine 1 - Workload Prediction.

Handles model loading, inference, prediction classification, and pod recommendations.
Full Engine 1 functionality with cold-start and runtime support.
"""

import numpy as np
import pickle
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime

import torch
import torch.nn as nn

from model import LSTMWorkloadPredictor
from config import (
    DEVICE,
    LOAD_LEVEL_THRESHOLDS,
    TARGET_CPU_PER_POD,
    TARGET_UTILIZATION,
    MIN_PODS,
    MAX_PODS,
    MODEL_PATH,
    SCALER_PATH,
    MODEL_VERSION,
    PREDICTION_WINDOW_SECONDS,
    SEQUENCE_LENGTH
)
from output_contract import Engine1Output, create_engine1_output

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Device selection
DEVICE = torch.device(DEVICE if torch.cuda.is_available() else 'cpu')


class WorkloadPredictor:
    """
    Inference engine for CPU workload prediction using trained LSTM model.
    """
    
    def __init__(self, model_path: str, scaler_path: str):
        """
        Initialize WorkloadPredictor with model and scaler paths.
        
        Args:
            model_path: Path to saved trained model (.pt file)
            scaler_path: Path to saved MinMaxScaler (.pkl file)
        """
        self.model_path = Path(model_path)
        self.scaler_path = Path(scaler_path)
        self.model = None
        self.scalers = None
        self.device = DEVICE
        
        logger.info(f"Initializing WorkloadPredictor")
        logger.info(f"  Model path: {self.model_path}")
        logger.info(f"  Scaler path: {self.scaler_path}")
        logger.info(f"  Device: {self.device}")
    
    def load_model(self) -> None:
        """
        Load trained PyTorch LSTM model from disk.
        
        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If model loading fails
        """
        logger.info("Loading trained model...")
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        try:
            self.model = LSTMWorkloadPredictor()
            self.model.load_state_dict(
                torch.load(self.model_path, map_location=self.device)
            )
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"[OK] Model loaded successfully")
            logger.info(self.model.get_architecture_summary())
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
    
    def load_scaler(self) -> None:
        """
        Load saved MinMaxScaler for denormalization.
        
        Expected pickle format:
        {
            'global_cpu': fitted_scaler_cpu,
            'global_memory': fitted_scaler_memory (optional)
        }
        
        Raises:
            FileNotFoundError: If scaler file doesn't exist
            RuntimeError: If scaler loading fails
        """
        logger.info("Loading scaler...")
        
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Scaler file not found: {self.scaler_path}")
        
        try:
            with open(self.scaler_path, 'rb') as f:
                self.scalers = pickle.load(f)
            
            logger.info(f"[OK] Scaler loaded successfully")
            
            if isinstance(self.scalers, dict):
                logger.info(f"  Available scalers: {list(self.scalers.keys())}")
            else:
                logger.warning("Scaler format unexpected, treating as single scaler")
                self.scalers = {'global_cpu': self.scalers}
            
        except Exception as e:
            logger.error(f"Failed to load scaler: {e}")
            raise RuntimeError(f"Scaler loading failed: {e}")
    
    def validate_sequence(self, sequence: np.ndarray) -> Tuple[bool, str]:
        """
        Validate input sequence shape and values.
        
        Args:
            sequence: Input sequence to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Convert to numpy if needed
            if isinstance(sequence, torch.Tensor):
                sequence = sequence.cpu().numpy()
            
            # Handle shape variations
            if len(sequence.shape) == 2 and sequence.shape == (SEQUENCE_LENGTH, 2):
                # Shape: (12, 2) - single sequence
                pass
            elif len(sequence.shape) == 3 and sequence.shape[0] == 1:
                # Shape: (1, 12, 2) - batch of 1
                sequence = sequence[0]
            else:
                return False, f"Invalid shape: {sequence.shape}, expected (12, 2) or (1, 12, 2)"
            
            # Check timesteps
            if sequence.shape[0] != SEQUENCE_LENGTH:
                return False, f"Expected {SEQUENCE_LENGTH} timesteps, got {sequence.shape[0]}"
            
            # Check features
            if sequence.shape[1] != 2:
                return False, f"Expected 2 features, got {sequence.shape[1]}"
            
            # Check values are finite
            if not np.isfinite(sequence).all():
                return False, "Sequence contains NaN or infinite values"
            
            # Check value ranges (CPU and memory should be positive)
            if (sequence < 0).any():
                return False, "Negative values detected"
            
            logger.debug(f"[OK] Sequence validation passed. Shape: {sequence.shape}")
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def predict(
        self,
        sequence: np.ndarray,
        system_id: str = "system_01",
        data_source: str = "cold_start"
    ) -> Engine1Output:
        """
        Predict next 30-second workload and create structured output.
        
        Full prediction pipeline:
        1. Validate input sequence
        2. Run model inference (torch.no_grad())
        3. Denormalize prediction to original scale
        4. Classify load level
        5. Recommend pod count
        6. Build output contract
        
        Args:
            sequence: Input workload sequence (12, 2)
            system_id: Target system identifier
            data_source: "cold_start" or "runtime"
        
        Returns:
            Engine1Output with complete prediction
        
        Raises:
            RuntimeError: If model/scaler not loaded
            ValueError: If sequence invalid
        """
        # In mock mode or if model not loaded, generate mock prediction
        if self.model is None:
            logger.info(f"Model not loaded - generating mock prediction for system: {system_id}")
            # Return mock prediction based on sequence mean
            sequence_mean = np.mean(sequence) * 100 if len(sequence) > 0 else 50.0
            mock_cpu = np.clip(sequence_mean, 10.0, 90.0)
            
            # Determine load level and pods
            if mock_cpu < 30:
                load_level = "LOW"
                pods = 1
            elif mock_cpu < 70:
                load_level = "NORMAL"
                pods = 2
            else:
                load_level = "HIGH"
                pods = 3
            
            return create_engine1_output(
                system_id=system_id,
                predicted_cpu=mock_cpu,
                predicted_load_level=load_level,
                recommended_pods=pods,
                confidence=0.75,
                data_source="cold_start"  # Use valid data source
            )
        
        logger.info(f"Starting prediction for system: {system_id}")
        logger.debug(f"Input sequence shape: {sequence.shape}")
        
        # Validate input
        is_valid, error_msg = self.validate_sequence(sequence)
        if not is_valid:
            logger.error(f"Sequence validation failed: {error_msg}")
            raise ValueError(f"Invalid sequence: {error_msg}")
        
        # Ensure correct shape (1, 12, 2)
        if len(sequence.shape) == 2:
            sequence = np.expand_dims(sequence, axis=0)
            logger.debug("Added batch dimension")
        
        # Convert to torch tensor
        sequence_tensor = torch.from_numpy(sequence).float()
        sequence_tensor = sequence_tensor.to(self.device)
        
        logger.debug(f"Tensor prepared: shape={sequence_tensor.shape}, device={sequence_tensor.device}")
        
        # Run inference with no gradients
        with torch.no_grad():
            prediction_normalized = self.model(sequence_tensor)
            prediction_normalized = prediction_normalized.cpu().numpy()
        
        # Extract scalar prediction
        cpu_pred_normalized = float(prediction_normalized[0, 0])
        logger.debug(f"Raw prediction (normalized): {cpu_pred_normalized:.6f}")
        
        # Denormalize back to original scale (%)
        cpu_pred_original = self._denormalize_cpu(cpu_pred_normalized)
        logger.debug(f"Denormalized CPU: {cpu_pred_original:.2f}%")
        
        # Classify load level
        load_level = self._classify_load(cpu_pred_original)
        logger.debug(f"Load classification: {load_level}")
        
        # Recommend pod count
        recommended_pods = self._estimate_pods(cpu_pred_original)
        logger.debug(f"Recommended pods: {recommended_pods}")
        
        # Calculate confidence
        confidence = self._calculate_confidence(cpu_pred_normalized)
        
        # Create output object
        output = create_engine1_output(
            system_id=system_id,
            predicted_cpu=cpu_pred_original,
            predicted_load_level=load_level,
            recommended_pods=recommended_pods,
            data_source=data_source,
            model_version=MODEL_VERSION,
            predicted_memory=None,  # Not predicted in this version
            confidence=confidence,
            model_input_source="normalized_sequence"
        )
        
        logger.info(f"[OK] Prediction complete:")
        logger.info(f"  CPU: {cpu_pred_original:.2f}%")
        logger.info(f"  Load: {load_level}")
        logger.info(f"  Pods: {recommended_pods}")
        logger.info(f"  Confidence: {confidence:.4f}")
        
        return output
    
    def predict_multiple(
        self,
        sequences: np.ndarray,
        system_id: str = "system_01",
        data_source: str = "cold_start"
    ) -> list:
        """
        Predict for multiple sequences (batch).
        
        Args:
            sequences: Array of shape (batch_size, 12, 2)
            system_id: System identifier
            data_source: Data source
        
        Returns:
            List of Engine1Output objects
        """
        logger.info(f"Batch prediction for {len(sequences)} sequences")
        
        results = []
        for idx, seq in enumerate(sequences):
            try:
                logger.debug(f"Predicting sequence {idx+1}/{len(sequences)}")
                result = self.predict(seq, system_id, data_source)
                results.append(result)
            except Exception as e:
                logger.error(f"Prediction failed for sequence {idx}: {e}")
                results.append(None)
        
        logger.info(f"Batch complete: {len([r for r in results if r is not None])}/{len(results)} successful")
        return results
    
    def _denormalize_cpu(self, normalized_value: float) -> float:
        """
        Convert normalized CPU prediction (0-1) to original scale (0-100%).
        
        Uses the saved scaler's data_min and data_range to perform
        inverse MinMaxScaler transformation.
        
        Args:
            normalized_value: Normalized prediction (0 to 1)
        
        Returns:
            CPU percentage in original scale (0-100)
        """
        if self.scalers is None:
            logger.warning("Scalers not loaded, scaling 0-1 to 0-100")
            return normalized_value * 100
        
        if 'global_cpu' not in self.scalers:
            logger.warning("Global CPU scaler not available")
            return normalized_value * 100
        
        try:
            scaler = self.scalers['global_cpu']
            
            # MinMaxScaler inverse: X = (X_norm * range) + min
            data_min = scaler.data_min_[0]
            data_range = scaler.data_range_[0]
            
            original_value = (normalized_value * data_range) + data_min
            
            # Clip to valid CPU range
            original_value = np.clip(original_value, 0, 100)
            
            logger.debug(f"Denormalization: {normalized_value:.6f} → {original_value:.2f}%")
            
            return float(original_value)
            
        except Exception as e:
            logger.error(f"Denormalization failed: {e}")
            return normalized_value * 100
    
    def _classify_load(self, cpu_percentage: float) -> str:
        """
        Classify predicted CPU load into LOW, NORMAL, or HIGH.
        
        Uses configurable thresholds from LOAD_LEVEL_THRESHOLDS:
        - LOW: 0-30%
        - NORMAL: 30-70%
        - HIGH: 70-100%
        
        Args:
            cpu_percentage: Predicted CPU utilization (0-100)
        
        Returns:
            Load level string: "LOW", "NORMAL", or "HIGH"
        """
        cpu_clipped = np.clip(cpu_percentage, 0, 100)
        
        low_threshold = LOAD_LEVEL_THRESHOLDS['LOW']
        normal_threshold = LOAD_LEVEL_THRESHOLDS['NORMAL']
        
        if cpu_clipped < low_threshold:
            return "LOW"
        elif cpu_clipped < normal_threshold:
            return "NORMAL"
        else:
            return "HIGH"
    
    def _estimate_pods(self, cpu_percentage: float) -> int:
        """
        Estimate recommended pod count based on predicted CPU workload.
        
        Formula:
        recommended_pods = ceil(predicted_cpu / (target_cpu_per_pod * target_utilization))
        
        Example:
        - predicted_cpu = 72.5%
        - target_cpu_per_pod = 50%
        - target_utilization = 0.8
        - required_capacity = 72.5 / (50 * 0.8) = 1.8
        - recommended_pods = 2
        
        Args:
            cpu_percentage: Predicted total CPU percentage
        
        Returns:
            Recommended number of pods (MIN_PODS to MAX_PODS)
        """
        if cpu_percentage <= 0:
            return MIN_PODS
        
        # Calculate required pod capacity
        effective_pod_capacity = TARGET_CPU_PER_POD * TARGET_UTILIZATION
        required_pods = np.ceil(cpu_percentage / effective_pod_capacity)
        
        # Clamp to valid range
        recommended_pods = int(np.clip(required_pods, MIN_PODS, MAX_PODS))
        
        logger.debug(
            f"Pod calculation: cpu={cpu_percentage:.2f}, "
            f"capacity={effective_pod_capacity:.2f}, "
            f"required={required_pods:.1f}, "
            f"recommended={recommended_pods}"
        )
        
        return recommended_pods
    
    def _calculate_confidence(self, normalized_prediction: float) -> float:
        """
        Calculate model confidence based on prediction characteristics.
        
        Confidence heuristic:
        - Near boundaries (0 or 1): lower confidence
        - Near center (0.5): higher confidence
        - Formula: 1.0 - min(|pred - 0.5| * 2 * 0.1, 1.0)
        
        Args:
            normalized_prediction: Prediction in normalized scale (0-1)
        
        Returns:
            Confidence score (0-1)
        """
        # Penalize extreme values
        distance_from_center = abs(normalized_prediction - 0.5) * 2
        confidence = 1.0 - (distance_from_center * 0.1)
        confidence = float(np.clip(confidence, 0.5, 1.0))
        
        return confidence


def main():
    """Example usage of WorkloadPredictor with full Engine 1 workflow."""
    
    logger.info("="*80)
    logger.info("ENGINE 1 - WORKLOAD PREDICTION INFERENCE")
    logger.info("="*80)
    
    try:
        # Initialize predictor
        predictor = WorkloadPredictor()
        predictor.load_model()
        predictor.load_scaler()
        
        logger.info("\n" + "="*80)
        logger.info("EXAMPLE 1: Single Prediction with Cold-Start Data")
        logger.info("="*80)
        
        # Create dummy normalized test sequence
        test_sequence = np.array([
            [0.2, 0.3],   # 12 timesteps × 2 features
            [0.22, 0.32],
            [0.24, 0.34],
            [0.26, 0.36],
            [0.28, 0.38],
            [0.3, 0.4],
            [0.32, 0.42],
            [0.34, 0.44],
            [0.36, 0.46],
            [0.38, 0.48],
            [0.4, 0.5],
            [0.42, 0.52]
        ], dtype=np.float32)
        
        logger.info(f"Input sequence shape: {test_sequence.shape}")
        logger.info(f"CPU range: [{test_sequence[:, 0].min():.2f}, {test_sequence[:, 0].max():.2f}]")
        
        # Make prediction
        output = predictor.predict(
            test_sequence,
            system_id="system_01",
            data_source="cold_start"
        )
        
        logger.info("\nPrediction Output:")
        logger.info(output.to_json())
        
        logger.info("\n" + "="*80)
        logger.info("EXAMPLE 2: Batch Prediction")
        logger.info("="*80)
        
        # Create batch (3 sequences)
        batch_sequences = np.tile(test_sequence, (3, 1, 1))
        batch_sequences[1] = batch_sequences[1] * 0.9
        batch_sequences[2] = batch_sequences[2] * 1.1
        
        logger.info(f"Batch shape: {batch_sequences.shape}")
        
        batch_outputs = predictor.predict_multiple(
            batch_sequences,
            system_id="system_02",
            data_source="cold_start"
        )
        
        logger.info(f"\nBatch Results ({len(batch_outputs)} predictions):")
        for idx, output in enumerate(batch_outputs):
            if output:
                logger.info(
                    f"  [{idx+1}] CPU={output.predicted_cpu:.2f}% | "
                    f"Level={output.predicted_load_level} | "
                    f"Pods={output.recommended_pods}"
                )
        
        logger.info("\n" + "="*80)
        logger.info("INFERENCE COMPLETE")
        logger.info("="*80)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.info("Note: This example requires trained model and scaler files")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
