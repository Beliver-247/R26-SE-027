"""
FastAPI endpoints for Engine 1 Workload Prediction Engine.

Provides simple REST API for:
- GET /predict - Latest prediction for a system
- GET /health - System health and mode status
- GET /metrics/{system_id} - Metrics summary for a system
- POST /carbon/evaluate - Carbon emission evaluation

Lightweight production-ready endpoints with minimal dependencies.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import os
import sys
import numpy as np
import time

# Add src directory to path for imports (so we can import carbon_engine as a package)
src_path = os.path.join(os.path.dirname(__file__), '..')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

logger = logging.getLogger(__name__)


# ==================== PYDANTIC MODELS ====================

class TimestepData(BaseModel):
    """Single timestep with CPU and memory metrics."""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU usage 0-100%")
    memory_mb: float = Field(..., ge=0.0, description="Memory usage in MB")


class ManualPredictionRequest(BaseModel):
    """Request for manual input prediction."""
    system_id: str = Field(..., description="System identifier")
    data_source: str = Field("manual_test", description="Data source label")
    sequence: List[TimestepData] = Field(
        ..., 
        description="Exactly 12 timesteps of metrics"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "system_id": "test-pod",
                "data_source": "manual_test",
                "sequence": [
                    {"timestamp": "2026-04-16T12:00:00Z", "cpu_percent": 25.0, "memory_mb": 550},
                    {"timestamp": "2026-04-16T12:00:30Z", "cpu_percent": 26.5, "memory_mb": 560}
                ]
            }
        }
    }


# ==================== PYDANTIC MODELS FOR CARBON EVALUATION ====================

class CarbonEvaluationRequest(BaseModel):
    """Request for carbon emission evaluation with Engine 3 support."""
    system_id: str = Field(..., description="System identifier")
    predicted_cpu: float = Field(..., ge=0.0, le=100.0, description="Predicted CPU percentage (0-100%)")
    predicted_load_level: str = Field(..., description="Predicted load level (LOW/NORMAL/HIGH)")
    recommended_pods: int = Field(..., ge=1, le=20, description="Recommended pod count from Engine 1")
    current_pods: int = Field(..., ge=1, le=20, description="Current running pod count")
    prediction_window_seconds: int = Field(30, description="Prediction window in seconds (default: 30)")
    delayable_jobs: Optional[int] = Field(None, ge=0, description="Number of jobs that can be delayed (from Engine 3, optional)")
    workload_reduction_percent: Optional[float] = Field(None, ge=0.0, le=1.0, description="Workload reduction fraction (0-1.0, e.g., 0.4 = 40%, from Engine 3, optional)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "system_id": "api-service",
                "predicted_cpu": 75.5,
                "predicted_load_level": "HIGH",
                "recommended_pods": 5,
                "current_pods": 3,
                "prediction_window_seconds": 30,
                "delayable_jobs": 10,
                "workload_reduction_percent": 0.4
            }
        }
    }


class CarbonScenario(BaseModel):
    """Single carbon scenario result."""
    name: str
    description: str
    pod_count: int
    energy_kwh: float
    carbon_gco2: float
    carbon_kg: Optional[float] = None


class CarbonDecision(BaseModel):
    """Carbon-based decision recommendation."""
    recommended_action: str
    carbon_saving_percent: float
    carbon_saving_gco2: float
    reasoning: Optional[str] = None


class CarbonEvaluationResponse(BaseModel):
    """Response from carbon emission evaluation."""
    status: str = Field("success", description="Request status")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    system_id: str = Field(..., description="System identifier")
    engine_version: str = Field("2.0", description="Engine version")
    
    input: Dict[str, Any] = Field(..., description="Echo back of input parameters")
    scenarios: List[Dict[str, Any]] = Field(..., description="Evaluated scenarios with energy/carbon metrics")
    decision: Dict[str, Any] = Field(..., description="Recommended action and carbon savings")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Model configuration and assumptions")


# ==================== PYDANTIC MODELS FOR ENGINE 3 JOB PRIORITIZATION ====================

class JobMetadata(BaseModel):
    """Metadata for a single job."""
    job_id: str = Field(..., description="Unique job identifier")
    job_type: str = Field(..., description="Type/class of the job")
    priority: Optional[str] = Field(None, description="Explicit priority (HIGH/MEDIUM/LOW)")
    estimated_runtime_seconds: Optional[int] = Field(None, ge=0, description="Estimated runtime in seconds")
    estimated_cpu_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Estimated CPU contribution (0-100%)")
    deadline_seconds: Optional[int] = Field(None, ge=0, description="Time until deadline in seconds")
    already_delayed_seconds: Optional[int] = Field(None, ge=0, description="Cumulative delay already applied")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "job_101",
                "job_type": "report_generation",
                "priority": "LOW",
                "estimated_runtime_seconds": 180,
                "estimated_cpu_percent": 10.0,
                "deadline_seconds": 3600,
                "already_delayed_seconds": 0
            }
        }
    }


class Engine3EvaluationRequest(BaseModel):
    """Request for Engine 3 job prioritization evaluation."""
    jobs: List[JobMetadata] = Field(..., description="List of jobs to evaluate")
    backlog_size: Optional[int] = Field(0, ge=0, description="Current job backlog size")
    current_load_level: Optional[str] = Field("NORMAL", description="Current load level (LOW/NORMAL/HIGH)")
    current_cpu: Optional[float] = Field(None, ge=0.0, le=100.0, description="Current CPU utilization (0-100%)")
    current_pods: Optional[int] = Field(None, ge=1, description="Current running pod count")
    
    @field_validator("current_load_level")
    @classmethod
    def validate_load_level(cls, v: str) -> str:
        """Validate load_level is one of allowed values."""
        if v not in ("LOW", "NORMAL", "HIGH"):
            raise ValueError(f"current_load_level must be LOW/NORMAL/HIGH, got {v}")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "jobs": [
                    {
                        "job_id": "job_101",
                        "job_type": "report_generation",
                        "priority": "LOW",
                        "estimated_runtime_seconds": 180,
                        "estimated_cpu_percent": 10.0,
                        "deadline_seconds": 3600,
                        "already_delayed_seconds": 0
                    },
                    {
                        "job_id": "job_102",
                        "job_type": "payment_processing",
                        "priority": "HIGH",
                        "estimated_runtime_seconds": 5,
                        "estimated_cpu_percent": 20.0,
                        "deadline_seconds": 10,
                        "already_delayed_seconds": 0
                    }
                ],
                "backlog_size": 5,
                "current_load_level": "HIGH",
                "current_cpu": 85.0,
                "current_pods": 5
            }
        }
    }


class Engine3EvaluationResponse(BaseModel):
    """Response from Engine 3 job prioritization evaluation."""
    status: str = Field("success", description="Request status")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    engine_version: str = Field("3.0", description="Engine version")
    
    input: Dict[str, Any] = Field(..., description="Echo back of input parameters")
    classification_summary: Dict[str, Any] = Field(..., description="Job classification statistics")
    delayable_jobs: int = Field(..., ge=0, description="Number of jobs safe to delay")
    delayable_job_ids: List[str] = Field(..., description="IDs of jobs that can be delayed")
    workload_reduction_percent: float = Field(..., ge=0.0, le=1.0, description="Workload reduction as decimal (0-1)")
    delayed_cpu_percent: float = Field(..., ge=0.0, le=100.0, description="Workload reduction as percentage (0-100)")
    is_meaningful: bool = Field(..., description="Whether reduction meets minimum threshold")
    reason: str = Field(..., description="Explanation of the recommendation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional classification and eligibility information")
    evaluation_ms: float = Field(..., ge=0, description="Evaluation time in milliseconds")


# ==================== PYDANTIC MODELS FOR DECISION LAYER ====================

class DecisionLayerRequest(BaseModel):
    """Request for final Decision Layer evaluation combining all engines."""
    system_id: str = Field(..., description="System identifier")
    current_pods: int = Field(..., ge=1, le=100, description="Current running pod count")
    
    # Engine 1 output (prediction)
    engine1_output: Dict[str, Any] = Field(..., description="Engine 1 prediction output")
    
    # Engine 2 output (carbon analysis)
    engine2_output: Dict[str, Any] = Field(..., description="Engine 2 carbon analysis output")
    
    # Engine 3 output (job prioritization) - optional
    engine3_output: Optional[Dict[str, Any]] = Field(None, description="Engine 3 job prioritization output (optional)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "system_id": "api-service",
                "current_pods": 3,
                "engine1_output": {
                    "system_id": "api-service",
                    "prediction": {
                        "predicted_cpu": 65.5,
                        "predicted_load_level": "NORMAL",
                        "recommended_pods": 4,
                        "confidence": 0.92
                    }
                },
                "engine2_output": {
                    "raw_scenario": {"required_pods": 4},
                    "optimized_scenario": {"required_pods": 3},
                    "recommended_action": "hybrid",
                    "carbon_saving_gco2": 5.0,
                    "carbon_saving_percent": 25.0,
                    "metadata": {"sla_protected": False}
                },
                "engine3_output": {
                    "delayable_jobs": 5,
                    "delayable_job_ids": ["job_101", "job_102"],
                    "workload_reduction_percent": 0.3
                }
            }
        }
    }


class DecisionLayerResponse(BaseModel):
    """Response from Decision Layer with final merged decision."""
    status: str = Field("success", description="Request status")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    decision_id: str = Field(..., description="Unique decision identifier")
    
    decision: Dict[str, Any] = Field(..., description="Final decision details")
    reasoning: Dict[str, Any] = Field(..., description="Decision reasoning and explanation")
    input_echo: Dict[str, Any] = Field(..., description="Echo of input data for verification")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    evaluation_ms: float = Field(..., ge=0, description="Evaluation time in milliseconds")


class Engine1API:
    """Simple REST API for Engine 1 Workload Prediction Engine."""
    
    def __init__(self, app: FastAPI = None):
        """
        Initialize API with FastAPI app.
        
        Args:
            app: FastAPI application instance (creates new if None)
        """
        self.app = app or FastAPI(
            title="Engine 1 Workload Prediction API",
            description="Workload prediction and resource scaling API",
            version="1.0.0"
        )
        
        self.live_predictor = None
        self.last_prediction = None
        self.carbon_engine = None  # Carbon Emission Engine (Engine 2)
        self.job_prioritization_engine = None  # Job Prioritization Engine (Engine 3)
        self.decision_orchestrator = None  # Decision Layer orchestrator
        self.logger = logging.getLogger(__name__)
        
        # Register routes
        self._register_routes()
    
    def set_predictor(self, predictor) -> None:
        """
        Set the LivePredictor instance.
        
        Args:
            predictor: LivePredictor instance from workload_prediction_engine
        """
        self.live_predictor = predictor
        self.logger.info(f"[OK] Predictor set for system: {predictor.system_id}")
    
    def set_carbon_engine(self, carbon_engine) -> None:
        """
        Set the CarbonEmissionEngine instance (Engine 2).
        
        Args:
            carbon_engine: CarbonEmissionEngine instance from carbon_engine module
        """
        self.carbon_engine = carbon_engine
        self.logger.info("[OK] Carbon Emission Engine (Engine 2) set for carbon evaluation")
    
    def set_job_prioritization_engine(self, job_prioritization_engine) -> None:
        """
        Set the JobPrioritizationEngine instance (Engine 3).
        
        Args:
            job_prioritization_engine: JobPrioritizationEngine instance from job_prioritization_engine module
        """
        self.job_prioritization_engine = job_prioritization_engine
        self.logger.info("[OK] Job Prioritization Engine (Engine 3) set for job evaluation")
    
    def set_decision_orchestrator(self, decision_orchestrator) -> None:
        """
        Set the DecisionOrchestrator instance (Decision Layer).
        
        Args:
            decision_orchestrator: DecisionOrchestrator instance from decision_layer module
        """
        self.decision_orchestrator = decision_orchestrator
        self.logger.info("[OK] Decision Orchestrator (Decision Layer) set for final decision making")

    def _prediction_response_dict(self, prediction) -> Dict[str, Any]:
        """Return JSON-safe Engine 1 prediction fields."""
        return {
            "system_id": str(prediction.system_id),
            "predicted_cpu": float(prediction.predicted_cpu),
            "predicted_load_level": str(prediction.predicted_load_level),
            "recommended_pods": int(prediction.recommended_pods),
            "confidence": float(prediction.confidence or 0.0),
            "data_source": str(prediction.data_source),
            "model_version": str(prediction.model_version),
        }
    
    def _register_routes(self) -> None:
        """Register all API routes."""
        
        @self.app.get("/health", tags=["System"])
        async def health_check() -> Dict[str, Any]:
            """
            Health check endpoint.
            
            Returns:
                Status with current mode, record count, model version
            """
            if not self.live_predictor:
                raise HTTPException(
                    status_code=503,
                    detail="Predictor not initialized"
                )
            
            try:
                mode_info = self.live_predictor.get_mode_info()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "system_id": self.live_predictor.system_id,
                    "mode": mode_info['current_mode'],
                    "records_collected": mode_info['record_count'],
                    "model_version": mode_info.get('model_version', 'v1.0'),
                    "data_source": mode_info.get('data_source', 'mock'),
                    "retraining_ready": mode_info.get('retraining_ready', False)
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Health check failed: {str(e)}"
                )
        
        @self.app.get("/predict", tags=["Prediction"])
        async def get_latest_prediction() -> Dict[str, Any]:
            """
            Get latest prediction result.
            
            If no prediction available, runs one immediately.
            
            Returns:
                Latest Engine1Output with prediction details
            """
            if not self.live_predictor:
                raise HTTPException(
                    status_code=503,
                    detail="Predictor not initialized"
                )
            
            try:
                # Get or generate latest prediction
                if not self.last_prediction:
                    self.last_prediction = self.live_predictor.predict_next_window()
                
                return {
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "prediction": self._prediction_response_dict(self.last_prediction)
                }
            except Exception as e:
                self.logger.error(f"Prediction failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Prediction failed: {str(e)}"
                )
        
        @self.app.post("/predict/manual", tags=["Prediction"])
        async def predict_manual(request: ManualPredictionRequest) -> Dict[str, Any]:
            """
            Run prediction with manually provided input sequence.
            
            Accepts 12 timesteps of CPU and memory metrics, converts to model input,
            and returns prediction with analysis metadata.
            
            Args:
                request: ManualPredictionRequest with system_id and 12-timestep sequence
            
            Returns:
                Prediction with analysis (CPU range, confidence, inference time)
            """
            if not self.live_predictor:
                raise HTTPException(
                    status_code=503,
                    detail="Predictor not initialized"
                )
            
            try:
                # Validate sequence length
                if len(request.sequence) != 12:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Sequence must contain exactly 12 timesteps. Provided: {len(request.sequence)}"
                    )
                
                # Extract CPU and memory values into numpy array
                sequence_data = np.array([
                    [step.cpu_percent, step.memory_mb] 
                    for step in request.sequence
                ], dtype=np.float32)
                
                # Validate array shape
                if sequence_data.shape != (12, 2):
                    raise ValueError(f"Invalid sequence shape: {sequence_data.shape}")
                
                # Measure inference time
                start_time = time.time()
                
                # Run prediction
                prediction = self.live_predictor.predictor.predict(
                    sequence_data,
                    system_id=request.system_id,
                    data_source=request.data_source
                )
                
                inference_ms = (time.time() - start_time) * 1000
                
                # Calculate input statistics
                cpu_values = sequence_data[:, 0]
                mem_values = sequence_data[:, 1]
                
                input_analysis = {
                    "input_sequence_length": 12,
                    "input_cpu_range": {
                        "min": float(np.min(cpu_values)),
                        "max": float(np.max(cpu_values)),
                        "mean": float(np.mean(cpu_values)),
                        "std_dev": float(np.std(cpu_values))
                    },
                    "input_memory_range": {
                        "min": float(np.min(mem_values)),
                        "max": float(np.max(mem_values)),
                        "mean": float(np.mean(mem_values))
                    },
                    "prediction_confidence_category": (
                        "very_high" if prediction.confidence > 0.90 else
                        "high" if prediction.confidence > 0.80 else
                        "medium" if prediction.confidence > 0.70 else
                        "low"
                    ),
                    "model_inference_ms": round(inference_ms, 2)
                }
                
                return {
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "request_id": f"manual-{request.system_id}-{int(time.time()*1000)}",
                    "prediction": {
                        "system_id": prediction.system_id,
                        "predicted_cpu_percent": prediction.predicted_cpu,
                        "predicted_load_level": prediction.predicted_load_level,
                        "recommended_pods": prediction.recommended_pods,
                        "confidence": prediction.confidence,
                        "prediction_window_seconds": 30,
                        "data_source": request.data_source,
                        "model_version": prediction.model_version
                    },
                    "analysis": input_analysis
                }
            
            except HTTPException:
                raise
            except ValueError as e:
                self.logger.error(f"Validation error in manual prediction: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}"
                )
            except Exception as e:
                self.logger.error(f"Manual prediction failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Prediction failed: {str(e)}"
                )
        
        @self.app.get("/predict/run", tags=["Prediction"])
        async def run_prediction() -> Dict[str, Any]:
            """
            Run a new prediction immediately.
            
            Returns:
                New Engine1Output with prediction details
            """
            if not self.live_predictor:
                raise HTTPException(
                    status_code=503,
                    detail="Predictor not initialized"
                )
            
            try:
                prediction = self.live_predictor.predict_next_window()
                self.last_prediction = prediction
                
                return {
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "prediction": self._prediction_response_dict(prediction)
                }
            except Exception as e:
                self.logger.error(f"Prediction failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Prediction failed: {str(e)}"
                )
        
        @self.app.get("/metrics/{system_id}", tags=["Metrics"])
        async def get_metrics_summary(system_id: str) -> Dict[str, Any]:
            """
            Get summary statistics for collected metrics.
            
            Args:
                system_id: System identifier
            
            Returns:
                Statistics: record count, time span, CPU stats, etc.
            """
            if not self.live_predictor:
                raise HTTPException(
                    status_code=503,
                    detail="Predictor not initialized"
                )
            
            try:
                stats = self.live_predictor.store.get_stats(system_id)
                
                return {
                    "status": "success",
                    "system_id": system_id,
                    "metrics": {
                        "record_count": stats['record_count'],
                        "time_span_minutes": stats['time_span_seconds'] / 60,
                        "cpu_mean_percent": stats.get('cpu_mean'),
                        "cpu_min_percent": stats.get('cpu_min'),
                        "cpu_max_percent": stats.get('cpu_max'),
                        "earliest_timestamp": stats.get('earliest_timestamp'),
                        "latest_timestamp": stats.get('latest_timestamp')
                    }
                }
            except Exception as e:
                self.logger.error(f"Metrics query failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Metrics query failed: {str(e)}"
                )
        
        @self.app.get("/status", tags=["System"])
        async def get_status() -> Dict[str, Any]:
            """
            Get detailed system status.
            
            Returns:
                Comprehensive status information including mode, records, and timing
            """
            if not self.live_predictor:
                raise HTTPException(
                    status_code=503,
                    detail="Predictor not initialized"
                )
            
            try:
                mode_info = self.live_predictor.get_mode_info()
                
                return {
                    "status": "operational",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "system": {
                        "system_id": self.live_predictor.system_id,
                        "mode": mode_info['current_mode'],
                        "records_collected": mode_info['record_count'],
                        "data_age_minutes": (
                            mode_info['record_count'] * 30 // 60
                            if mode_info['record_count'] > 0 else 0
                        )
                    },
                    "model": {
                        "version": mode_info.get('model_version', 'v1.0'),
                        "data_source": mode_info.get('data_source', 'mock'),
                        "bootstrap_strategy": getattr(
                            self.live_predictor.bootstrap,
                            'strategy_name',
                            'unknown'
                        )
                    },
                    "retraining": {
                        "ready": mode_info.get('retraining_ready', False),
                        "records_threshold": (
                            self.live_predictor.mode_manager.retraining_threshold_records
                        )
                    },
                    "latest_prediction": (
                        {
                            "cpu_percent": float(self.last_prediction.predicted_cpu),
                            "load_level": str(self.last_prediction.predicted_load_level),
                            "pods": int(self.last_prediction.recommended_pods),
                            "confidence": float(self.last_prediction.confidence or 0.0)
                        } if self.last_prediction else None
                    )
                }
            except Exception as e:
                self.logger.error(f"Status query failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Status query failed: {str(e)}"
                )
        
        @self.app.post("/carbon/evaluate", tags=["Carbon Emissions"])
        async def evaluate_carbon(request: CarbonEvaluationRequest) -> Dict[str, Any]:
            """
            Evaluate carbon emissions for a workload prediction.
            
            Accepts Engine 1 prediction output and optionally Engine 3 job prioritization,
            calculates energy and carbon scenarios, and returns optimization recommendation.
            
            Args:
                request: CarbonEvaluationRequest with prediction and system data
            
            Returns:
                Carbon evaluation with scenarios and recommendation
            
            Example:
                POST /carbon/evaluate
                {
                    "system_id": "api-service",
                    "predicted_cpu": 75.5,
                    "predicted_load_level": "HIGH",
                    "recommended_pods": 5,
                    "current_pods": 3,
                    "prediction_window_seconds": 30,
                    "delayable_jobs": 10,
                    "workload_reduction_percent": 15.0
                }
            """
            # Check if carbon engine is initialized
            if not self.carbon_engine:
                self.logger.warning(
                    "Carbon engine not initialized. Attempting lazy initialization..."
                )
                try:
                    from carbon_engine import CarbonEmissionEngine
                    self.carbon_engine = CarbonEmissionEngine()
                    self.logger.info("[OK] Carbon Emission Engine initialized lazily")
                except ImportError as e:
                    self.logger.error(f"Failed to import CarbonEmissionEngine: {e}")
                    raise HTTPException(
                        status_code=503,
                        detail="Carbon Emission Engine not available"
                    )
            
            try:
                # Validate request data
                if not 0 <= request.predicted_cpu <= 100:
                    raise ValueError(f"predicted_cpu must be 0-100, got {request.predicted_cpu}")
                
                if request.predicted_load_level not in ("LOW", "NORMAL", "HIGH"):
                    raise ValueError(
                        f"predicted_load_level must be LOW/NORMAL/HIGH, got {request.predicted_load_level}"
                    )
                
                if request.recommended_pods < 1 or request.recommended_pods > 20:
                    raise ValueError(
                        f"recommended_pods must be 1-20, got {request.recommended_pods}"
                    )
                
                if request.current_pods < 1 or request.current_pods > 20:
                    raise ValueError(
                        f"current_pods must be 1-20, got {request.current_pods}"
                    )
                
                # Validate optional fields
                if request.workload_reduction_percent is not None:
                    if not 0 <= request.workload_reduction_percent <= 1.0:
                        raise ValueError(
                            f"workload_reduction_percent must be 0-1.0 (float), got {request.workload_reduction_percent}"
                        )
                
                if request.delayable_jobs is not None and request.delayable_jobs < 0:
                    raise ValueError(
                        f"delayable_jobs must be >= 0, got {request.delayable_jobs}"
                    )
                
                self.logger.info(
                    f"Carbon evaluation request: system={request.system_id}, "
                    f"cpu={request.predicted_cpu}%, load={request.predicted_load_level}, "
                    f"pods={request.recommended_pods}, current={request.current_pods}"
                )
                
                if request.workload_reduction_percent is not None:
                    self.logger.info(
                        f"  Engine 3 support: {request.workload_reduction_percent:.1%} workload reduction, "
                        f"{request.delayable_jobs} delayable jobs"
                    )
                
                # Run carbon evaluation
                start_time = time.time()
                
                result = self.carbon_engine.evaluate(
                    predicted_cpu=request.predicted_cpu,
                    load_level=request.predicted_load_level,
                    raw_required_pods=request.recommended_pods,
                    current_pods=request.current_pods,
                    prediction_window_seconds=request.prediction_window_seconds,
                    delayable_jobs=request.delayable_jobs,
                    workload_reduction_percent=request.workload_reduction_percent
                )
                
                evaluation_ms = (time.time() - start_time) * 1000
                
                # Return structured response with Engine 3 support
                return {
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "system_id": request.system_id,
                    "engine_version": "2.1",
                    "input": result.get("input", {}),
                    "raw_scenario": result.get("raw_scenario", {}),
                    "optimized_scenario": result.get("optimized_scenario"),
                    "recommended_action": result.get("recommended_action"),
                    "optimized_required_pods": result.get("optimized_required_pods"),
                    "carbon_saving_gco2": result.get("carbon_saving_gco2"),
                    "carbon_saving_percent": result.get("carbon_saving_percent"),
                    "reason": result.get("reason"),
                    "scenarios": result.get("scenarios", []),
                    "metadata": result.get("metadata", {}),
                    "evaluation_ms": round(evaluation_ms, 2)
                }
            
            except ValueError as e:
                self.logger.error(f"Validation error in carbon evaluation: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}"
                )
            except Exception as e:
                self.logger.error(f"Carbon evaluation failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Carbon evaluation failed: {str(e)}"
                )
        
        
        @self.app.post("/jobs/evaluate", tags=["Job Prioritization"])
        async def evaluate_jobs(request: Engine3EvaluationRequest) -> Dict[str, Any]:
            """
            Evaluate job prioritization and determine delayable workload.
            
            Accepts a list of jobs with metadata, classifies them by priority,
            checks delay eligibility, and estimates workload reduction from delaying
            safe jobs. Output suitable for Engine 2 carbon analysis.
            
            Args:
                request: Engine3EvaluationRequest with job list and system context
            
            Returns:
                Job prioritization analysis with delayable jobs and workload reduction
            
            Example:
                POST /jobs/evaluate
                {
                    "jobs": [
                        {
                            "job_id": "job_101",
                            "job_type": "report_generation",
                            "priority": "LOW",
                            "estimated_runtime_seconds": 180,
                            "estimated_cpu_percent": 10.0,
                            "deadline_seconds": 3600,
                            "already_delayed_seconds": 0
                        }
                    ],
                    "backlog_size": 5,
                    "current_load_level": "HIGH",
                    "current_cpu": 85.0,
                    "current_pods": 5
                }
            """
            # Check if job prioritization engine is initialized
            if not self.job_prioritization_engine:
                self.logger.warning(
                    "Job Prioritization Engine not initialized. Attempting lazy initialization..."
                )
                try:
                    from job_prioritization_engine import JobPrioritizationEngine
                    self.job_prioritization_engine = JobPrioritizationEngine()
                    self.logger.info("[OK] Job Prioritization Engine (Engine 3) initialized lazily")
                except ImportError as e:
                    self.logger.error(f"Failed to import JobPrioritizationEngine: {e}")
                    raise HTTPException(
                        status_code=503,
                        detail="Job Prioritization Engine not available"
                    )
            
            try:
                # Validate request data
                if not request.jobs:
                    raise ValueError("jobs list cannot be empty")
                
                if request.backlog_size < 0:
                    raise ValueError(f"backlog_size must be >= 0, got {request.backlog_size}")
                
                if request.current_load_level not in ("LOW", "NORMAL", "HIGH"):
                    raise ValueError(
                        f"current_load_level must be LOW/NORMAL/HIGH, got {request.current_load_level}"
                    )
                
                if request.current_cpu is not None and not (0 <= request.current_cpu <= 100):
                    raise ValueError(f"current_cpu must be 0-100, got {request.current_cpu}")
                
                if request.current_pods is not None and request.current_pods < 1:
                    raise ValueError(f"current_pods must be >= 1, got {request.current_pods}")
                
                self.logger.info(
                    f"Job evaluation request: {len(request.jobs)} jobs, "
                    f"load={request.current_load_level}, "
                    f"backlog={request.backlog_size}"
                )
                
                # Convert Pydantic models to dicts for engine
                jobs_list = [job.dict(exclude_none=True) for job in request.jobs]
                
                # Run job prioritization evaluation
                start_time = time.time()
                
                result = self.job_prioritization_engine.evaluate(
                    jobs=jobs_list,
                    backlog_size=request.backlog_size,
                    current_load_level=request.current_load_level,
                    current_cpu=request.current_cpu,
                    current_pods=request.current_pods
                )
                
                evaluation_ms = (time.time() - start_time) * 1000
                
                # Return structured response
                return {
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "engine_version": "3.0",
                    "input": result.get("input", {}),
                    "classification_summary": result.get("classification_summary", {}),
                    "delayable_jobs": result.get("delayable_jobs", 0),
                    "delayable_job_ids": result.get("delayable_job_ids", []),
                    "workload_reduction_percent": result.get("workload_reduction_percent", 0.0),
                    "delayed_cpu_percent": result.get("delayed_cpu_percent", 0.0),
                    "is_meaningful": result.get("is_meaningful", False),
                    "reason": result.get("reason", ""),
                    "metadata": result.get("metadata", {}),
                    "evaluation_ms": round(evaluation_ms, 2)
                }
            
            except ValueError as e:
                self.logger.error(f"Validation error in job evaluation: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}"
                )
            except Exception as e:
                self.logger.error(f"Job evaluation failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Job evaluation failed: {str(e)}"
                )
        
        
        @self.app.post("/decision/evaluate", tags=["Decision Layer"])
        async def evaluate_decision(request: DecisionLayerRequest) -> Dict[str, Any]:
            """
            Evaluate final decision by merging all engine outputs.
            
            Accepts outputs from Engine 1 (prediction), Engine 2 (carbon analysis),
            and Engine 3 (job prioritization), and produces one final executable action.
            
            Args:
                request: DecisionLayerRequest with all engine outputs
            
            Returns:
                Final merged decision with action, pod requirements, and reasoning
            
            Example:
                POST /decision/evaluate
                {
                    "system_id": "api-service",
                    "current_pods": 3,
                    "engine1_output": {...},
                    "engine2_output": {...},
                    "engine3_output": {...}
                }
            """
            # Check if decision orchestrator is initialized
            if not self.decision_orchestrator:
                self.logger.warning(
                    "Decision Orchestrator not initialized. Attempting lazy initialization..."
                )
                try:
                    from decision_layer import DecisionOrchestrator
                    self.decision_orchestrator = DecisionOrchestrator()
                    self.logger.info("[OK] Decision Orchestrator initialized lazily")
                except ImportError as e:
                    self.logger.error(f"Failed to import DecisionOrchestrator: {e}")
                    raise HTTPException(
                        status_code=503,
                        detail="Decision Orchestrator not available"
                    )
            
            try:
                self.logger.info(
                    f"Decision evaluation request: system={request.system_id}, "
                    f"current_pods={request.current_pods}"
                )
                
                # Run decision evaluation
                start_time = time.time()
                
                decision_output = self.decision_orchestrator.evaluate(
                    engine1_output=request.engine1_output,
                    engine2_output=request.engine2_output,
                    engine3_output=request.engine3_output,
                    current_pods=request.current_pods
                )
                
                evaluation_ms = (time.time() - start_time) * 1000
                
                # Validate and return response
                decision_output.validate()
                response = decision_output.to_response_dict()
                response["evaluation_ms"] = round(evaluation_ms, 2)
                return response
            
            except ValueError as e:
                self.logger.error(f"Validation error in decision evaluation: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}"
                )
            except Exception as e:
                self.logger.error(f"Decision evaluation failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Decision evaluation failed: {str(e)}"
                )


def create_api_app(
    live_predictor=None,
    carbon_engine=None,
    job_prioritization_engine=None,
    decision_orchestrator=None,
    title: str = "Engine 1 API",
    debug: bool = False
) -> FastAPI:
    """
    Factory function to create a configured FastAPI application.
    
    Args:
        live_predictor: LivePredictor instance (optional)
        carbon_engine: CarbonEmissionEngine instance (optional)
        job_prioritization_engine: JobPrioritizationEngine instance (optional)
        decision_orchestrator: DecisionOrchestrator instance (optional)
        title: API title
        debug: Enable debug mode
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description="Workload prediction and automatic scaling engine",
        version="1.0.0",
        debug=debug
    )
    
    api = Engine1API(app)
    app.state.engine1_api = api
    
    if live_predictor:
        api.set_predictor(live_predictor)
    
    if carbon_engine:
        api.set_carbon_engine(carbon_engine)
    
    if job_prioritization_engine:
        api.set_job_prioritization_engine(job_prioritization_engine)
    
    if decision_orchestrator:
        api.set_decision_orchestrator(decision_orchestrator)
    
    return app


# Example usage for standalone server (see run_api_server.py)
if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create app
    app = create_api_app()
    
    # Run server (requires uvicorn)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
