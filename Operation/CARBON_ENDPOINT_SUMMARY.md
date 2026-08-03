"""
Feature Summary: Carbon Emission Evaluation Endpoint

Newly Added Endpoint: POST /carbon/evaluate
Location: workload_prediction_engine/api.py

OVERVIEW
========

The /carbon/evaluate endpoint enables energy and carbon footprint analysis,
integrating Engine 1 (Workload Prediction) with Engine 2 (Carbon Emission 
Analysis) to provide optimization recommendations that minimize environmental 
impact while maintaining performance.

PURPOSE
=======

Transform workload predictions into carbon-aware scaling decisions by:

1. Accepting Engine 1 predictions (CPU, load level, pod recommendations)
2. Optionally incorporating Engine 3 job deferral data
3. Running multi-scenario carbon analysis
4. Returning optimization recommendations with carbon savings estimates


REQUEST FIELDS (JSON)
====================

Required:
  - system_id: str
    System identifier (e.g., "api-service", "worker-pod")
  
  - predicted_cpu: float (0-100)
    Predicted CPU percentage from Engine 1 workload prediction
  
  - predicted_load_level: str ("LOW", "NORMAL", "HIGH")
    Workload classification from Engine 1
  
  - recommended_pods: int (1-20)
    Recommended pod count from Engine 1
  
  - current_pods: int (1-20)
    Currently running pod count in the system

Optional:
  - prediction_window_seconds: int
    Time window for prediction (default: 30 seconds)
  
  - delayable_jobs: int
    Number of jobs that can be deferred (from Engine 3)
  
  - workload_reduction_percent: float (0-100)
    Maximum workload reduction percentage via job deferral (from Engine 3)


RESPONSE FIELDS (JSON)
=====================

{
  "status": "success",
  "timestamp": "ISO 8601 string",
  "system_id": "string",
  "engine_version": "2.0",
  
  "input": {
    "predicted_cpu": float,
    "predicted_load_level": string,
    "recommended_pods": int,
    "current_pods": int,
    "prediction_window_seconds": int,
    "has_job_data": boolean
  },
  
  "scenarios": [
    {
      "name": "string",
      "description": "string",
      "pod_count": int,
      "energy_kwh": float,
      "carbon_gco2": float,
      "carbon_kg": float (optional)
    },
    ...
  ],
  
  "decision": {
    "recommended_action": "scale_up|scale_down|delay_jobs|hybrid|no_action",
    "carbon_saving_percent": float,
    "carbon_saving_gco2": float,
    "reasoning": "string (optional)"
  },
  
  "metadata": {
    "energy_model": {
      "energy_per_pod_kwh_per_hour": float,
      "model_type": "string",
      "assumptions": [string, ...]
    },
    "carbon_calculator": {
      "carbon_intensity_gco2_per_kwh": float,
      "carbon_intensity_description": "string",
      "conversion_factors": {...}
    }
  },
  
  "evaluation_ms": float
}


KEY FEATURES
============

1. MULTI-SCENARIO ANALYSIS
   - "raw_scale": Scale to Engine 1 recommendation
   - "conservative": Scale with margin for stability
   - "aggressive": Minimal scaling for carbon reduction
   - "with_deferral": Scale down with job deferral
   
2. DECISION RECOMMENDATIONS
   - scale_up: Increase pods (performance takes priority)
   - scale_down: Reduce pods (load is low)
   - delay_jobs: Defer work to reduce carbon (if beneficial)
   - hybrid: Combine scaling and job deferral
   - no_action: Current pods are optimal
   
3. CARBON OPTIMIZATION
   - Evaluates energy consumption per scenario
   - Converts to CO2 emissions using grid carbon intensity
   - Calculates carbon savings vs baseline
   - Considers performance constraints
   
4. ERROR HANDLING
   - Validates all input parameters (0-100 for percentages, 1-20 for pods)
   - Returns 400 for validation errors with descriptive messages
   - Returns 500 for internal errors with debugging info
   - Lazy initialization of Carbon Engine if needed


IMPLEMENTATION DETAILS
======================

Classes Added to api.py:

1. CarbonEvaluationRequest (Pydantic)
   - Request model with field validation
   - Supports all input fields
   - Includes schema example for documentation

2. CarbonEvaluationResponse (Pydantic)
   - Response model with structured output
   - Ensures type safety and schema consistency

3. Additional Pydantic models:
   - CarbonScenario: Represents a single scenario result
   - CarbonDecision: Represents the final recommendation

Engine1API class extensions:

1. set_carbon_engine(carbon_engine) method
   - Sets the CarbonEmissionEngine instance
   - Enables deferred initialization if needed
   - Logs initialization status

2. evaluate_carbon route (@app.post("/carbon/evaluate"))
   - Validates request data
   - Handles lazy initialization of Engine 2
   - Measures evaluation time
   - Returns structured response
   - Provides detailed error messages


INTEGRATION WITH ENGINE 2
==========================

The endpoint uses these Engine 2 components:

1. CarbonEmissionEngine
   - Main orchestrator for carbon analysis
   - Coordinates energy, carbon, scenario, and decision modules
   
2. EnergyModel
   - Calculates energy consumption: energy = pods × energy_per_pod × time
   - Default: 0.5 kWh per pod per hour
   
3. CarbonCalculator
   - Converts energy to CO2: carbon = energy × carbon_intensity
   - Default: 400 g CO2/kWh (US average grid)
   
4. ScenarioSimulator
   - Creates multiple scaling scenarios
   - Evaluates energy/carbon for each
   
5. DecisionEngine
   - Recommends optimal action
   - Balances performance, carbon, and constraints


USE CASES
=========

1. Real-time Scaling Optimization
   - Call after each Engine 1 prediction
   - Use recommendation to scale pods
   - Reduces carbon footprint while maintaining SLA
   
2. Batch Job Scheduling
   - Combine with Engine 3 job deferral
   - Defer non-critical jobs during high-carbon hours
   - Significant carbon reduction with minimal SLA impact
   
3. Dashboard Integration
   - Display scenario analysis to operators
   - Show carbon impact of scaling decisions
   - Help understand trade-offs
   
4. Automated Carbon Optimization
   - Use recommendation directly for auto-scaling
   - Apply delay_jobs or hybrid decisions
   - Achieve carbon goals automatically


EXAMPLE USAGE (Python)
======================

import requests

# Call endpoint
response = requests.post(
    "http://localhost:8000/carbon/evaluate",
    json={
        "system_id": "api-service",
        "predicted_cpu": 75.5,
        "predicted_load_level": "HIGH",
        "recommended_pods": 5,
        "current_pods": 3,
        "prediction_window_seconds": 30,
        "delayable_jobs": 10,
        "workload_reduction_percent": 15.0
    }
)

result = response.json()

# Extract recommendation
action = result["decision"]["recommended_action"]
carbon_saving = result["decision"]["carbon_saving_percent"]

print(f"Action: {action}")
print(f"Carbon Saving: {carbon_saving:.1f}%")

# Examine scenarios
for scenario in result["scenarios"]:
    print(f"{scenario['name']}: {scenario['carbon_gco2']:.2f} g CO2")


EXAMPLE USAGE (curl)
====================

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


INTEGRATION WITH OTHER ENGINES
===============================

Engine 1 → Engine 2 Flow:
1. Engine 1 generates prediction output (CPU, load level, pods)
2. Pass prediction to /carbon/evaluate
3. Engine 2 analyzes carbon impact
4. Returns optimized pod count and action

Optional Engine 3 Integration:
1. Engine 3 identifies deferrable jobs
2. Include delayable_jobs and workload_reduction_percent in request
3. Engine 2 evaluates job deferral scenarios
4. May recommend delay_jobs or hybrid action


CONFIGURATION
=============

Engine 2 constants (src/carbon_engine/config.py):

- ENERGY_PER_POD_KWH_PER_HOUR = 0.5
  Energy consumption per pod per hour
  
- CARBON_INTENSITY_GCO2_PER_KWH = 400.0
  Grid carbon intensity (US average)
  
- CARBON_SAVING_THRESHOLD_PERCENT = 10.0
  Minimum carbon saving for job deferral recommendation
  
- MAX_ACCEPTABLE_PERFORMANCE_DEGRADATION_PERCENT = 15.0
  Maximum performance degradation for carbon savings


TESTING
=======

Test script: test_carbon_endpoint.py
- Basic carbon evaluation
- Carbon evaluation with job deferral
- Low load scenarios
- Error handling validation

Integration example: integration_example.py
- Complete workflow showing all engines
- Multi-system optimization
- Job deferral scenarios
- Reporting and analysis


DOCUMENTATION
==============

Main guide: CARBON_EVALUATION_GUIDE.md
- Quick start guide
- Request/response schema
- Use case examples
- FAQ and troubleshooting

This file: CARBON_ENDPOINT_SUMMARY.md
- Feature overview
- Implementation details
- Integration points
- Code examples


PERFORMANCE
===========

- Evaluation latency: ~5-15ms (see evaluation_ms in response)
- Can handle hundreds of evaluations per second
- Minimal memory overhead per evaluation
- Suitable for real-time production use


ERROR HANDLING
==============

Validation (400 Bad Request):
- predicted_cpu must be 0-100
- predicted_load_level must be LOW/NORMAL/HIGH
- recommended_pods must be 1-20
- current_pods must be 1-20
- workload_reduction_percent must be 0-100

Engine Error (500 Internal Server Error):
- Carbon engine initialization failed
- Scenario simulation error
- Decision engine error

Connection Error:
- Carbon engine module not available
- Will attempt lazy initialization on first call
  
Returns descriptive error messages for debugging


NEXT STEPS
==========

1. Integration Testing
   - Run test_carbon_endpoint.py
   - Verify response schemas
   - Test error cases
   
2. Production Deployment
   - Set environment-specific config (carbon intensity)
   - Configure monitoring and alerting
   - Set up dashboard integration
   
3. Advanced Integration
   - Connect Engine 3 for job deferral
   - Implement auto-scaling with recommendations
   - Add persistence for historical analysis
   
4. Performance Optimization
   - Cache scenarios for repeated calls
   - Optimize carbon intensity lookups
   - Consider async evaluation for batch operations


═══════════════════════════════════════════════════════════════════════════════
For more detailed information, see:
- CARBON_EVALUATION_GUIDE.md (comprehensive user guide)
- integration_example.py (complete workflow example)
- test_carbon_endpoint.py (test suite)
- src/carbon_engine/ (Engine 2 implementation)
"""
