# Notebooks Directory

Jupyter notebooks for research, analysis, and exploration.

## Available Notebooks

- `exploratory_analysis.ipynb` - Data exploration and visualization
- `model_development.ipynb` - Model building and experimentation
- `cold_start_evaluation.ipynb` - Cold-start model evaluation
- `decision_analysis.ipynb` - Decision impact analysis

## Running Notebooks

```bash
# Install Jupyter
pip install jupyter notebook

# Start Jupyter server
jupyter notebook

# Navigate to notebooks/ directory and select notebook

# Or run specific notebook
jupyter notebook notebooks/exploratory_analysis.ipynb
```

## Creating New Notebooks

Create notebook for:
- New research experiments
- Algorithm exploration
- Performance analysis
- Visualization and reporting

Name convention: `{topic_name}.ipynb`

## Best Practices

1. Include markdown documentation
2. Add comments explaining analysis
3. Save outputs and figures
4. Version control notebook json (or use `.ipynb` format)
5. Include data sources and parameters

## Converting to Python Scripts

Convert notebook to Python for production:
```bash
jupyter nbconvert --to python notebooks/exploratory_analysis.ipynb --output scripts/analysis.py
```

## Sharing Results

Export notebooks as HTML for sharing:
```bash
jupyter nbconvert --to html notebooks/exploratory_analysis.ipynb --output exploratory_analysis.html
```
