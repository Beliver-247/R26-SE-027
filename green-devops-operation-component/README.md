# Green DevOps Operation Component

Intelligent carbon-aware autoscaling and job optimization system for Kubernetes.

## Overview

The Operation Phase component predicts near-future workload, estimates carbon impact, identifies delayable jobs, and decides the optimal number of pods to scale up or down while maintaining SLA.

### Key Features

- **Workload Prediction Engine**: LSTM-based 30-second-ahead workload forecasting
- **Carbon Emission Engine**: Real-time carbon impact estimation for scaling decisions
- **Job Prioritization Engine**: Intelligent job delay scheduling for carbon reduction
- **Decision Engine**: Multi-objective optimization balancing performance and sustainability

### Technology Stack

- Python 3.9+
- Kubernetes
- Prometheus + Grafana
- FastAPI
- Docker & Terraform

## Quick Start

### Prerequisites

- Python 3.9+
- Docker
- Kubernetes cluster (local or remote)
- Prometheus for metrics collection

### Installation

```bash
# Clone repository
git clone <repo>
cd green-devops-operation-component

# Setup environment
make setup

# Run tests
make test

# Start local development
docker-compose up
```

### Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## Project Structure

```
green-devops-operation-component/
├── docs/              # Documentation
├── config/            # Configuration files
├── data/              # Datasets & collected metrics
├── models/            # Trained models & scalers
├── src/               # Core application code
├── tests/             # Unit & integration tests
├── scripts/           # Utility scripts
├── infrastructure/    # Terraform & K8s manifests
├── monitoring/        # Prometheus & Grafana configs
├── experiments/       # Research experiments
└── notebooks/         # Jupyter notebooks
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Cold Start Strategy](docs/COLD_START.md)
- [API Reference](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Development

### Running Tests

```bash
make test
```

### Training Models

```bash
python scripts/train_cold_start_models.py
```

### Local Development

```bash
docker-compose -f infrastructure/docker/docker-compose.yaml up
```

## Configuration

All configuration is in `config/` directory:
- `default.yaml`: Default configuration
- `dev.yaml`: Development overrides
- `prod.yaml`: Production overrides
- `carbon_config.yaml`: Carbon calculation parameters
- `sla_config.yaml`: SLA thresholds
- `scaling_config.yaml`: Pod scaling rules
- `job_policies.yaml`: Job prioritization rules

## License

MIT

## Contact

For questions, please open an issue or contact the research team.
# Green DevOps Operation Component

A research implementation of an intelligent carbon-aware autoscaling and job optimization system for Kubernetes.

## Overview

This component is deployed independently within each target application/system to:
- **Predict** near-future workload (next 30 seconds)
- **Estimate** carbon impact of scaling decisions
- **Identify** delayable jobs that can be delayed to reduce carbon footprint
- **Optimize** pod scaling while maintaining SLA constraints

## Key Features

- **Workload Prediction Engine**: LSTM/ARIMA-based prediction with cold-start support
- **Carbon Emission Engine**: Calculates carbon cost of scaling and savings from job delays
- **Job Prioritization Engine**: Classifies jobs and manages delayed job queue
- **Decision Engine**: Multi-objective optimization balancing carbon and performance
- **Kubernetes Integration**: Direct pod scaling via K8s API
- **Prometheus Integration**: Metrics collection and monitoring

## Quick Start

### Prerequisites
- Python 3.9+
- Kubernetes cluster access
- Prometheus instance
- Docker

### Installation

```bash
# Clone and setup
git clone <repo-url>
cd green-devops-operation-component
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download cold-start datasets
python scripts/fetch_public_datasets.py

# Train initial models
python scripts/train_cold_start_models.py
```

### Deployment

```bash
# Deploy to Kubernetes
kubectl apply -f infrastructure/k8s_manifests/

# Or use Helm
helm install operation-phase ./infrastructure/helm/ -f infrastructure/helm/values-prod.yaml
```

### Local Development

```bash
# Start full stack locally
docker-compose -f infrastructure/docker/docker-compose.yaml up

# Run tests
pytest tests/ -v

# Run API
python -m src.api.main
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and component interactions
- [Deployment Guide](docs/DEPLOYMENT.md) - Installation and configuration
- [Cold Start Strategy](docs/COLD_START.md) - Initial deployment without historical data
- [API Reference](docs/API.md) - REST API endpoints
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## Project Structure

```
├── config/               # Configuration and policies
├── data/                 # Public datasets, metrics, features
├── models/               # Trained models and scalers
├── src/                  # Core application code
│   ├── shared/          # Common utilities
│   ├── data_layer/      # Data ingestion and preprocessing
│   ├── workload_prediction_engine/
│   ├── carbon_emission_engine/
│   ├── job_prioritization_engine/
│   ├── decision_engine/
│   ├── kubernetes_integration/
│   ├── metrics_layer/
│   ├── api/
│   └── background_jobs/
├── tests/               # Unit and integration tests
├── scripts/             # Utility scripts
├── infrastructure/      # Terraform, K8s, Docker configs
├── monitoring/          # Prometheus and Grafana configs
├── experiments/         # Experiment results and logs
├── notebooks/           # Research and analysis notebooks
└── logs/               # Runtime logs
```

## Configuration

All system configuration lives in `config/`:
- `default.yaml` - Default settings
- `dev.yaml` / `prod.yaml` - Environment overrides
- `carbon_config.yaml` - Carbon calculation parameters
- `sla_config.yaml` - SLA thresholds
- `scaling_config.yaml` - Pod scaling limits
- `job_policies.yaml` - Job prioritization rules

## Research Outputs

See `experiments/` for:
- Cold-start evaluation results
- Scaling strategy comparisons
- Carbon optimization metrics
- Decision impact analysis

Research papers and detailed analysis: [research_outputs/](research_outputs/)

## Contributing

For research collaboration, please refer to contribution guidelines in individual components.

## License

See LICENSE file.

## Authors

Research Project: Green DevOps Operation Phase
