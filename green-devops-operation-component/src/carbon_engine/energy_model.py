"""
Energy consumption model for Engine 2.

Calculates energy usage based on pod count and time window.
"""

import logging
from typing import Dict, Any
from carbon_engine.config import ENERGY_PER_POD_KWH_PER_HOUR

logger = logging.getLogger(__name__)


class EnergyModel:
    """
    Model energy consumption for cloud workloads.
    
    Energy calculation:
        energy_kwh = pods × energy_per_pod_per_hour × (time_window_seconds / 3600)
    
    Assumptions:
    - Each pod consumes ~0.5 kW average
    - Linear scaling with pod count
    - Time-proportional consumption
    """
    
    def __init__(self, energy_per_pod_kwh: float = ENERGY_PER_POD_KWH_PER_HOUR):
        """
        Initialize energy model.
        
        Args:
            energy_per_pod_kwh: Energy consumption per pod per hour (kWh)
                Default: 0.5 kWh based on typical cloud pod
        """
        self.energy_per_pod_kwh = energy_per_pod_kwh
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(
            f"EnergyModel initialized: {energy_per_pod_kwh} kWh per pod per hour"
        )
    
    def calculate_energy(
        self,
        pod_count: int,
        time_window_seconds: int
    ) -> float:
        """
        Calculate total energy consumption.
        
        Args:
            pod_count: Number of pods running
            time_window_seconds: Time window for prediction (e.g., 30 seconds, 1 hour)
        
        Returns:
            Energy consumption in kWh
        
        Example:
            >>> model = EnergyModel(energy_per_pod_kwh=0.5)
            >>> energy = model.calculate_energy(pod_count=5, time_window_seconds=3600)
            >>> print(energy)
            2.5  # 5 pods × 0.5 kWh/hr × (3600 sec / 3600) = 2.5 kWh
        """
        if pod_count < 0:
            raise ValueError(f"pod_count must be >= 0, got {pod_count}")
        
        if time_window_seconds <= 0:
            raise ValueError(f"time_window_seconds must be > 0, got {time_window_seconds}")
        
        # Convert time window to hours
        time_hours = time_window_seconds / 3600.0
        
        # Calculate energy: pods × energy_per_pod × time_hours
        energy_kwh = pod_count * self.energy_per_pod_kwh * time_hours
        
        self.logger.debug(
            f"Energy calculated: {pod_count} pods × {self.energy_per_pod_kwh} kWh/hr "
            f"× {time_hours:.4f} hr = {energy_kwh:.6f} kWh"
        )
        
        return round(energy_kwh, 6)
    
    def calculate_energy_reduction(
        self,
        reduced_pod_count: int,
        baseline_pod_count: int,
        time_window_seconds: int
    ) -> float:
        """
        Calculate energy reduction from scaling down.
        
        Args:
            reduced_pod_count: Pod count after reduction
            baseline_pod_count: Pod count before reduction
            time_window_seconds: Time window
        
        Returns:
            Energy saved in kWh
        
        Example:
            >>> model = EnergyModel(energy_per_pod_kwh=0.5)
            >>> saved = model.calculate_energy_reduction(3, 5, 3600)
            >>> print(saved)
            1.0  # (5-3) pods × 0.5 kWh/hr × 1 hr = 1.0 kWh
        """
        energy_baseline = self.calculate_energy(baseline_pod_count, time_window_seconds)
        energy_reduced = self.calculate_energy(reduced_pod_count, time_window_seconds)
        
        energy_saved = energy_baseline - energy_reduced
        
        self.logger.debug(
            f"Energy reduction: {energy_baseline:.6f} kWh → {energy_reduced:.6f} kWh "
            f"= {energy_saved:.6f} kWh saved"
        )
        
        return round(energy_saved, 6)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get current model configuration.
        
        Returns:
            Dict with model parameters
        """
        return {
            "energy_per_pod_kwh_per_hour": self.energy_per_pod_kwh,
            "model_type ": "linear_scaling",
            "assumptions": [
                "Linear scaling with pod count",
                "Time-proportional consumption",
                "No overhead factored in"
            ]
        }
