"""Common utility functions"""
import logging
from typing import Any, Dict
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


def get_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.utcnow()


def get_timestamp_str() -> str:
    """Get current UTC timestamp as ISO string"""
    return datetime.utcnow().isoformat() + "Z"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except Exception as e:
        logger.error(f"Division error: {e}")
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


def dict_to_dotdict(d: Dict) -> "DotDict":
    """Convert dict to dot-notation dict"""
    return DotDict(d)


class DotDict(dict):
    """Dict with dot-notation access"""
    def __getattr__(self, key):
        return self.get(key)
    
    def __setattr__(self, key, value):
        self[key] = value


def format_carbon_grams(grams: float) -> str:
    """Format carbon grams to human readable"""
    if grams < 1000:
        return f"{grams:.1f}g CO2"
    elif grams < 1_000_000:
        return f"{grams/1000:.2f}kg CO2"
    else:
        return f"{grams/1_000_000:.2f}t CO2"
