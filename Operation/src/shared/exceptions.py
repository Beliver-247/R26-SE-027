"""Custom exception types"""


class OperationPhaseException(Exception):
    """Base exception for Operation Phase component"""
    pass


class ConfigException(OperationPhaseException):
    """Configuration related errors"""
    pass


class ModelException(OperationPhaseException):
    """Model loading/inference errors"""
    pass


class PredictionException(OperationPhaseException):
    """Workload prediction errors"""
    pass


class CarbonCalculationException(OperationPhaseException):
    """Carbon calculation errors"""
    pass


class JobPrioritizationException(OperationPhaseException):
    """Job prioritization errors"""
    pass


class KubernetesIntegrationException(OperationPhaseException):
    """Kubernetes integration errors"""
    pass


class PrometheusException(OperationPhaseException):
    """Prometheus connection/query errors"""
    pass


class DataLayerException(OperationPhaseException):
    """Data collection/preprocessing errors"""
    pass
