# Carbon Evaluation Endpoint Integration Guide

## Overview

The `/carbon/evaluate` endpoint enables energy and carbon footprint analysis for workload predictions. It integrates **Engine 1** (Workload Prediction) with **Engine 2** (Carbon Emission Analysis) to provide optimization recommendations that minimize environmental impact.

## Quick Start

### Basic Usage

```bash
curl -X POST http://localhost:8000/carbon/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "system_id": "api-service",
    "predicted_cpu": 75.5,
    "predicted_load_level": "HIGH",
    "recommended_pods": 5,
    "current_pods": 3,
    "prediction_window_seconds": 30
  }'
```

## Request Schema

### Required Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `system_id` | string | - | System identifier |
| `predicted_cpu` | float | 0-100 | Predicted CPU usage percentage from Engine 1 |
| `predicted_load_level` | string | LOW/NORMAL/HIGH | Workload classification |
| `recommended_pods` | integer | 1-20 | Recommended pod count from Engine 1 |
| `current_pods` | integer | 1-20 | Currently running pods |

### Optional Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `prediction_window_seconds` | integer | > 0 | Prediction window (default: 30s) |
| `delayable_jobs` | integer | ≥ 0 | Jobs that can be deferred (Engine 3 input) |
| `workload_reduction_percent` | float | 0-100 | Max workload reduction via deferral |

## Response Schema

### Success Response (200 OK)

```json
{
  "status": "success",
  "timestamp": "2026-04-17T10:30:45Z",
  "system_id": "api-service",
  "engine_version": "2.0",
  "input": {
    "predicted_cpu": 75.5,
    "predicted_load_level": "HIGH",
    "recommended_pods": 5,
    "current_pods": 3,
    "prediction_window_seconds": 30,
    "has_job_data": false
  },
  "scenarios": [
    {
      "name": "raw_scale",
      "description": "Scale to Engine 1 recommendation (5 pods)",
      "pod_count": 5,
      "energy_kwh": 0.041667,
      "carbon_gco2": 16.67,
      "carbon_kg": 0.01667
    },
    {
      "name": "conservative",
      "description": "Conservative scaling with 10% margin",
      "pod_count": 4,
      "energy_kwh": 0.033333,
      "carbon_gco2": 13.33,
      "carbon_kg": 0.01333
    }
  ],
  "decision": {
    "recommended_action": "scale_up",
    "carbon_saving_percent": 15.0,
    "carbon_saving_gco2": 50.0,
    "reasoning": "HIGH load requires scaling up, but conservative approach saves 15% carbon"
  },
  "metadata": {
    "energy_model": {
      "energy_per_pod_kwh_per_hour": 0.5,
      "model_type": "linear_scaling",
      "assumptions": [...]
    },
    "carbon_calculator": {
      "carbon_intensity_gco2_per_kwh": 400.0,
      "carbon_intensity_description": "Moderate grid (mixed sources)"
    }
  },
  "evaluation_ms": 12.45
}
```

### Error Response (400/500)

```json
{
  "detail": "Invalid input: predicted_cpu must be 0-100, got 150.0"
}
```

## Use Cases

### 1. Scaling with Carbon Optimization

When Engine 1 recommends scaling up, use carbon evaluation to find the minimum pods needed:

```python
import requests

# Get Engine 1 prediction
e1_prediction = {
    "predicted_cpu": 80.0,
    "predicted_load_level": "HIGH",
    "recommended_pods": 6,
}

# Evaluate carbon impact
response = requests.post(
    "http://localhost:8000/carbon/evaluate",
    json={
        "system_id": "web-app",
        "predicted_cpu": e1_prediction["predicted_cpu"],
        "predicted_load_level": e1_prediction["predicted_load_level"],
        "recommended_pods": e1_prediction["recommended_pods"],
        "current_pods": 3,
    }
)

result = response.json()
action = result["decision"]["recommended_action"]
savings = result["decision"]["carbon_saving_percent"]

print(f"Recommended: {action} ({savings}% carbon savings)")
```

### 2. Job Deferral with Carbon Analysis

When Engine 3 identifies deferrable jobs, evaluate carbon savings:

```python
# Engine 3 job analysis
engine3_output = {
    "delayable_jobs": 25,
    "workload_reduction_percent": 30.0
}

# Evaluate with job deferral
response = requests.post(
    "http://localhost:8000/carbon/evaluate",
    json={
        "system_id": "batch-processor",
        "predicted_cpu": 70.0,
        "predicted_load_level": "NORMAL",
        "recommended_pods": 4,
        "current_pods": 4,
        "delayable_jobs": engine3_output["delayable_jobs"],
        "workload_reduction_percent": engine3_output["workload_reduction_percent"]
    }
)

result = response.json()
if result["decision"]["carbon_saving_percent"] > 20:
    print("High carbon savings available via job deferral!")
```

### 3. Multi-Engine Pipeline

Integrate Engine 1, Engine 2, and Engine 3 in a complete pipeline:

```python
class GreenDevOpsOrchestrator:
    """Orchestrate multi-engine optimization pipeline."""
    
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_url = api_base_url
    
    def optimize(self, system_id: str, metrics: dict):
        """
        Run complete optimization pipeline.
        
        Flow:
        1. Engine 1: Predict workload
        2. Engine 3: Identify deferrable jobs (optional)
        3. Engine 2: Evaluate carbon impact and recommend
        """
        
        # Step 1: Get Engine 1 prediction
        e1_response = requests.get(
            f"{self.api_url}/predict",
            params={"system_id": system_id}
        )
        e1_prediction = e1_response.json()["prediction"]
        
        # Step 2: Optional - Get Engine 3 job analysis
        e3_data = self._get_engine3_analysis(system_id, metrics)
        
        # Step 3: Run carbon evaluation
        carbon_request = {
            "system_id": system_id,
            "predicted_cpu": e1_prediction["predicted_cpu_percent"],
            "predicted_load_level": e1_prediction["predicted_load_level"],
            "recommended_pods": e1_prediction["recommended_pods"],
            "current_pods": metrics.get("current_pods", 1),
        }
        
        # Add Engine 3 data if available
        if e3_data:
            carbon_request.update(e3_data)
        
        # Run evaluation
        e2_response = requests.post(
            f"{self.api_url}/carbon/evaluate",
            json=carbon_request
        )
        
        decision = e2_response.json()
        
        # Apply recommendation
        self._apply_decision(system_id, decision)
        
        return decision
    
    def _get_engine3_analysis(self, system_id: str, metrics: dict):
        """Get Engine 3 job analysis if available."""
        # Placeholder for Engine 3 integration
        return None
    
    def _apply_decision(self, system_id: str, decision: dict):
        """Apply the recommended decision."""
        action = decision["decision"]["recommended_action"]
        print(f"Applying decision: {action} for {system_id}")
```

## Decision Actions

The recommendation engine returns one of these actions:

| Action | Meaning | When Used |
|--------|---------|-----------|
| `scale_up` | Increase pod count | Load is high, performance requires more resources |
| `scale_down` | Reduce pod count | Load is low, can reduce without performance impact |
| `delay_jobs` | Defer non-critical jobs | Can reduce workload significantly, carbon savings > 10% |
| `hybrid` | Scale down + defer jobs | Combines scaling and deferral for optimal carbon reduction |
| `no_action` | Keep current pods | Current pods are optimal |

## Error Handling

### Validation Errors (400)

```python
# Invalid CPU percentage
{
    "detail": "Invalid input: predicted_cpu must be 0-100, got 150.0"
}

# Invalid load level
{
    "detail": "Invalid input: predicted_load_level must be LOW/NORMAL/HIGH, got EXTREME"
}

# Invalid pod count
{
    "detail": "Invalid input: recommended_pods must be 1-20, got 0"
}
```

### Service Errors (500)

```python
try:
    response = requests.post(url, json=payload)
    if response.status_code == 500:
        print(f"Engine error: {response.json()['detail']}")
except requests.exceptions.ConnectionError:
    print("API server not reachable")
```

## Performance Considerations

- **Evaluation Time**: Typically 5-15ms (see `evaluation_ms` in response)
- **Throughput**: Can handle hundreds of evaluations per second
- **Memory**: Each evaluation uses minimal memory

Example monitoring:

```python
response = requests.post(url, json=payload)
eval_time = response.json()["evaluation_ms"]

if eval_time > 50:
    print("Warning: Slow evaluation, consider scaling API")
```

## Configuration

The carbon engine uses these constants (in `src/carbon_engine/config.py`):

```python
# Energy consumption per pod
ENERGY_PER_POD_KWH_PER_HOUR = 0.5

# Grid carbon intensity (US average)
CARBON_INTENSITY_GCO2_PER_KWH = 400.0

# Pod scaling constraints
MIN_REQUIRED_PODS = 1
MAX_PODS = 20

# Carbon optimization thresholds
CARBON_SAVING_THRESHOLD_PERCENT = 10.0
```

To customize, update these values before starting the API server.

## Examples

### Example 1: Web Service Peak Load

```json
{
  "system_id": "web-frontend",
  "predicted_cpu": 85.0,
  "predicted_load_level": "HIGH",
  "recommended_pods": 8,
  "current_pods": 4,
  "prediction_window_seconds": 30
}
```

**Response**: `scale_up` (necessary for performance)

### Example 2: Batch Processing Job

```json
{
  "system_id": "data-processor",
  "predicted_cpu": 60.0,
  "predicted_load_level": "NORMAL",
  "recommended_pods": 4,
  "current_pods": 4,
  "prediction_window_seconds": 30,
  "delayable_jobs": 20,
  "workload_reduction_percent": 25.0
}
```

**Response**: `delay_jobs` or `hybrid` (can defer work for carbon savings)

### Example 3: Off-Peak Operation

```json
{
  "system_id": "background-tasks",
  "predicted_cpu": 20.0,
  "predicted_load_level": "LOW",
  "recommended_pods": 1,
  "current_pods": 3,
  "prediction_window_seconds": 30
}
```

**Response**: `scale_down` (reduce unnecessary pods)

## Integration with Dashboards

The carbon evaluation output integrates with monitoring dashboards:

```javascript
// Example frontend code
async function updateCarbonMetrics(systemId) {
  const response = await fetch('/carbon/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      system_id: systemId,
      predicted_cpu: currentMetrics.cpu,
      predicted_load_level: currentMetrics.loadLevel,
      recommended_pods: engine1Prediction.pods,
      current_pods: kubernetesCluster.podCount
    })
  });
  
  const carbon_data = await response.json();
  
  // Display on dashboard
  updateChart('carbon-scenarios', carbon_data.scenarios);
  updateRecommendation('decision', carbon_data.decision);
  updateMetadata('carbon-model', carbon_data.metadata);
}
```

## FAQ

**Q: What if Engine 2 is not initialized?**
A: The endpoint will attempt lazy initialization on first call. If the carbon_engine module is not available, you'll get a 503 error.

**Q: Can I use this without Engine 1 predictions?**
A: Yes! Provide the required fields directly. You don't need to run Engine 1 first.

**Q: How often should I call this endpoint?**
A: Typically once per prediction cycle (e.g., every 30 seconds for real-time systems).

**Q: What's the difference between scenarios?**
A: Different scenarios represent various scaling strategies. Compare their carbon_gco2 values to see which minimizes environmental impact.

---

For more details, see the [API Documentation](./API_REFERENCE.md) and [Configuration Guide](./CONFIG_GUIDE.md).
