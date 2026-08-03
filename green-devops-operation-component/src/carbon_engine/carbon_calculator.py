"""
Carbon emission calculator for Engine 2.

Converts energy consumption to CO2 emissions using grid carbon intensity.
"""

import logging
from typing import Dict, Any
try:
    from .config import CARBON_INTENSITY_GCO2_PER_KWH
except ImportError:
    from carbon_engine.config import CARBON_INTENSITY_GCO2_PER_KWH

logger = logging.getLogger(__name__)


class CarbonCalculator:
    """
    Convert energy consumption to carbon emissions.
    
    Carbon calculation:
        carbon_gco2 = energy_kwh × carbon_intensity_gco2_per_kwh
    
    Assumptions:
    - Carbon intensity is fixed (actual varies by time/region)
    - Using US average grid mix: ~400 g CO2/kWh
    - Direct correlation between energy and emissions
    """
    
    def __init__(self, carbon_intensity: float = CARBON_INTENSITY_GCO2_PER_KWH):
        """
        Initialize carbon calculator.
        
        Args:
            carbon_intensity: Grid carbon intensity (grams CO2 per kWh)
                Default: 400 g CO2/kWh (US average)
        """
        if carbon_intensity < 0:
            raise ValueError(f"carbon_intensity must be >= 0, got {carbon_intensity}")
        
        self.carbon_intensity = carbon_intensity
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(
            f"CarbonCalculator initialized: {carbon_intensity} g CO2/kWh"
        )
    
    def calculate_carbon(self, energy_kwh: float) -> float:
        """
        Convert energy to CO2 emissions.
        
        Args:
            energy_kwh: Energy consumption in kWh
        
        Returns:
            Carbon emissions in grams CO2
        
        Example:
            >>> calc = CarbonCalculator(carbon_intensity=400)
            >>> carbon = calc.calculate_carbon(energy_kwh=2.5)
            >>> print(carbon)
            1000.0  # 2.5 kWh × 400 g CO2/kWh = 1000 g CO2
        """
        if energy_kwh < 0:
            raise ValueError(f"energy_kwh must be >= 0, got {energy_kwh}")
        
        carbon_gco2 = energy_kwh * self.carbon_intensity
        
        self.logger.debug(
            f"Carbon calculated: {energy_kwh} kWh × {self.carbon_intensity} g CO2/kWh "
            f"= {carbon_gco2:.2f} g CO2"
        )
        
        return round(carbon_gco2, 2)
    
    def calculate_carbon_reduction(
        self,
        reduced_energy_kwh: float,
        baseline_energy_kwh: float
    ) -> float:
        """
        Calculate carbon reduction from energy savings.
        
        Args:
            reduced_energy_kwh: Energy after reduction
            baseline_energy_kwh: Energy before reduction
        
        Returns:
            Carbon saved in grams CO2
        
        Example:
            >>> calc = CarbonCalculator(carbon_intensity=400)
            >>> saved = calc.calculate_carbon_reduction(1.5, 2.5)
            >>> print(saved)
            400.0  # (2.5 - 1.5) kWh × 400 g CO2/kWh = 400 g CO2
        """
        carbon_baseline = self.calculate_carbon(baseline_energy_kwh)
        carbon_reduced = self.calculate_carbon(reduced_energy_kwh)
        
        carbon_saved = carbon_baseline - carbon_reduced
        
        self.logger.debug(
            f"Carbon reduction: {carbon_baseline:.2f} g CO2 → {carbon_reduced:.2f} g CO2 "
            f"= {carbon_saved:.2f} g CO2 saved"
        )
        
        return round(carbon_saved, 2)
    
    def calculate_carbon_saving_percent(
        self,
        reduced_carbon: float,
        baseline_carbon: float
    ) -> float:
        """
        Calculate percentage carbon reduction.
        
        Args:
            reduced_carbon: Carbon emissions after reduction
            baseline_carbon: Carbon emissions before reduction
        
        Returns:
            Percentage reduction (0-100)
        
        Raises:
            ValueError if baseline_carbon is 0
        
        Example:
            >>> calc = CarbonCalculator()
            >>> pct = calc.calculate_carbon_saving_percent(600, 1000)
            >>> print(pct)
            40.0  # (1000 - 600) / 1000 × 100 = 40%
        """
        if baseline_carbon == 0:
            if reduced_carbon == 0:
                return 0.0
            raise ValueError("Cannot calculate percentage reduction from zero baseline")
        
        percent_saved = ((baseline_carbon - reduced_carbon) / baseline_carbon) * 100.0
        
        self.logger.debug(
            f"Carbon saving: {baseline_carbon:.2f} g CO2 → {reduced_carbon:.2f} g CO2 "
            f"= {percent_saved:.1f}% reduction"
        )
        
        return round(percent_saved, 1)
    
    def convert_gco2_to_kg(self, carbon_gco2: float) -> float:
        """
        Convert grams CO2 to kilograms CO2.
        
        Args:
            carbon_gco2: Carbon in grams
        
        Returns:
            Carbon in kilograms
        """
        return round(carbon_gco2 / 1000.0, 6)
    
    def convert_gco2_to_tons(self, carbon_gco2: float) -> float:
        """
        Convert grams CO2 to metric tons CO2.
        
        Args:
            carbon_gco2: Carbon in grams
        
        Returns:
            Carbon in metric tons
        """
        return round(carbon_gco2 / 1_000_000.0, 6)
    
    def get_calculator_info(self) -> Dict[str, Any]:
        """
        Get current calculator configuration.
        
        Returns:
            Dict with calculator parameters
        """
        return {
            "carbon_intensity_gco2_per_kwh": self.carbon_intensity,
            "carbon_intensity_description": self._get_intensity_description(),
            "conversion_factors": {
                "gco2_per_kwh": self.carbon_intensity,
                "kg_co2_per_kwh": self.carbon_intensity / 1000,
                "tons_co2_per_kwh": self.carbon_intensity / 1_000_000
            }
        }
    
    def _get_intensity_description(self) -> str:
        """Return description of carbon intensity value."""
        if self.carbon_intensity < 200:
            return "Very clean grid (renewable-heavy)"
        elif self.carbon_intensity < 400:
            return "Clean-to-moderate grid"
        elif self.carbon_intensity < 600:
            return "Moderate grid (mixed sources)"
        elif self.carbon_intensity < 800:
            return "Carbon-heavy grid"
        else:
            return "Very carbon-heavy grid (coal-dependent)"
