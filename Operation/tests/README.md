# Tests Directory

Unit and integration tests for the Green DevOps Operation Component.

## Test Structure

- Unit tests: Individual component testing
- Integration tests: End-to-end workflow testing
- Fixtures: Mock data and test utilities

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_workload_predictor.py -v

# Run tests matching pattern
pytest tests/ -k "prediction" -v

# Run with verbose output
pytest tests/ -vv
```

## Test Files

- `test_data_layer.py` - Data collection and preprocessing
- `test_workload_predictor.py` - Workload prediction engine
- `test_carbon_engine.py` - Carbon emission engine
- `test_job_prioritizer.py` - Job prioritization engine
- `test_decision_engine.py` - Decision orchestration
- `test_kubernetes_integration.py` - K8s integration
- `test_api.py` - REST API endpoints

## Fixtures

Mock data and utilities in `fixtures/`:
- `mock_metrics.json` - Sample Prometheus metrics
- `mock_k8s_state.yaml` - Mock Kubernetes state
- `sample_data.parquet` - Sample preprocessed data

## Writing Tests

```python
import pytest
from src.workload_prediction_engine.predictor import Predictor

@pytest.fixture
def predictor():
    return Predictor()

def test_prediction_output_shape(predictor):
    result = predictor.predict(mock_metrics)
    assert result['pod_count'] > 0
    assert 0 <= result['confidence'] <= 1

def test_prediction_with_low_data(predictor):
    with pytest.raises(ValueError):
        predictor.predict({})  # Empty metrics
```

## Coverage Goals

- Unit tests: 80%+ coverage per module
- Integration tests: All main workflows
- Focus on: Business logic, error handling, edge cases

## CI/CD Integration

Tests run automatically on:
- Push to main branch
- Pull requests
- Nightly scheduled runs

See `.github/workflows/test.yaml` for CI configuration.
