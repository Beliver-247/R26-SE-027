"""
Data quality analysis and validation for combined workload datasets.
Companion script to combine_workload_datasets.py
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkloadDataValidator:
    """Validate and analyze workload dataset quality."""
    
    def __init__(self, data_path: str):
        """
        Initialize validator.
        
        Args:
            data_path: Path to CSV file
        """
        self.data_path = Path(data_path)
        self.df = None
        self.quality_report = {}
    
    def load_data(self) -> pd.DataFrame:
        """Load dataset from CSV."""
        if not self.data_path.exists():
            logger.error(f"File not found: {self.data_path}")
            raise FileNotFoundError(f"File not found: {self.data_path}")
        
        logger.info(f"Loading data from: {self.data_path}")
        self.df = pd.read_csv(self.data_path)
        logger.info(f"Loaded {len(self.df)} records")
        return self.df
    
    def validate_columns(self) -> Dict:
        """Validate required columns exist."""
        required_columns = ['timestamp', 'cpu', 'memory', 'system_id']
        
        report = {
            'has_all_columns': True,
            'missing_columns': [],
            'extra_columns': []
        }
        
        for col in required_columns:
            if col not in self.df.columns:
                report['has_all_columns'] = False
                report['missing_columns'].append(col)
        
        for col in self.df.columns:
            if col not in required_columns:
                report['extra_columns'].append(col)
        
        return report
    
    def validate_data_types(self) -> Dict:
        """Validate data types."""
        report = {
            'timestamp_type': str(self.df['timestamp'].dtype),
            'cpu_type': str(self.df['cpu'].dtype),
            'memory_type': str(self.df['memory'].dtype),
            'system_id_type': str(self.df['system_id'].dtype),
        }
        
        return report
    
    def validate_null_values(self) -> Dict:
        """Check for null and NaN values."""
        report = {
            'total_rows': len(self.df),
            'null_counts': self.df.isnull().sum().to_dict(),
            'has_nulls': self.df.isnull().any().any()
        }
        
        return report
    
    def validate_numeric_ranges(self) -> Dict:
        """Validate numeric column ranges."""
        report = {
            'cpu': {
                'min': float(self.df['cpu'].min()),
                'max': float(self.df['cpu'].max()),
                'mean': float(self.df['cpu'].mean()),
                'std': float(self.df['cpu'].std()),
                'negative_values': (self.df['cpu'] < 0).sum(),
                'values_over_100': (self.df['cpu'] > 100).sum()
            },
            'memory': {
                'min': float(self.df['memory'].min()),
                'max': float(self.df['memory'].max()),
                'mean': float(self.df['memory'].mean()),
                'std': float(self.df['memory'].std()),
                'negative_values': (self.df['memory'] < 0).sum(),
                'values_over_100': (self.df['memory'] > 100).sum()
            },
            'timestamp': {
                'min': float(self.df['timestamp'].min()),
                'max': float(self.df['timestamp'].max()),
                'mean': float(self.df['timestamp'].mean()),
                'is_sorted': (self.df['timestamp'].diff()[1:] >= 0).all()
            }
        }
        
        return report
    
    def validate_system_distribution(self) -> Dict:
        """Validate system ID distribution."""
        system_counts = self.df['system_id'].value_counts().to_dict()
        
        report = {
            'unique_systems': self.df['system_id'].nunique(),
            'system_counts': system_counts,
            'min_records_per_system': min(system_counts.values()),
            'max_records_per_system': max(system_counts.values()),
            'avg_records_per_system': np.mean(list(system_counts.values()))
        }
        
        return report
    
    def validate_timestamp_consistency(self) -> Dict:
        """Validate timestamp consistency within systems."""
        report = {}
        
        for system_id in self.df['system_id'].unique():
            system_data = self.df[self.df['system_id'] == system_id].sort_values('timestamp')
            
            diffs = system_data['timestamp'].diff()[1:]
            
            report[system_id] = {
                'records': len(system_data),
                'timestamp_min': float(system_data['timestamp'].min()),
                'timestamp_max': float(system_data['timestamp'].max()),
                'is_sorted': (diffs >= 0).all(),
                'has_gaps': (diffs > 1).any(),
                'avg_interval': float(diffs.mean()) if len(diffs) > 0 else 0
            }
        
        return report
    
    def run_full_validation(self) -> Dict:
        """Run all validation checks."""
        logger.info("=" * 80)
        logger.info("Starting full data validation...")
        logger.info("=" * 80)
        
        self.quality_report = {
            'columns': self.validate_columns(),
            'data_types': self.validate_data_types(),
            'null_values': self.validate_null_values(),
            'numeric_ranges': self.validate_numeric_ranges(),
            'system_distribution': self.validate_system_distribution(),
            'timestamp_consistency': self.validate_timestamp_consistency()
        }
        
        logger.info("=" * 80)
        logger.info("Validation complete!")
        logger.info("=" * 80)
        
        return self.quality_report
    
    def print_report(self):
        """Print validation report."""
        if not self.quality_report:
            logger.error("No report available. Run run_full_validation() first.")
            return
        
        print("\n" + "=" * 80)
        print("DATA QUALITY REPORT")
        print("=" * 80)
        
        # Column validation
        print("\n1. COLUMN VALIDATION")
        col_report = self.quality_report['columns']
        print(f"   Has all required columns: {col_report['has_all_columns']}")
        if col_report['missing_columns']:
            print(f"   Missing columns: {col_report['missing_columns']}")
        if col_report['extra_columns']:
            print(f"   Extra columns: {col_report['extra_columns']}")
        
        # Data types
        print("\n2. DATA TYPES")
        for col, dtype in self.quality_report['data_types'].items():
            print(f"   {col}: {dtype}")
        
        # Null values
        print("\n3. NULL VALUES")
        null_report = self.quality_report['null_values']
        print(f"   Total rows: {null_report['total_rows']}")
        print(f"   Has nulls: {null_report['has_nulls']}")
        for col, count in null_report['null_counts'].items():
            if count > 0:
                print(f"   {col}: {count} nulls")
        
        # Numeric ranges
        print("\n4. NUMERIC RANGES")
        ranges = self.quality_report['numeric_ranges']
        
        print(f"\n   CPU Usage:")
        print(f"     Min: {ranges['cpu']['min']:.2f}, Max: {ranges['cpu']['max']:.2f}")
        print(f"     Mean: {ranges['cpu']['mean']:.2f}, Std: {ranges['cpu']['std']:.2f}")
        if ranges['cpu']['negative_values'] > 0:
            print(f"     WARNING: {ranges['cpu']['negative_values']} negative values")
        if ranges['cpu']['values_over_100'] > 0:
            print(f"     NOTE: {ranges['cpu']['values_over_100']} values over 100")
        
        print(f"\n   Memory Usage:")
        print(f"     Min: {ranges['memory']['min']:.2f}, Max: {ranges['memory']['max']:.2f}")
        print(f"     Mean: {ranges['memory']['mean']:.2f}, Std: {ranges['memory']['std']:.2f}")
        if ranges['memory']['negative_values'] > 0:
            print(f"     WARNING: {ranges['memory']['negative_values']} negative values")
        if ranges['memory']['values_over_100'] > 0:
            print(f"     NOTE: {ranges['memory']['values_over_100']} values over 100")
        
        print(f"\n   Timestamp:")
        print(f"     Min: {ranges['timestamp']['min']:.0f}, Max: {ranges['timestamp']['max']:.0f}")
        print(f"     Is sorted: {ranges['timestamp']['is_sorted']}")
        
        # System distribution
        print("\n5. SYSTEM DISTRIBUTION")
        sys_report = self.quality_report['system_distribution']
        print(f"   Unique systems: {sys_report['unique_systems']}")
        print(f"   Min records per system: {sys_report['min_records_per_system']}")
        print(f"   Max records per system: {sys_report['max_records_per_system']}")
        print(f"   Avg records per system: {sys_report['avg_records_per_system']:.0f}")
        
        # Timestamp consistency
        print("\n6. TIMESTAMP CONSISTENCY (by system)")
        ts_consistency = self.quality_report['timestamp_consistency']
        for system_id, info in sorted(ts_consistency.items())[:10]:
            print(f"\n   System {system_id}:")
            print(f"     Records: {info['records']}")
            print(f"     Sorted: {info['is_sorted']}")
            print(f"     Has gaps: {info['has_gaps']}")
            print(f"     Avg interval: {info['avg_interval']:.2f}")
        
        if len(ts_consistency) > 10:
            print(f"\n   ... and {len(ts_consistency) - 10} more systems")
        
        print("\n" + "=" * 80 + "\n")


def main():
    """Main execution block."""
    DATA_PATH = r"D:\Research\Operation\green-devops-operation-component\data\processed\workload_data.csv"
    
    try:
        validator = WorkloadDataValidator(DATA_PATH)
        validator.load_data()
        validator.run_full_validation()
        validator.print_report()
        
        logger.info("Validation completed successfully!")
        return validator
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise


if __name__ == "__main__":
    validator = main()
