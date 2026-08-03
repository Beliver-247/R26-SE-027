#!/usr/bin/env python3
"""
Test Engine 1 runtime mode transition.

Demonstrates cold-start → runtime mode transition when 12 records are collected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src/workload_prediction_engine'))

from live_predictor import LivePredictor

print('Testing mode transition: cold_start -> runtime\n')

# Create predictor in mock mode
predictor = LivePredictor(
    system_id='mode_transition_test',
    use_mock=True,
    runtime_store_dir='data/runtime_metrics_test'
)

# Clear any previous data
predictor.clear_runtime_history()

print('Running predictions until mode transitions...\n')

for cycle in range(20):
    # Get current info before prediction
    info_before = predictor.get_mode_info()
    mode_before = info_before['current_mode']
    
    # Execute prediction
    output = predictor.predict_next_window()
    
    # Get current info after prediction
    info_after = predictor.get_mode_info()
    mode_after = info_after['current_mode']
    records = info_after['record_count']
    
    # Print cycle info
    print(f'Cycle {cycle+1:2d}: Records={records:2d}, Mode={mode_after:10s}, '
          f'CPU={output.predicted_cpu:6.2f}%, '
          f'Load={output.predicted_load_level:6s}', end='')
    
    # Highlight mode transition
    if mode_before != mode_after:
        print(f' <- MODE TRANSITION: {mode_before} -> {mode_after}')
    else:
        print()
    
    # Stop after mode transition
    if mode_after == 'runtime':
        print(f'\n✓ Mode transition successful at cycle {cycle+1}')
        print(f'✓ Now using real runtime data for prediction\n')
        
        # Run a few more cycles in runtime mode
        print('Running 5 more cycles in runtime mode:\n')
        for i in range(5):
            output = predictor.predict_next_window()
            info = predictor.get_mode_info()
            print(f'  Cycle {cycle+2+i}: Records={info["record_count"]}, '
                  f'CPU={output.predicted_cpu:6.2f}%, '
                  f'Load={output.predicted_load_level:6s}')
        
        break

# Final summary
print('\nFinal Status:')
final_info = predictor.get_mode_info()
print(f'  Mode: {final_info["current_mode"]}')
print(f'  Total Records: {final_info["record_count"]}')
print(f'  Retraining Ready: {final_info["retraining_ready"]}')
print(f'  Mode Transitions: {final_info["mode_transitions"]}')
