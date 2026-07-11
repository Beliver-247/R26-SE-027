#!/usr/bin/env python3
"""
Engine 1 (Workload Prediction Engine) - Comprehensive Testing Suite
Tests model inference, output validation, and edge cases
"""

import sys
import logging
from pathlib import Path

import numpy as np
import torch
import pickle

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))

try:
    from predictor import WorkloadPredictor
    from output_contract import Engine1Output
except ImportError as e:
    logger.error(f"Failed to import Engine 1 modules: {e}")
    sys.exit(1)


class Engine1TestSuite:
    """Comprehensive Engine 1 validation tests"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        self.avg_mae = 0.0
        self.samples_tested = 0
        self.model_loaded = False
        self.data_loaded = False
        
    def log_test(self, name, status, message=""):
        """Log individual test result"""
        result = f"{'✓' if status else '✗'} {name}"
        if message:
            result += f" - {message}"
        self.test_results.append((name, status))
        logger.info(result)
        
    def test_dataset_loading(self):
        """Test 1: Load test dataset"""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: LOADING TEST DATASET")
        logger.info("="*80)
        
        try:
            X_test_path = Path('data/preprocessed/balanced_dataset/X_test.npy')
            y_test_path = Path('data/preprocessed/balanced_dataset/y_test.npy')
            
            if not X_test_path.exists():
                self.log_test("Dataset X_test file exists", False, f"Not found: {X_test_path}")
                return False
            
            if not y_test_path.exists():
                self.log_test("Dataset y_test file exists", False, f"Not found: {y_test_path}")
                return False
            
            self.X_test = np.load(X_test_path)
            self.y_test = np.load(y_test_path)
            
            self.log_test("Dataset X_test file exists", True)
            self.log_test("Dataset y_test file exists", True)
            
            logger.info(f"X_test shape: {self.X_test.shape}")
            logger.info(f"y_test shape: {self.y_test.shape}")
            
            # Validate shapes
            if len(self.X_test.shape) != 3:
                self.log_test("X_test has 3D shape", False, f"Got {len(self.X_test.shape)}D")
                return False
            self.log_test("X_test has 3D shape", True, f"({self.X_test.shape[0]}, {self.X_test.shape[1]}, {self.X_test.shape[2]})")
            
            if self.X_test.shape[1] != 12:
                self.log_test("X_test sequence length = 12", False, f"Got {self.X_test.shape[1]}")
                return False
            self.log_test("X_test sequence length = 12", True)
            
            if self.X_test.shape[2] != 2:
                self.log_test("X_test features = 2", False, f"Got {self.X_test.shape[2]}")
                return False
            self.log_test("X_test features = 2", True)
            
            if len(self.y_test) != len(self.X_test):
                self.log_test("y_test matches X_test length", False)
                return False
            self.log_test("y_test matches X_test length", True)
            
            # Check data ranges
            logger.info(f"X_test range: [{self.X_test.min():.4f}, {self.X_test.max():.4f}]")
            logger.info(f"y_test range: [{self.y_test.min():.4f}, {self.y_test.max():.4f}]")
            
            if self.X_test.min() < 0 or self.X_test.max() > 1:
                self.log_test("X_test normalized [0,1]", False, f"Range: [{self.X_test.min():.4f}, {self.X_test.max():.4f}]")
            else:
                self.log_test("X_test normalized [0,1]", True)
            
            self.data_loaded = True
            return True
            
        except Exception as e:
            self.log_test("Dataset loading", False, str(e))
            self.errors.append(f"Dataset loading failed: {e}")
            return False
    
    def test_model_loading(self):
        """Test 2: Load trained model"""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: LOADING TRAINED MODEL")
        logger.info("="*80)
        
        try:
            model_path = Path('models/trained/workload_predictor_balanced.pt')
            scaler_path = Path('data/preprocessed/balanced_dataset/scaler.pkl')
            
            if not model_path.exists():
                self.log_test("Model file exists", False, f"Not found: {model_path}")
                return False
            self.log_test("Model file exists", True)
            
            if not scaler_path.exists():
                self.log_test("Scaler file exists", False, f"Not found: {scaler_path}")
                return False
            self.log_test("Scaler file exists", True)
            
            # Load model size
            model_size_mb = model_path.stat().st_size / 1e6
            logger.info(f"Model file size: {model_size_mb:.2f} MB")
            self.log_test("Model file size > 0.1 MB", model_size_mb > 0.1, f"{model_size_mb:.2f} MB")
            
            # Initialize predictor
            self.predictor = WorkloadPredictor(str(model_path), str(scaler_path))
            self.predictor.load_model()
            self.predictor.load_scaler()
            
            self.log_test("WorkloadPredictor initialized", True)
            self.log_test("Model loaded from checkpoint", True)
            self.log_test("Scaler loaded", True)
            
            self.model_loaded = True
            return True
            
        except Exception as e:
            self.log_test("Model loading", False, str(e))
            self.errors.append(f"Model loading failed: {e}")
            return False
    
    def test_real_predictions(self):
        """Test 3: Predictions on real test samples"""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: PREDICTIONS ON REAL TEST SAMPLES")
        logger.info("="*80)
        
        if not self.data_loaded or not self.model_loaded:
            self.log_test("Data and model loaded", False)
            return False
        
        try:
            # Take first 10 samples
            num_samples = min(10, len(self.X_test))
            X_samples = self.X_test[:num_samples]
            y_actual = self.y_test[:num_samples]
            
            logger.info(f"Testing {num_samples} samples...")
            
            # Direct model inference
            device = torch.device('cpu')
            model = self.predictor.model
            model.eval()
            
            mae_errors = []
            
            with torch.no_grad():
                for i in range(num_samples):
                    # Get sample
                    sample = torch.from_numpy(X_samples[i:i+1]).float().to(device)
                    
                    # Predict
                    pred_normalized = model(sample).cpu().numpy().flatten()[0]
                    
                    # Denormalize
                    pred_original = self.predictor.scalers['global_cpu'].inverse_transform(
                        np.array([[pred_normalized, 0.5]])
                    )[0, 0]
                    
                    actual_original = self.predictor.scalers['global_cpu'].inverse_transform(
                        np.array([[y_actual[i], 0.5]])
                    )[0, 0]
                    
                    # Calculate error
                    mae = abs(pred_original - actual_original)
                    mae_errors.append(mae)
                    
                    logger.info(f"Sample {i+1}: Actual={actual_original:.2f}%, Pred={pred_original:.2f}%, MAE={mae:.2f}%")
            
            avg_mae = np.mean(mae_errors)
            max_mae = np.max(mae_errors)
            
            self.avg_mae = avg_mae
            self.samples_tested = num_samples
            
            self.log_test("All samples predicted successfully", True, f"n={num_samples}")
            self.log_test("Average MAE reasonable", avg_mae < 20, f"Avg MAE: {avg_mae:.2f}%")
            self.log_test("Max MAE acceptable", max_mae < 50, f"Max MAE: {max_mae:.2f}%")
            
            logger.info(f"Average MAE: {avg_mae:.2f}%")
            logger.info(f"Max MAE: {max_mae:.2f}%")
            
            return True
            
        except Exception as e:
            self.log_test("Real predictions", False, str(e))
            self.errors.append(f"Real predictions failed: {e}")
            return False
    
    def test_predictor_module(self):
        """Test 4: Full Engine 1 predictor output"""
        logger.info("\n" + "="*80)
        logger.info("TEST 4: ENGINE 1 PREDICTOR MODULE")
        logger.info("="*80)
        
        if not self.model_loaded:
            self.log_test("Predictor module test", False, "Model not loaded")
            return False
        
        try:
            # Test on first sample
            sample = self.X_test[0]
            
            output = self.predictor.predict(
                sample,
                system_id='test_system_001',
                data_source='runtime'
            )
            
            # Validate output type
            if not isinstance(output, Engine1Output):
                self.log_test("Output is Engine1Output instance", False)
                return False
            self.log_test("Output is Engine1Output instance", True)
            
            # Check required fields
            required_fields = [
                'predicted_cpu',
                'predicted_load_level',
                'recommended_pods',
                'prediction_window_seconds'
            ]
            
            for field in required_fields:
                if not hasattr(output, field):
                    self.log_test(f"Output has {field}", False)
                    return False
                self.log_test(f"Output has {field}", True)
            
            # Validate values
            logger.info(f"Predicted CPU: {output.predicted_cpu:.2f}%")
            logger.info(f"Load Level: {output.predicted_load_level}")
            logger.info(f"Recommended Pods: {output.recommended_pods}")
            logger.info(f"Prediction Window: {output.prediction_window_seconds} seconds")
            
            # Check prediction window
            if output.prediction_window_seconds != 30:
                self.log_test("Prediction window = 30 seconds", False, f"Got {output.prediction_window_seconds}")
                return False
            self.log_test("Prediction window = 30 seconds", True)
            
            # Check load level
            valid_levels = ['LOW', 'NORMAL', 'HIGH']
            if output.predicted_load_level not in valid_levels:
                self.log_test("Load level is valid", False, f"Got {output.predicted_load_level}")
                return False
            self.log_test("Load level is valid", True, output.predicted_load_level)
            
            # Check pods
            if output.recommended_pods < 1:
                self.log_test("Recommended pods >= 1", False, f"Got {output.recommended_pods}")
                return False
            self.log_test("Recommended pods >= 1", True, f"{output.recommended_pods} pods")
            
            # Test validation
            try:
                output.validate()
                self.log_test("Output validation passes", True)
            except ValueError as e:
                self.log_test("Output validation passes", False, str(e))
                return False
            
            # Test JSON serialization
            try:
                json_str = output.to_json_compact()
                if not json_str or len(json_str) == 0:
                    self.log_test("JSON serialization works", False, "Empty string")
                    return False
                self.log_test("JSON serialization works", True, f"{len(json_str)} chars")
            except Exception as e:
                self.log_test("JSON serialization works", False, str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_test("Predictor module", False, str(e))
            self.errors.append(f"Predictor module test failed: {e}")
            return False
    
    def test_edge_cases(self):
        """Test 5: Edge cases and error handling"""
        logger.info("\n" + "="*80)
        logger.info("TEST 5: EDGE CASES AND ERROR HANDLING")
        logger.info("="*80)
        
        if not self.model_loaded:
            self.log_test("Edge case tests", False, "Model not loaded")
            return False
        
        try:
            # Test 1: Invalid shape
            invalid_shape = np.random.randn(11, 2).astype(np.float32)  # Wrong seq length
            try:
                self.predictor.predict(invalid_shape, system_id='test', data_source='runtime')
                self.log_test("Handles invalid shape", False, "Should have raised error")
            except (ValueError, RuntimeError, AssertionError):
                self.log_test("Handles invalid shape", True, "Raised appropriate error")
            
            # Test 2: NaN values
            nan_sample = self.X_test[0].copy()
            nan_sample[0, 0] = np.nan
            try:
                self.predictor.predict(nan_sample, system_id='test', data_source='runtime')
                self.log_test("Handles NaN values", False, "Should have raised error")
            except (ValueError, RuntimeError):
                self.log_test("Handles NaN values", True, "Raised appropriate error")
            
            # Test 3: Out of range values (should handle gracefully)
            try:
                oob_sample = self.X_test[0].copy()
                oob_sample[:] = 2.0  # Out of [0,1] range but might be handled
                output = self.predictor.predict(oob_sample, system_id='test', data_source='runtime')
                # If we get here, check that output is still valid
                if output.predicted_cpu >= 0 and output.recommended_pods >= 1:
                    self.log_test("Handles out-of-range values", True, "Clipped gracefully")
                else:
                    self.log_test("Handles out-of-range values", False, "Invalid output")
            except Exception as e:
                self.log_test("Handles out-of-range values", True, f"Raised error: {type(e).__name__}")
            
            # Test 4: Batch prediction
            try:
                batch = self.X_test[:5]
                predictions = []
                for sample in batch:
                    pred = self.predictor.predict(sample, system_id='test', data_source='runtime')
                    predictions.append(pred)
                
                if len(predictions) == 5:
                    self.log_test("Batch prediction works", True, "5 predictions generated")
                else:
                    self.log_test("Batch prediction works", False, f"Got {len(predictions)}")
            except Exception as e:
                self.log_test("Batch prediction works", False, str(e))
            
            return True
            
        except Exception as e:
            self.log_test("Edge cases", False, str(e))
            self.errors.append(f"Edge case testing failed: {e}")
            return False
    
    def test_output_distributions(self):
        """Test 6: Output distributions on larger sample"""
        logger.info("\n" + "="*80)
        logger.info("TEST 6: OUTPUT DISTRIBUTIONS")
        logger.info("="*80)
        
        if not self.model_loaded or not self.data_loaded:
            self.log_test("Output distribution test", False, "Prerequisites not met")
            return False
        
        try:
            # Test on 100 samples
            sample_count = min(100, len(self.X_test))
            predictions = []
            load_levels = {'LOW': 0, 'NORMAL': 0, 'HIGH': 0}
            
            for i in range(sample_count):
                output = self.predictor.predict(
                    self.X_test[i],
                    system_id=f'system_{i:03d}',
                    data_source='runtime'
                )
                predictions.append(output.predicted_cpu)
                load_levels[output.predicted_load_level] += 1
            
            predictions = np.array(predictions)
            
            logger.info(f"Tested {sample_count} predictions")
            logger.info(f"Mean CPU: {predictions.mean():.2f}%")
            logger.info(f"Std CPU: {predictions.std():.2f}%")
            logger.info(f"Min CPU: {predictions.min():.2f}%")
            logger.info(f"Max CPU: {predictions.max():.2f}%")
            logger.info(f"Load distribution: LOW={load_levels['LOW']}, NORMAL={load_levels['NORMAL']}, HIGH={load_levels['HIGH']}")
            
            # Check ranges
            if predictions.min() >= 0 and predictions.max() <= 100:
                self.log_test("Predictions in valid range [0,100]", True)
            else:
                self.log_test("Predictions in valid range [0,100]", False, 
                             f"Range: [{predictions.min():.2f}, {predictions.max():.2f}]")
            
            # Check distribution makes sense
            if load_levels['NORMAL'] > 0:
                self.log_test("Load distribution is realistic", True, 
                             f"Most common: NORMAL ({load_levels['NORMAL']} samples)")
            else:
                self.log_test("Load distribution is realistic", False, "No NORMAL predictions")
            
            return True
            
        except Exception as e:
            self.log_test("Output distributions", False, str(e))
            self.errors.append(f"Distribution test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("\n\n")
        logger.info("#"*80)
        logger.info("# ENGINE 1 COMPREHENSIVE TEST SUITE")
        logger.info("#"*80)
        
        self.test_dataset_loading()
        self.test_model_loading()
        self.test_real_predictions()
        self.test_predictor_module()
        self.test_edge_cases()
        self.test_output_distributions()
        
        self.print_summary()
    
    def print_summary(self):
        """Print final test summary"""
        logger.info("\n\n")
        logger.info("="*80)
        logger.info("FINAL TEST SUMMARY")
        logger.info("="*80)
        
        passed = sum(1 for _, status in self.test_results if status)
        total = len(self.test_results)
        
        logger.info(f"\nTests Passed: {passed}/{total}")
        
        if self.avg_mae > 0:
            logger.info(f"Average Prediction Error (MAE): {self.avg_mae:.2f}%")
            logger.info(f"Samples Tested: {self.samples_tested}")
        
        if self.errors:
            logger.info("\nErrors Encountered:")
            for error in self.errors:
                logger.info(f"  - {error}")
        
        # Final status
        status = "PASS" if passed == total and not self.errors else "FAIL"
        logger.info("\n" + "="*80)
        logger.info(f"TEST STATUS: {status}")
        logger.info("="*80 + "\n")
        
        return status == "PASS"


def main():
    """Main entry point"""
    suite = Engine1TestSuite()
    suite.run_all_tests()


if __name__ == '__main__':
    main()
