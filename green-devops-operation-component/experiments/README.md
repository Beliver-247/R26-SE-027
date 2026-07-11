# Experiments Directory

This directory stores experiment results, configurations, and analysis.

## Structure

- `experiment_registry.csv` - Log of all experiments
- `cold_start_eval/` - Cold-start evaluation experiments
- `scaling_strategy_eval/` - Scaling strategy experiments
- `carbon_optimization_eval/` - Carbon optimization experiments

## Experiment Organization

Each experiment subdirectory contains:
- `exp_XXX_config.yaml` - Configuration used
- `exp_XXX_results.json` - Experiment results
- `exp_XXX_metrics.csv` - Detailed metrics
- `exp_XXX_notes.md` - Notes and analysis

## Experiment Registry

CSV format with columns:
- exp_id - Unique experiment ID
- date - Run date
- type - Experiment type
- config - Configuration file
- status - completed/failed/in_progress
- results - Link to results file
- notes - Brief description

## Examples

See individual subdirectories for example experiments:
- exp_001_cold_start_evaluation - Test cold-start model quality
- exp_002_scaling_strategies - Compare scaling strategies
- exp_003_carbon_optimization - Measure carbon reduction

## Analysis

Use Jupyter notebooks in `notebooks/` for detailed analysis of experiments.

## Adding New Experiments

1. Create directory: `exp_XXX_<description>/`
2. Add config YAML file
3. Run experiment
4. Store results JSON and metrics CSV
5. Update experiment_registry.csv
6. Add analysis notebook if needed
