# Monitoring Directory

Prometheus and Grafana configurations for monitoring the Green DevOps Operation Component.

## Structure

- `prometheus/` - Prometheus configuration
- `grafana/dashboards/` - Dashboard JSON files
- `grafana/provisioning/` - Grafana provisioning configs

## Prometheus Metrics

The component exports metrics on `/metrics` endpoint:
- `workload_prediction_mae` - Prediction accuracy
- `carbon_emissions_grams` - Current carbon emissions
- `scaling_decision_duration_ms` - Decision latency
- `scaled_jobs_count` - Delayed jobs count
- `pod_count_current` - Current pod count
- `pod_count_target` - Target pod count

## Grafana Dashboards

Available dashboards in `grafana/dashboards/`:
- `overview.json` - System overview
- `workload_prediction.json` - Prediction metrics
- `carbon_emissions.json` - Carbon tracking
- `system_health.json` - System health

## Setup

1. Add Prometheus data source in Grafana
2. Import dashboards from JSON files
3. Configure alerts if needed

## Customization

Edit Prometheus scrape config to match your environment.
Add custom dashboards for domain-specific metrics.
