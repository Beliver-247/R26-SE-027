#!/usr/bin/env python3
"""
Analyze raw CSV files to find data quality and variability
"""
import numpy as np
import pandas as pd
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import sys

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CSV_DIR = Path('data/public_datasets/fastStorage/2013-8')
OUTPUT_FILE = 'data/csv_file_analysis.npz'

def analyze_csv_file(csv_path):
    """Analyze single CSV file for CPU variability"""
    try:
        # Read with tab delimiter and handle the column header format
        df = pd.read_csv(csv_path, sep=';\t', engine='python')
        
        # Standardize column names
        df.columns = [col.strip().lower() for col in df.columns]
        
        # Find CPU column
        cpu_col = None
        for col in df.columns:
            if 'cpu usage [%]' in col or 'cpu usage' in col:
                cpu_col = col
                break
        
        if cpu_col is None:
            return None
        
        # Extract CPU values
        cpu_values = pd.to_numeric(df[cpu_col], errors='coerce')
        cpu_values = cpu_values.dropna()
        
        if len(cpu_values) < 10:
            return None
        
        # Filter to reasonable range [0, 100]
        cpu_values = cpu_values[(cpu_values >= 0) & (cpu_values <= 100)]
        
        if len(cpu_values) < 10:
            return None
        
        # Compute statistics
        mean_cpu = cpu_values.mean()
        std_cpu = cpu_values.std()
        min_cpu = cpu_values.min()
        max_cpu = cpu_values.max()
        q25 = cpu_values.quantile(0.25)
        q75 = cpu_values.quantile(0.75)
        
        # Count load levels
        low = (cpu_values < 30).sum()
        normal = ((cpu_values >= 30) & (cpu_values < 70)).sum()
        high = (cpu_values >= 70).sum()
        
        return {
            'path': str(csv_path),
            'samples': len(cpu_values),
            'mean': mean_cpu,
            'std': std_cpu,
            'min': min_cpu,
            'max': max_cpu,
            'q25': q25,
            'q75': q75,
            'low': low,
            'normal': normal,
            'high': high,
            'range': max_cpu - min_cpu,
            'has_high': high > 0,
            'has_normal': normal > 0,
            'has_variety': std_cpu > 2.0,  # 2% threshold
        }
    except Exception as e:
        return None

logger.info("Analyzing raw CSV files...")
csv_files = sorted(CSV_DIR.glob('*.csv'))
logger.info(f"Found {len(csv_files)} CSV files")

# Process files sequentially
results = []
for i, csv_path in enumerate(csv_files):
    if (i + 1) % 100 == 0:
        logger.info(f"  Analyzed {i+1}/{len(csv_files)}...")
    result = analyze_csv_file(csv_path)
    if result:
        results.append(result)

logger.info(f"Successfully analyzed {len(results)} files")

# Convert to structured array for filtering
if results:
    results_sorted = sorted(results, key=lambda x: x['std'], reverse=True)
    
    logger.info("\n" + "="*80)
    logger.info("CSV FILE QUALITY SUMMARY")
    logger.info("="*80)
    
    # Overall stats
    means = [r['mean'] for r in results]
    stds = [r['std'] for r in results]
    ranges = [r['range'] for r in results]
    has_high_count = sum(1 for r in results if r['has_high'])
    has_normal_count = sum(1 for r in results if r['has_normal'])
    has_variety_count = sum(1 for r in results if r['has_variety'])
    
    logger.info(f"\nMean CPU utilization:")
    logger.info(f"  Average: {np.mean(means):.2f}%")
    logger.info(f"  Median: {np.median(means):.2f}%")
    logger.info(f"  Range: {np.min(means):.2f}% - {np.max(means):.2f}%")
    
    logger.info(f"\nCPU variability (std):")
    logger.info(f"  Average: {np.mean(stds):.2f}%")
    logger.info(f"  Median: {np.median(stds):.2f}%")
    logger.info(f"  Range: {np.min(stds):.2f}% - {np.max(stds):.2f}%")
    
    logger.info(f"\nFile characteristics:")
    logger.info(f"  Files with HIGH load (>70%): {has_high_count}/{len(results)} ({100*has_high_count/len(results):.1f}%)")
    logger.info(f"  Files with NORMAL load (30-70%): {has_normal_count}/{len(results)} ({100*has_normal_count/len(results):.1f}%)")
    logger.info(f"  Files with variety (std>2%): {has_variety_count}/{len(results)} ({100*has_variety_count/len(results):.1f}%)")
    
    # Stratify files by quality
    high_variability = [r for r in results if r['std'] > 5.0]  # High variability
    medium_variability = [r for r in results if 2.0 <= r['std'] <= 5.0]  # Medium
    low_variability = [r for r in results if r['std'] < 2.0]  # Low
    zero_variability = [r for r in results if r['std'] == 0]  # Constant
    
    logger.info(f"\nVariability stratification:")
    logger.info(f"  High (std>5%): {len(high_variability)} files")
    logger.info(f"  Medium (2-5%): {len(medium_variability)} files")
    logger.info(f"  Low (0-2%): {len(low_variability)} files")
    logger.info(f"  Constant (0%): {len(zero_variability)} files")
    
    # Top 10 files by variability
    logger.info(f"\nTop 10 files by variability (std):")
    for i, r in enumerate(results_sorted[:10], 1):
        logger.info(f"  {i}. std={r['std']:.2f}%, mean={r['mean']:.2f}%, " +
                   f"range={r['range']:.1f}%, high={r['has_high']}, normal={r['has_normal']}")
    
    # Save analysis
    np.savez(OUTPUT_FILE,
             paths=np.array([r['path'] for r in results]),
             means=np.array([r['mean'] for r in results]),
             stds=np.array([r['std'] for r in results]),
             ranges=np.array([r['range'] for r in results]),
             has_high=np.array([r['has_high'] for r in results]),
             has_normal=np.array([r['has_normal'] for r in results]),
             has_variety=np.array([r['has_variety'] for r in results]),
             low_counts=np.array([r['low'] for r in results]),
             normal_counts=np.array([r['normal'] for r in results]),
             high_counts=np.array([r['high'] for r in results]))
    
    logger.info(f"\nAnalysis saved to {OUTPUT_FILE}")
    logger.info("="*80)
