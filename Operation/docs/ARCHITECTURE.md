# Architecture

## System Overview

The Green DevOps Operation Component is a self-contained, per-deployment system that runs independently within each target application. It continuously monitors workload, predicts future demand, estimates carbon impact, identifies delayable jobs, and makes optimal scaling decisions.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     REST API Layer (FastAPI)                     │
│             Prediction / Decision / Admin Endpoints             │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Decision Engine                             │
│  • Multi-objective optimization                                 │
│  • Constraint validation (SLA, resources)                       │
│  • Final scaling decision making                                │
└─────────────────────────────────────────────────────────────────┘
      ▲                       ▲                       ▲
      │                       │                       │
┌─────┴──────┐    ┌──────────┴──────┐    ┌──────────┴──────┐
│  Workload   │    │   Carbon       │    │   Job           │
│  Prediction │    │   Emission     │    │   Prioritization│
│  Engine     │    │   Engine       │    │   Engine        │
└────┬────────┘    └────┬───────────┘    └────┬────────────┘
     │                  │                      │
     └──────────────────┴──────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────┴────────┐         ┌──────────┴──────┐
│  Data Layer    │         │  K8s Integration│
│  └─ Ingestion  │         │  └─ Scaling     │
│  └─ Preprocess │         │  └─ Monitoring  │
│  └─ Features   │         └─────────────────┘
└────┬───────────┘
     │
     ├─ Prometheus (metrics)
     ├─ Kubernetes (cluster state)
     └─ Public datasets (cold-start)
```

## Three Engine Design

### 1. Workload Prediction Engine
**Purpose**: Predict near-future workload (next 30 seconds)

**Workflow**:
- Collects historical pod metrics from Prometheus
- Extracts temporal features (time of day, day of week)
- Uses LSTM or ARIMA model for prediction
- Cold-start: Uses pre-trained model on public datasets
- Continuous: Retrains on collected live data periodically

**Output**: Predicted CPU/memory demand, pod count needed

### 2. Carbon Emission Engine
**Purpose**: Estimate carbon impact of scaling decisions

**Workflow**:
- Maps resource usage to carbon emissions (gCO2e)
- Considers energy source mix and PUE factors
- Calculates scale-up carbon cost
- Estimates carbon savings from delaying jobs
- Compares scenarios

**Output**: Carbon cost (gCO2e) for each scaling scenario

### 3. Job Prioritization Engine
**Purpose**: Identify delayable jobs to reduce carbon footprint

**Workflow**:
- Classifies jobs by urgency/SLA
- Identifies jobs that can be delayed
- Manages delayed job queue
- Schedules release when load drops

**Output**: List of delayable jobs, delayed job queue state

## Decision Engine

The Decision Engine orchestrates all three engines:

1. **Predict** future workload (next 30s)
2. **Estimate** pods needed to satisfy prediction
3. **Calculate** carbon cost of scaling up
4. **Identify** delayable jobs
5. **Calculate** carbon savings from delaying jobs
6. **Compare** scenarios:
   - Scale up + keep all jobs running
   - Scale up + delay non-critical jobs
   - Don't scale + delay jobs
   - Scale down if load drops
7. **Choose** optimal action that balances:
   - SLA compliance
   - Carbon footprint
   - Cost
8. **Execute** decision via Kubernetes API

## Data Flow

```
Prometheus Metrics
       ↓
    [Data Layer: Ingestion & Preprocessing]
       ↓
[Feature Engineering]
       ↓
┌──────────────────────────────────────┐
│  Workload Predictor → Prediction     │
│  Carbon Engine → Carbon Cost         │
│  Job Prioritizer → Delayable Jobs    │
└──────────────────────────────────────┘
       ↓
 [Decision Engine]
       ↓
    Scaling Decision (scale up/down/none)
       ↓
 [K8s Integration] → kubectl apply
       ↓
  Kubelet Updates Deployment
       ↓
  Pods Created/Destroyed
```

## Cold-Start Strategy

**Day 1**: No historical data available
- Use pre-trained models from public workload datasets
- Load generic carbon rates and SLA patterns
- Monitor and collect real metrics

**Days 1-7**: Collecting first week of data
- Predictor: Uses public model + real metrics for validation
- Carbon engine: Uses regional carbon rates
- Job prioritizer: Uses job labels from deployment

**Day 7+**: Retraining phase
- Sufficient historical data collected
- Fine-tune predictor on real workload
- Validate carbon assumptions
- Update job prioritization rules

## Configuration Management

All configuration in `config/` YAML files:
- `default.yaml`: Base configuration
- `dev.yaml` / `prod.yaml`: Environment overrides
- `carbon_config.yaml`: Carbon calculation parameters
- `sla_config.yaml`: SLA thresholds and constraints
- `scaling_config.yaml`: Pod scaling limits and policies
- `job_policies.yaml`: Job delay and priority rules

## Monitoring & Observability

**Prometheus Integration**:
- Exports metrics on `/metrics` endpoint
- Metrics: prediction accuracy, carbon cost, scaling decisions, SLA compliance

**Grafana Dashboards**:
- Workload vs Prediction (accuracy)
- Carbon emissions over time
- Job delay impact
- Scaling decisions history
- System health

**Decision Logging**:
- All decisions logged with:
  - Prediction
  - Carbon cost
  - Delayed jobs
  - Final action
  - Rationale

## Performance Requirements

- **Prediction latency**: < 100ms
- **Decision latency**: < 500ms
- **Scaling operation**: Executed within 5 seconds
- **Metric collection**: Every 30 seconds
- **Retraining**: Once per 24 hours

## Scalability

- Per-deployment component: Each system runs independently
- No centralized state: Runs on single machine/container
- Minimal dependencies: Prometheus + K8s API
- Memory: ~500MB for models + caching
- CPU: ~1 core during normal operations

## Security Considerations

- K8s API authentication via ServiceAccount
- RBAC: Only can patch deployment replicas
- Configuration: Stored in K8s ConfigMaps/Secrets
- API: Optional authentication/rate limiting
- Metrics: No sensitive data exposed

## Extensions and Future Work

- Multi-region carbon tracking
- Cost optimization integration
- Federated learning for improved predictions
- Real-time job dependency analysis
- Advanced scheduling policies
