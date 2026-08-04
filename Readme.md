# Green DevOps – Energy Efficient CI/CD Pipeline

**Research ID:** R26-SE-027  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT)  
**Specialization:** Software Engineering

## Overview

Green DevOps is a research project focused on improving the energy efficiency of modern CI/CD pipelines. Traditional DevOps pipelines are mainly optimized for speed and automation, but they often ignore energy consumption, resource wastage, and carbon emissions.

This project proposes an intelligent, sustainability-aware CI/CD framework that optimizes the **release**, **deployment**, **operation**, and **monitoring** stages of software delivery. The goal is to reduce unnecessary builds, tests, deployments, resource usage, and carbon emissions while maintaining software quality and service-level performance.

## Problem Statement

Modern cloud-native systems and CI/CD pipelines are growing rapidly. However, most pipelines still perform full builds, full test executions, and deployments even for small code changes. This creates unnecessary computational overhead, increases cloud infrastructure usage, and contributes to higher carbon emissions.

Key problems addressed by this research include:

- Full builds and tests triggered by minor code changes
- Lack of visibility into energy usage and carbon emissions
- Deployment decisions made without considering carbon intensity or energy cost
- Reactive resource scaling that causes resource wastage
- Limited sustainability-focused monitoring and analytics in DevOps workflows

## Proposed Solution

The proposed solution is an energy-efficient CI/CD pipeline framework that introduces intelligent optimization across four main components:

1. **Release Stage Optimization**
2. **Deployment Stage Optimization**
3. **Operation Stage Optimization**
4. **Monitoring and Sustainability Analytics**

Together, these components help reduce energy usage, improve resource efficiency, and provide better visibility into the environmental impact of CI/CD activities.

## System Components

### 1. Release Stage Component

The release component focuses on reducing unnecessary builds and test executions in the CI/CD pipeline.

#### Main Features

- Change Impact Analysis
- Directed Acyclic Graph (DAG) based dependency mapping
- Selective build execution
- Selective test execution
- Jenkins-based CI/CD pipeline automation
- Release metrics submission to the GreenDevOps dashboard

#### Technologies Used

- Jenkins Pipeline
- Groovy
- Maven
- GitHub
- Python
- REST API
- JSON
- Flask dashboard
- SQLite database

#### Expected Impact

This component reduces computational overhead by building and testing only the affected modules instead of executing the entire pipeline for every commit.

---

### 2. Deployment Stage Component

The deployment component focuses on measuring deployment-related energy consumption and carbon emissions, then using that information to support smarter deployment decisions.

#### Main Features

- Deployment energy profiling
- CPU and memory usage monitoring
- Energy consumption calculation in kWh
- Carbon emission estimation
- Live grid carbon intensity integration
- AI-based deployment timing and strategy recommendation

#### Main Modules

- `profiler.py` – Measures CPU and memory usage
- `energy_calculator.py` – Converts resource usage into kWh
- `carbon_api.py` – Fetches live grid carbon intensity
- `carbon_calculator.py` – Converts kWh into CO₂ emissions
- `db_sync.py` – Saves deployment energy and carbon data to the database

#### Expected Impact

This component helps identify the carbon cost of each deployment and supports more sustainable deployment scheduling.

---

### 3. Operation Stage Component

The operation component focuses on intelligent resource management during system runtime.

#### Main Features

- AI workload prediction
- Carbon-aware optimization
- Job prioritization
- Smart autoscaling decisions
- SLA-aware resource allocation
- Kubernetes-based scaling support

#### Technologies Used

- Kubernetes
- Oracle Cloud Infrastructure
- Python
- LSTM model
- Prometheus

#### Expected Impact

This component reduces resource wastage and operational cost while maintaining service-level performance.

---

### 4. Monitor Stage Component

The monitor component provides sustainability-focused observability for the CI/CD pipeline.

#### Main Features

- Stage-level resource monitoring
- Energy consumption estimation
- Carbon emission estimation
- Statistical anomaly detection
- Isolation Forest based anomaly detection prototype
- Sustainability Analyst Assistant
- Interactive analytics dashboard
- Historical sustainability insights

#### Expected Impact

This component improves visibility into the environmental impact of CI/CD pipelines and helps teams identify abnormal energy or carbon emission patterns.

## High-Level Architecture

The system is designed around a CI/CD pipeline integrated with four sustainability-focused stages:

- **Release Optimizer** – Analyzes code changes and reduces unnecessary builds/tests
- **Deployment Optimizer** – Profiles deployments and estimates carbon emissions
- **Operation Optimizer** – Predicts workload and optimizes runtime resource usage
- **Monitor Optimizer** – Tracks resource usage, detects anomalies, and provides sustainability insights

The system integrates with tools such as Jenkins, Docker, Kubernetes, Prometheus, SQLite/MongoDB Atlas, and external carbon intensity APIs.

## Research Environment Setup

The research environment uses an Oracle Cloud Free Tier instance as a public jump server and a local Lubuntu laptop as the main server environment.

### Environment Components

- **Admin PC / Client** – Used to access the environment remotely
- **Oracle Cloud Free Tier Instance** – Acts as the jump server / bastion host
- **Lubuntu Laptop** – Acts as the local server running required services
- **Reverse SSH Tunnel** – Exposes the local server through the Oracle public IP

This setup allows external access to the local research server while keeping the main workload on the Lubuntu machine.

## Current Progress

### Completed for PP1

- Release Component
  - Change Impact Analyzer
  - Selective Build Execution
  - Selective Test Execution

- Deployment Component
  - Energy Profiler
  - Deployment Comparator

- Operation Component
  - Future Workload Prediction
  - Pod Scaling Engine

- Monitor Component
  - Monitoring Framework
  - Statistical Anomaly Detection
  - Isolation Forest Prototype

### Planned for PP2

- Carbon emission-aware AI model for build location suggestion
- AI decision engine for deployment optimization
- Job prioritization and testing completion
- LLM-based Sustainability Analyst Assistant

### Final Phase

- Fine-tune all components
- Integrate the complete system
- Improve the AI models and sustainability analytics
- Validate the system using experimental results

## Project Team

| Student ID | Name | Component |
|---|---|---|
| IT22110084 | Mendis J.D.L. | Release Stage Component |
| IT22149930 | Rathnayake D.M.B.H. | Deploy Stage Component |
| IT22281432 | M.P.M Thassara | Operation Stage Component |
| IT22189776 | Kodithuwakku I.P. | Monitor Stage Component |

## Expected Outcomes

The expected outcomes of this research include:

- Reduced unnecessary CI/CD pipeline executions
- Lower energy consumption during build, test, deployment, and operation stages
- Better carbon emission visibility across the software delivery lifecycle
- Improved resource utilization in cloud-native environments
- Sustainability-aware decision-making for DevOps teams
- A monitoring dashboard for energy, carbon, and anomaly insights

## Future Enhancements

Potential improvements for the project include:

- Integration with real-time carbon intensity APIs
- Advanced AI-based deployment scheduling
- Fine-tuned workload prediction models
- Support for more CI/CD platforms
- More detailed carbon emission reporting
- LLM-based recommendations for sustainable DevOps improvements
- Full integration with cloud-native observability tools

## Repository Structure

The final repository structure may follow the layout below:

```text
green-devops-energy-efficient-cicd/
├── release-component/
│   ├── impact-analyzer/
│   ├── selective-build/
│   └── selective-test/
├── deployment-component/
│   ├── profiler.py
│   ├── energy_calculator.py
│   ├── carbon_api.py
│   ├── carbon_calculator.py
│   └── db_sync.py
├── operation-component/
│   ├── workload-prediction/
│   ├── carbon-optimization/
│   └── autoscaling-controller/
├── monitor-component/
│   ├── resource-monitoring/
│   ├── anomaly-detection/
│   ├── sustainability-assistant/
│   └── dashboard/
├── docs/
├── README.md
└── LICENSE
```

## How to Use This Repository

1. Clone the repository:

```bash
git clone https://github.com/Beliver-247/R26-SE-027
```

2. Navigate to the required component:

```bash
cd release-component
```

3. Follow the setup instructions provided inside each component directory.

> Note: Each component may have its own dependencies, configuration files, and execution steps.

## License

This project is developed for academic research purposes under Sri Lanka Institute of Information Technology.

## Acknowledgement

This research is conducted as part of the Software Engineering specialization at SLIIT. The project aims to contribute toward more sustainable software engineering and greener DevOps practices.
