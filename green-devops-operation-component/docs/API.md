# REST API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication. In production, add API key validation in `src/api/middleware.py`.

## Health & Status Endpoints

### GET /health

Check if service is alive.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-04-15T10:30:00Z"
}
```

### GET /ready

Check if service is ready to serve requests.

**Response** (200 OK):
```json
{
  "status": "ready",
  "models_loaded": true,
  "prometheus_connected": true,
  "kubernetes_connected": true
}
```

## Prediction Endpoints

### POST /predict/workload

Predict workload for next 30 seconds.

**Request**:
```json
{
  "namespace": "default",
  "deployment": "api-server"
}
```

**Response** (200 OK):
```json
{
  "predicted_cpu_cores": 5.2,
  "predicted_memory_gb": 8.1,
  "predicted_pod_count": 3,
  "confidence": 0.92,
  "timestamp": "2024-04-15T10:30:00Z"
}
```

## Decision Endpoints

### POST /decide/scaling

Get recommended pod scaling decision.

**Request**:
```json
{
  "namespace": "default",
  "deployment": "api-server",
  "current_pod_count": 2,
  "current_cpu_utilization": 0.85,
  "current_memory_utilization": 0.72
}
```

**Response** (200 OK):
```json
{
  "action": "scale_up",
  "recommended_pod_count": 4,
  "carbon_cost_grams": 125.5,
  "delay_carbon_savings_grams": 45.2,
  "net_carbon_impact": 80.3,
  "sla_impact": "compliant",
  "confidence": 0.88,
  "timestamp": "2024-04-15T10:30:00Z",
  "explanation": "Predicted workload increase. Scaling up saves carbon via delayed jobs."
}
```

## Carbon Endpoints

### POST /carbon/estimate

Estimate carbon impact of a scaling decision.

**Request**:
```json
{
  "current_pod_count": 2,
  "target_pod_count": 4,
  "scaling_duration_seconds": 300,
  "energy_source": "grid"
}
```

**Response** (200 OK):
```json
{
  "carbon_grams": 125.5,
  "carbon_breakdown": {
    "scaling_operation": 45.2,
    "infrastructure": 50.1,
    "embodied": 30.2
  },
  "carbon_per_pod_per_second": 0.104,
  "energy_kwh": 0.348
}
```

### GET /carbon/current

Get current carbon emissions.

**Response** (200 OK):
```json
{
  "current_emissions_grams": 1250.5,
  "emissions_per_pod": 625.25,
  "energy_intensity": 400,
  "timestamp": "2024-04-15T10:30:00Z"
}
```

## Job Endpoints

### POST /jobs/prioritize

Determine job priorities and identify delayable jobs.

**Request**:
```json
{
  "jobs": [
    {
      "job_id": "job-001",
      "job_type": "api_request",
      "estimated_duration_seconds": 30,
      "deadline_seconds": 100
    },
    {
      "job_id": "job-002",
      "job_type": "batch_processing",
      "estimated_duration_seconds": 300,
      "deadline_seconds": 3600
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "priorities": [
    {
      "job_id": "job-001",
      "priority": "critical",
      "delay_allowed": false,
      "reason": "API request with tight deadline"
    },
    {
      "job_id": "job-002",
      "priority": "delayable",
      "delay_allowed": true,
      "max_delay_seconds": 900,
      "reason": "Batch job with flexible timeline"
    }
  ],
  "delayable_count": 1,
  "carbon_savings_if_delayed": 125.5
}
```

### POST /jobs/delay

Delay a job until later.

**Request**:
```json
{
  "job_id": "job-002",
  "reason": "High carbon period"
}
```

**Response** (200 OK):
```json
{
  "job_id": "job-002",
  "status": "delayed",
  "queued_at": "2024-04-15T10:30:00Z",
  "estimated_release_time": "2024-04-15T10:40:00Z",
  "carbon_saved": 125.5
}
```

### GET /jobs/delayed

List currently delayed jobs.

**Response** (200 OK):
```json
{
  "delayed_jobs": [
    {
      "job_id": "job-002",
      "delayed_at": "2024-04-15T10:30:00Z",
      "estimated_release": "2024-04-15T10:40:00Z",
      "carbon_saved_grams": 125.5
    }
  ],
  "total_count": 1,
  "total_carbon_saved": 125.5
}
```

### POST /jobs/release

Release a delayed job immediately.

**Request**:
```json
{
  "job_id": "job-002"
}
```

**Response** (200 OK):
```json
{
  "job_id": "job-002",
  "status": "released",
  "delayed_duration_seconds": 600,
  "carbon_saved": 125.5
}
```

## Metrics Endpoints

### GET /metrics

Prometheus metrics endpoint.

**Response**: Prometheus format metrics

```
# HELP workload_prediction_mae Workload prediction mean absolute error
# TYPE workload_prediction_mae gauge
workload_prediction_mae{deployment="api-server"} 0.45

# HELP carbon_emissions_grams Current carbon emissions
# TYPE carbon_emissions_grams gauge
carbon_emissions_grams{namespace="default"} 1250.5

# HELP scaling_decision_duration_ms Time to make scaling decision
# TYPE scaling_decision_duration_ms histogram
scaling_decision_duration_ms_bucket{le="100"} 45
scaling_decision_duration_ms_bucket{le="500"} 148
```

## Model Management Endpoints

### GET /models/status

Get status of all loaded models.

**Response** (200 OK):
```json
{
  "workload_predictor": {
    "version": "1.0",
    "loaded": true,
    "training_date": "2024-04-01",
    "accuracy_mae": 0.45,
    "data_source": "public_datasets"
  },
  "carbon_estimator": {
    "version": "1.0",
    "loaded": true,
    "training_date": "2024-04-01",
    "data_source": "public_datasets"
  },
  "job_prioritizer": {
    "version": "1.0",
    "loaded": true,
    "training_date": "2024-04-01",
    "data_source": "public_datasets"
  }
}
```

### POST /models/reload

Reload models from disk (useful after retraining).

**Response** (200 OK):
```json
{
  "status": "reloaded",
  "models_loaded": 3,
  "timestamp": "2024-04-15T10:30:00Z"
}
```

## Admin Endpoints

### GET /admin/config

Get current system configuration.

**Response** (200 OK):
```json
{
  "environment": "prod",
  "namespace": "green-devops",
  "prediction_window_seconds": 30,
  "scaling_cooldown_seconds": 60,
  "min_pod_count": 2,
  "max_pod_count": 100,
  "carbon_calculation_method": "grid_intensity"
}
```

### POST /admin/scaling-decision

Manually trigger a scaling decision (admin only).

**Request**:
```json
{
  "namespace": "default",
  "deployment": "api-server"
}
```

**Response** (200 OK):
```json
{
  "decision": { /* same as /decide/scaling */ },
  "executed": true,
  "timestamp": "2024-04-15T10:30:00Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request",
  "details": "namespace is required"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found",
  "details": "Deployment api-server not found in namespace default"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "details": "Failed to predict workload",
  "request_id": "abc123"
}
```

### 503 Service Unavailable
```json
{
  "error": "Service unavailable",
  "details": "Prometheus connection failed"
}
```

## Rate Limiting

- Default: 100 requests per minute per IP
- Can be configured in `config/default.yaml`
- Returns 429 Too Many Requests if exceeded

## Webhooks (Optional)

For automated job release notifications:

```yaml
webhook_config:
  enabled: false
  endpoint: "https://your-system/webhook"
  events: ["job_released", "scaling_executed"]
```

## Examples

### Example 1: Complete Scaling Decision Flow

```bash
# 1. Predict workload
curl -X POST http://localhost:8000/predict/workload \
  -H "Content-Type: application/json" \
  -d '{"namespace":"default","deployment":"api-server"}'

# 2. Get scaling decision
curl -X POST http://localhost:8000/decide/scaling \
  -H "Content-Type: application/json" \
  -d '{
    "namespace":"default",
    "deployment":"api-server",
    "current_pod_count":2,
    "current_cpu_utilization":0.85
  }'

# 3. Identify delayable jobs
curl -X POST http://localhost:8000/jobs/prioritize \
  -H "Content-Type: application/json" \
  -d '{"jobs":[...]}'
```

### Example 2: Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Make scaling decision
response = requests.post(
    f"{BASE_URL}/decide/scaling",
    json={
        "namespace": "default",
        "deployment": "api-server",
        "current_pod_count": 2
    }
)

decision = response.json()
print(f"Action: {decision['action']}")
print(f"Carbon: {decision['carbon_cost_grams']}g")
```

## SDK / Client Libraries

Currently maintained in Python/curl. Other language SDKs can be generated from OpenAPI schema.

See `docs/openapi.yaml` for full OpenAPI specification.
