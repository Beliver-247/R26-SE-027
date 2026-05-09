"""
Prometheus metrics collector for Engine 1 runtime data.

Collects live CPU and memory metrics from Prometheus for a deployed system.
Supports configuration-based Prometheus connections and fallback mock mode.
"""

import logging
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class PrometheusMetricsCollector:
    """Collect metrics from Prometheus for a specific deployed system."""
    
    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        system_id: str = "unknown_system",
        timeout: int = 10
    ):
        """
        Initialize Prometheus collector.
        
        Args:
            prometheus_url: Base URL of Prometheus instance
            system_id: Kubernetes pod/system identifier (pod_name, pod_namespace, etc.)
            timeout: Request timeout (seconds)
        """
        self.prometheus_url = prometheus_url.rstrip('/')
        self.system_id = system_id
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify Prometheus is reachable."""
        try:
            response = requests.get(
                f"{self.prometheus_url}/-/healthy",
                timeout=self.timeout
            )
            if response.status_code == 200:
                self.logger.info(f"✓ Connected to Prometheus: {self.prometheus_url}")
            else:
                self.logger.warning(
                    f"Prometheus responded with status {response.status_code}"
                )
        except Exception as e:
            self.logger.error(f"Cannot reach Prometheus: {e}")
            self.logger.warning("Falling back to mock metrics mode")
            self._use_mock_mode = True
            return
        
        self._use_mock_mode = False
    
    def query_latest_metrics(
        self,
        lookback_minutes: int = 10
    ) -> List[Dict]:
        """
        Query Prometheus for latest CPU and memory metrics.
        
        Args:
            lookback_minutes: How far back to look for data
        
        Returns:
            List of dicts with keys: timestamp, cpu, memory (in order from oldest to newest)
        """
        if self._use_mock_mode:
            return self._generate_mock_metrics(count=1)
        
        metrics = []
        
        try:
            # Query CPU usage
            cpu_query = f'container_cpu_usage_seconds_total{{pod="{self.system_id}"}}'
            cpu_data = self._query_prometheus(cpu_query)
            
            # Query memory usage
            mem_query = f'container_memory_usage_bytes{{pod="{self.system_id}"}}'
            mem_data = self._query_prometheus(mem_query)
            
            # Merge into unified stream
            metrics = self._merge_metrics(cpu_data, mem_data)
            
            self.logger.debug(f"Collected {len(metrics)} metric points")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Prometheus query failed: {e}")
            # Fallback to mock
            return self._generate_mock_metrics(count=1)
    
    def _query_prometheus(self, query: str) -> Dict:
        """Execute a Prometheus query."""
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {'query': query}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                raise RuntimeError(f"Query failed: {data.get('error', 'unknown')}")
            
            return data['data']['result']
            
        except Exception as e:
            self.logger.error(f"Prometheus query error: {e}")
            raise
    
    def _merge_metrics(self, cpu_data: List, mem_data: List) -> List[Dict]:
        """
        Merge CPU and memory data into unified metric stream.
        
        Args:
            cpu_data: Prometheus CPU query result
            mem_data: Prometheus memory query result
        
        Returns:
            List of dicts with timestamp, cpu, memory
        """
        metrics = []
        
        # Simple merge: assume timestamps match or are close
        # In production, use more sophisticated alignment
        for cpu_point in cpu_data:
            if not cpu_point['value']:
                continue
            
            ts = int(cpu_point['value'][0])
            cpu_val = float(cpu_point['value'][1])
            
            # Find corresponding memory point (within 5 sec tolerance)
            mem_val = 0.0
            for mem_point in mem_data:
                if not mem_point['value']:
                    continue
                mem_ts = int(mem_point['value'][0])
                if abs(mem_ts - ts) < 5:
                    mem_val = float(mem_point['value'][1])
                    break
            
            metrics.append({
                'timestamp': ts,
                'cpu': cpu_val,
                'memory': mem_val
            })
        
        # Sort by timestamp
        metrics.sort(key=lambda x: x['timestamp'])
        return metrics
    
    def _generate_mock_metrics(self, count: int = 1) -> List[Dict]:
        """
        Generate mock metrics for development/testing.
        
        Returns realistic-looking CPU and memory data.
        """
        import random
        metrics = []
        now = int(datetime.utcnow().timestamp())
        
        for i in range(count):
            ts = now - (count - 1 - i) * 30  # 30-sec intervals
            phase = (ts // 30) % 5
            if phase == 0:
                base_cpu = random.uniform(15.0, 25.0)
                base_memory = random.uniform(350, 550)
            elif phase in (1, 2):
                base_cpu = random.uniform(45.0, 60.0)
                base_memory = random.uniform(550, 750)
            elif phase == 3:
                base_cpu = random.uniform(75.0, 90.0)
                base_memory = random.uniform(750, 950)
            else:
                base_cpu = random.uniform(25.0, 40.0)
                base_memory = random.uniform(450, 650)

            cpu = base_cpu + random.gauss(0, 5.0)
            cpu = max(0, min(100, cpu))
            memory = base_memory + random.gauss(0, 50)
            memory = max(0, memory)
            
            metrics.append({
                'timestamp': ts,
                'cpu': cpu,
                'memory': memory
            })
        
        return metrics
    
    def query_range(
        self,
        lookback_minutes: int = 10,
        step_seconds: int = 30
    ) -> List[Dict]:
        """
        Query historical range of metrics.
        
        Args:
            lookback_minutes: How far back to query
            step_seconds: Data point spacing (30 sec recommended)
        
        Returns:
            List of dicts with timestamp, cpu, memory
        """
        if self._use_mock_mode:
            count = (lookback_minutes * 60) // step_seconds
            return self._generate_mock_metrics(count=count)
        
        try:
            now = datetime.utcnow()
            start_time = (now - timedelta(minutes=lookback_minutes)).isoformat() + "Z"
            end_time = now.isoformat() + "Z"
            
            # Query CPU range
            cpu_query = f'container_cpu_usage_seconds_total{{pod="{self.system_id}"}}'
            cpu_url = f"{self.prometheus_url}/api/v1/query_range"
            cpu_params = {
                'query': cpu_query,
                'start': start_time,
                'end': end_time,
                'step': f'{step_seconds}s'
            }
            cpu_response = requests.get(cpu_url, params=cpu_params, timeout=self.timeout)
            cpu_response.raise_for_status()
            cpu_data = cpu_response.json()
            
            # Query memory range
            mem_query = f'container_memory_usage_bytes{{pod="{self.system_id}"}}'
            mem_params = {
                'query': mem_query,
                'start': start_time,
                'end': end_time,
                'step': f'{step_seconds}s'
            }
            mem_response = requests.get(cpu_url, params=mem_params, timeout=self.timeout)
            mem_response.raise_for_status()
            mem_data = mem_response.json()
            
            # Merge results
            metrics = []
            if cpu_data['data']['result']:
                cpu_values = cpu_data['data']['result'][0]['values']
                for ts, cpu_val in cpu_values:
                    metrics.append({
                        'timestamp': int(ts),
                        'cpu': float(cpu_val),
                        'memory': 0.0
                    })
            
            # Fill memory values
            if metrics and mem_data['data']['result']:
                mem_values = mem_data['data']['result'][0]['values']
                mem_dict = {int(ts): float(val) for ts, val in mem_values}
                for metric in metrics:
                    metric['memory'] = mem_dict.get(metric['timestamp'], 0.0)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Range query failed: {e}")
            # Fallback to mock
            count = (lookback_minutes * 60) // step_seconds
            return self._generate_mock_metrics(count=count)


def align_to_30s(timestamp: int) -> int:
    """
    Align timestamp to nearest 30-second boundary.
    
    Args:
        timestamp: Unix timestamp (seconds)
    
    Returns:
        Aligned timestamp (rounded to nearest 30-sec interval)
    
    Example:
        align_to_30s(1234565) -> 1234560 (if closer to 1234560)
    """
    remainder = timestamp % 30
    if remainder < 15:
        return timestamp - remainder
    else:
        return timestamp + (30 - remainder)


class MetricsCollectorFactory:
    """Factory for creating metrics collectors."""
    
    @staticmethod
    def create_from_env(system_id: str) -> PrometheusMetricsCollector:
        """
        Create collector from environment variables.
        
        Environment variables:
        - PROMETHEUS_URL: Prometheus endpoint (default: http://localhost:9090)
        - USE_MOCK_METRICS: Force mock mode if set
        """
        import os
        
        prometheus_url = os.getenv(
            'PROMETHEUS_URL',
            'http://localhost:9090'
        )
        
        use_mock = os.getenv('USE_MOCK_METRICS', '').lower() == 'true'
        
        collector = PrometheusMetricsCollector(
            prometheus_url=prometheus_url,
            system_id=system_id
        )
        
        if use_mock:
            collector._use_mock_mode = True
            logger.info("Using mock metrics mode")
        
        return collector
    
    @staticmethod
    def create_mock() -> PrometheusMetricsCollector:
        """Create a collector in mock mode for testing."""
        collector = PrometheusMetricsCollector(
            prometheus_url='http://localhost:9090',
            system_id='test_system'
        )
        collector._use_mock_mode = True
        return collector
