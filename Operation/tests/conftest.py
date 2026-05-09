"""Pytest configuration and fixtures"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_metrics():
    """Sample Prometheus metrics"""
    return {
        "cpu_utilization": 0.75,
        "memory_utilization": 0.60,
        "pod_count": 5,
        "timestamp": "2024-04-15T10:30:00Z"
    }


@pytest.fixture
def sample_job():
    """Sample job definition"""
    return {
        "job_id": "job-001",
        "job_type": "api_request",
        "estimated_duration_seconds": 30,
        "deadline_seconds": 100
    }
