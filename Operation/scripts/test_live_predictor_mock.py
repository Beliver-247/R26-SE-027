#!/usr/bin/env python3
"""Quick test of LivePredictor with mock mode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))

from live_predictor import LivePredictor

print('Testing LivePredictor with mock mode...\n')

# Create live predictor in mock mode
predictor = LivePredictor(
    system_id='test_pod',
    use_mock=True,
    runtime_store_dir='data/runtime_metrics_test'
)

print('Running 5 prediction cycles...\n')

for cycle in range(5):
    print(f'Cycle {cycle+1}:')
    
    # Execute prediction
    output = predictor.predict_next_window()
    
    # Print results
    print(f'  CPU: {output.predicted_cpu:.2f}%')
    print(f'  Load: {output.predicted_load_level}')
    print(f'  Pods: {output.recommended_pods}')
    print(f'  Source: {output.data_source}')
    print()

# Print mode info
info = predictor.get_mode_info()
print('Final Status:')
print(f'  Mode: {info["current_mode"]}')
print(f'  Records: {info["record_count"]}')
print(f'  Retrain Ready: {info["retraining_ready"]}')
