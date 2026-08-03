"""
Runtime metrics storage for Engine 1.

Stores collected Prometheus metrics as historical data for building input sequences.
Uses CSV for simplicity and portability.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)


def align_to_30s(timestamp: int) -> int:
    """
    Align timestamp to nearest 30-second boundary.
    
    Ensures all metrics are on consistent 30-second intervals
    for proper LSTM input alignment.
    
    Args:
        timestamp: Unix timestamp (seconds)
    
    Returns:
        Aligned timestamp (rounded to nearest 30-sec interval)
    """
    remainder = timestamp % 30
    if remainder < 15:
        return timestamp - remainder
    else:
        return timestamp + (30 - remainder)


class RuntimeStore:
    """
    Store runtime metrics data in local file.
    
    Format: CSV with columns [timestamp, cpu, memory]
    - timestamp: Unix timestamp (seconds)
    - cpu: CPU usage (percentage or raw value from Prometheus)
    - memory: Memory usage (bytes or MB)
    """
    
    def __init__(self, store_dir: str = 'data/runtime_metrics'):
        """
        Initialize runtime store.
        
        Args:
            store_dir: Directory where runtime data is stored
        """
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def get_store_path(self, system_id: str) -> Path:
        """Get CSV file path for a system."""
        return self.store_dir / f"{system_id}_runtime_metrics.csv"
    
    def append_metrics(self, system_id: str, metrics: List[Dict]) -> int:
        """
        Append new metric records to store.
        
        Args:
            system_id: System identifier
            metrics: List of dicts with keys: timestamp, cpu, memory
        
        Returns:
            Number of records written
        """
        store_path = self.get_store_path(system_id)
        
        # Check if file exists (determines if we write header)
        file_exists = store_path.exists()
        
        try:
            with open(store_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'cpu', 'memory'])
                
                # Write header if new file
                if not file_exists:
                    writer.writeheader()
                    self.logger.info(f"Created new runtime store: {store_path}")
                
                # Write records
                for metric in metrics:
                    writer.writerow({
                        'timestamp': metric['timestamp'],
                        'cpu': metric['cpu'],
                        'memory': metric['memory']
                    })
            
            self.logger.debug(f"Appended {len(metrics)} records to {system_id}")
            return len(metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to write metrics: {e}")
            raise
    
    def read_latest(self, system_id: str, count: int = 12) -> List[Dict]:
        """
        Read the latest N records from store.
        
        Args:
            system_id: System identifier
            count: Number of latest records to return
        
        Returns:
            List of dicts with keys: timestamp, cpu, memory (oldest to newest)
        """
        store_path = self.get_store_path(system_id)
        
        if not store_path.exists():
            self.logger.warning(f"Store not found for {system_id}")
            return []
        
        try:
            records = []
            with open(store_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        'timestamp': int(row['timestamp']),
                        'cpu': float(row['cpu']),
                        'memory': float(row['memory'])
                    })
            
            # Return latest count records
            if len(records) > count:
                records = records[-count:]
            
            self.logger.debug(f"Read {len(records)} records for {system_id}")
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to read metrics: {e}")
            return []
    
    def get_record_count(self, system_id: str) -> int:
        """Get total number of records stored for a system."""
        store_path = self.get_store_path(system_id)
        
        if not store_path.exists():
            return 0
        
        try:
            count = 0
            with open(store_path, 'r') as f:
                count = sum(1 for _ in f) - 1  # Subtract header
            return max(0, count)
        except Exception as e:
            self.logger.error(f"Failed to count records: {e}")
            return 0
    
    def clear_store(self, system_id: str) -> bool:
        """Clear all data for a system."""
        store_path = self.get_store_path(system_id)
        
        try:
            if store_path.exists():
                store_path.unlink()
                self.logger.info(f"Cleared store for {system_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear store: {e}")
            return False
    
    def read_all(self, system_id: str) -> List[Dict]:
        """Read all records from store."""
        store_path = self.get_store_path(system_id)
        
        if not store_path.exists():
            return []
        
        try:
            records = []
            with open(store_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        'timestamp': int(row['timestamp']),
                        'cpu': float(row['cpu']),
                        'memory': float(row['memory'])
                    })
            return records
        except Exception as e:
            self.logger.error(f"Failed to read all metrics: {e}")
            return []
    
    def get_stats(self, system_id: str) -> Dict:
        """Get summary statistics about stored metrics."""
        records = self.read_all(system_id)
        
        if not records:
            return {
                'system_id': system_id,
                'record_count': 0,
                'time_span_seconds': 0,
                'cpu_mean': None,
                'cpu_min': None,
                'cpu_max': None
            }
        
        timestamps = [r['timestamp'] for r in records]
        cpus = [r['cpu'] for r in records]
        
        return {
            'system_id': system_id,
            'record_count': len(records),
            'time_span_seconds': timestamps[-1] - timestamps[0],
            'cpu_mean': sum(cpus) / len(cpus),
            'cpu_min': min(cpus),
            'cpu_max': max(cpus),
            'earliest_timestamp': timestamps[0],
            'latest_timestamp': timestamps[-1]
        }
    
    def export_as_npy(
        self,
        system_id: str,
        output_path: str,
        max_records: int = None
    ) -> bool:
        """
        Export runtime metrics as numpy arrays.
        
        Args:
            system_id: System identifier
            output_path: Path to save .npy file
            max_records: Limit number of records (None = all)
        
        Returns:
            True if successful
        """
        try:
            import numpy as np
            
            records = self.read_all(system_id)
            
            if max_records:
                records = records[-max_records:]
            
            if not records:
                self.logger.warning(f"No records to export for {system_id}")
                return False
            
            data = np.array([
                [r['cpu'], r['memory']] for r in records
            ], dtype=np.float32)
            
            np.save(output_path, data)
            self.logger.info(f"Exported {len(records)} records to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export as npy: {e}")
            return False
    
    def append_prediction(
        self,
        system_id: str,
        timestamp: int,
        predicted_cpu: float,
        predicted_load_level: str,
        recommended_pods: int,
        data_source: str
    ) -> bool:
        """
        Log prediction to CSV file for audit trail.
        
        Args:
            system_id: System identifier
            timestamp: Prediction timestamp (Unix seconds)
            predicted_cpu: Predicted CPU usage percentage
            predicted_load_level: Load classification (LOW/NORMAL/HIGH)
            recommended_pods: Recommended pod count
            data_source: Source of prediction (cold_start/runtime)
        
        Returns:
            True if successful
        """
        try:
            from pathlib import Path
            
            # Get predictions directory from config if available
            try:
                from config import PREDICTIONS_LOG_DIR
                pred_dir = Path(PREDICTIONS_LOG_DIR)
            except ImportError:
                pred_dir = Path("data/predictions")
            
            pred_dir.mkdir(parents=True, exist_ok=True)
            pred_file = pred_dir / f"{system_id}.csv"
            
            # Check if file exists
            file_exists = pred_file.exists()
            
            with open(pred_file, 'a', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        'timestamp',
                        'predicted_cpu',
                        'predicted_load_level',
                        'recommended_pods',
                        'data_source'
                    ]
                )
                
                # Write header if new file
                if not file_exists:
                    writer.writeheader()
                
                # Write prediction record
                writer.writerow({
                    'timestamp': timestamp,
                    'predicted_cpu': f"{predicted_cpu:.2f}",
                    'predicted_load_level': predicted_load_level,
                    'recommended_pods': recommended_pods,
                    'data_source': data_source
                })
            
            self.logger.debug(f"Logged prediction for {system_id} to {pred_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to append prediction: {e}")
            return False
