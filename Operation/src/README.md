# Source Code Structure

This directory contains all application code organized by responsibility:

## Core Modules

### `shared/` - Common Infrastructure
- `schemas.py` - Pydantic data models for inter-component communication
- `constants.py` - System constants and enumerations
- `utils.py` - Utility functions
- `logger.py` - Logging setup
- `config.py` - Configuration loader
- `exceptions.py` - Custom exception classes

### `data_layer/` - Data Pipeline
Handles data collection, preprocessing, validation, and feature engineering:
- `prometheus_client.py` - Query Prometheus metrics
- `metrics_collector.py` - Collect K8s metrics
- `data_preprocessor.py` - Clean and normalize data
- `feature_engineer.py` - Extract features for models
- `data_validator.py` - Validate data quality

### `workload_prediction_engine/` - Engine 1
Predicts near-future workload:
- `predictor.py` - Main prediction interface
- `model.py` - LSTM/ARIMA model implementations
- `trainer.py` - Training pipeline
- `evaluator.py` - Performance evaluation

### `carbon_emission_engine/` - Engine 2
Estimates carbon impact:
- `calculator.py` - Main calculation interface
- `models.py` - Carbon impact models
- `scenarios.py` - Calculate scale-up/down/delay scenarios
- `evaluator.py` - Validation and metrics

### `job_prioritization_engine/` - Engine 3
Manages job delays and prioritization:
- `prioritizer.py` - Main prioritization interface
- `classifier.py` - Classify job criticality
- `queue_manager.py` - Manage delayed job queue
- `policy_engine.py` - Apply prioritization policies
- `evaluator.py` - Fairness and impact metrics

### `decision_engine/` - Orchestration
Combines all engines and makes final decision:
- `optimizer.py` - Multi-objective optimization
- `constraint_checker.py` - Validate SLA/resource constraints
- `decision_logger.py` - Log all decisions for audit trail

### `kubernetes_integration/` - K8s Interface
Executes scaling decisions:
- `k8s_client.py` - Wrapper around Kubernetes Python client
- `scaling_executor.py` - Execute pod scaling operations
- `event_monitor.py` - Monitor K8s events

### `metrics_layer/` - Monitoring Integration
Exports metrics and publishes to Grafana:
- `prometheus_exporter.py` - Export metrics in Prometheus format
- `grafana_publisher.py` - Push to Grafana

### `api/` - REST API Layer
Provides HTTP interface:
- `main.py` - FastAPI app initialization
- `routes.py` - API endpoint definitions
- `middleware.py` - Authentication, error handling, logging
- `dependencies.py` - FastAPI dependency injection

### `background_jobs/` - Scheduled Tasks
Runs periodic jobs:
- `scheduler.py` - APScheduler configuration
- `retraining_job.py` - Model retraining task
- `metrics_collection_job.py` - Periodic metric collection
- `job_release_scheduler.py` - Release delayed jobs
- `health_check_job.py` - System health monitoring

## Development Guidelines

1. **Imports**: Use relative imports within src/, absolute for external packages
2. **Configuration**: Use `shared/config.py` for all config access
3. **Logging**: Use `shared/logger.py` for consistent logging
4. **Schemas**: Define all data contracts in `shared/schemas.py`
5. **Error Handling**: Use custom exceptions from `shared/exceptions.py`
6. **Testing**: Unit tests in `tests/` mirror this structure

## Module Dependencies

```
shared/
    ↓
data_layer/ ← depends on shared/
    ↓
workload_prediction_engine/ ← depends on shared/, data_layer/
    ↓ carbon_emission_engine/ ← depends on shared/, data_layer/
    ↓ job_prioritization_engine/ ← depends on shared/, data_layer/
    ↓
decision_engine/ ← depends on all engines
    ↓
kubernetes_integration/ ← depends on shared/, decision_engine/
    ↓
api/ ← depends on all layers
    ↓
background_jobs/ ← depends on all modules
```

## Adding New Modules

When adding a new module:
1. Create directory in `src/`
2. Add `__init__.py`
3. Create module files with clear interfaces
4. Add type hints to all functions
5. Add corresponding tests in `tests/`
6. Update this README
