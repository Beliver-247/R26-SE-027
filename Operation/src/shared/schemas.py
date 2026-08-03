"""Pydantic schemas for data contracts"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class PredictionResult(BaseModel):
    predicted_cpu_cores: float
    predicted_memory_gb: float
    predicted_pod_count: int
    confidence: float
    timestamp: datetime


class CarbonImpact(BaseModel):
    carbon_grams: float
    carbon_breakdown: Dict[str, float]
    energy_kwh: float


class ScalingDecision(BaseModel):
    action: str  # scale_up, scale_down, no_change
    recommended_pod_count: int
    carbon_cost_grams: float
    sla_impact: str  # compliant, risk, violation
    confidence: float


class JobPriority(BaseModel):
    job_id: str
    priority: str  # critical, important, delayable, background
    delay_allowed: bool
    max_delay_seconds: int
    reason: str
