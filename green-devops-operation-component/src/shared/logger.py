"""Logging configuration"""
import logging
import logging.handlers
import sys
import os
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs/",
    log_format: str = "json"
) -> logging.Logger:
    """Configure logging for the application"""
    
    # Create log directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # Get root logger
    logger = logging.getLogger("operation_phase")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "application.log"),
        maxBytes=100_000_000,  # 100MB
        backupCount=10
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Formatter
    if log_format == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Module-level logger
logger = setup_logging()
