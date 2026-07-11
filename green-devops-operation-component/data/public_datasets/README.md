# Public Datasets

This directory contains public workload datasets used for cold-start model training.

## Available Datasets

### Workload Traces

- `workload_traces_azure.csv` - Azure workload patterns (when downloaded)
- `workload_traces_google.csv` - Google cluster traces (when downloaded)
- `workload_traces_nist.csv` - NIST benchmark patterns (when downloaded)

Columns: timestamp, pod_count, cpu_utilization, memory_utilization

### Energy Profiles

- `energy_profiles_datacenter.csv` - Energy consumption baselines
- `energy_profiles_pue.csv` - PUE factor variations

Columns: power_source, region, co2_intensity_grams_per_kwh, seasonality

## Downloading Datasets

```bash
python scripts/fetch_public_datasets.py
```

This script:
- Fetches datasets from public repositories
- Validates data integrity
- Stores locally in this directory
- Generates summary statistics

## File Format

All datasets are CSV format with headers. Encoding: UTF-8

## Usage

See `feature_engineering/workload_features.py` for dataset loading and preprocessing.

## Attribution

- Azure: Microsoft Research
- Google: Google Cluster Workload Traces
- NIST: National Institute of Standards and Technology
