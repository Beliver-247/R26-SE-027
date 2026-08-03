
"""
energy_calculator.py
====================
Calculates energy consumption (kWh) from deployment profiling data.

Takes profiler.py output (CPU/Memory utilization percentages, duration)
and estimates electrical energy consumption based on server specifications.

Formula:
    Energy (kWh) = Power (kW) × Time (hours)
    Power = Baseline + (CPU_factor × CPU_util%) + (Memory_factor × Memory_util%)
"""

from __future__ import annotations
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# ─── Server Specifications ────────────────────────────────────────────────────
# Adjust these for YOUR server hardware
# You can find actual values using: 
#   - CPU model: lscpu | grep "Model name"
#   - TDP: Check manufacturer specs for your CPU model

SERVER_SPECS = {
    # CPU
    "cpu_model": "12th Gen Intel Core i5-1235U",
    "cpu_tdp_watts": 15.0,           # Base TDP in watts (U-series typically 15W)
    "cpu_max_tdp_watts": 55.0,       # Max turbo TDP
    "cpu_power_range": (1.0, 55.0),  # (idle_watts, max_watts)
    
    # Memory (DDR4/DDR5)
    "memory_type": "DDR4",
    "memory_power_per_gb_watts": 0.375,  # ~3W per 8GB DIMM
    
    # Network
    "network_power_per_gb_watts": 0.05,  # ~0.05W per GB transferred (estimate)
    
    # Baseline (motherboard, fans, SSD, etc. — always draws power)
    "baseline_power_watts": 10.0,
    
    # Power Supply Efficiency
    "psu_efficiency": 0.85,  # 85% efficiency typical for laptop PSU
    
    # Cooling overhead (laptops: minimal; servers: 1.3-1.5x)
    "cooling_multiplier": 1.05,  # 5% for fan cooling
}


# ─── Power Calculation Functions ──────────────────────────────────────────────

def calculate_cpu_power(cpu_util_percent: float, specs: Optional[Dict] = None) -> float:
    """
    Estimate CPU power draw based on utilization %.
    
    Uses linear interpolation between idle and max TDP.
    
    Args:
        cpu_util_percent: CPU utilization as percentage (0-100)
        specs: Server specifications dict (uses SERVER_SPECS if None)
    
    Returns:
        Estimated CPU power in watts
    """
    specs = specs or SERVER_SPECS
    
    idle_watts, max_watts = specs["cpu_power_range"]
    cpu_tdp = specs["cpu_tdp_watts"]
    
    # CPU power scales roughly linearly with utilization
    # At 0% util: idle power (~1W for modern CPUs)
    # At 100% util: max TDP
    utilization_factor = cpu_util_percent / 100.0
    estimated_power = idle_watts + (cpu_tdp - idle_watts) * utilization_factor
    
    # Clamp to reasonable range
    estimated_power = max(idle_watts, min(estimated_power, specs["cpu_max_tdp_watts"]))
    
    return round(estimated_power, 4)


def calculate_memory_power(memory_gb: float, specs: Optional[Dict] = None) -> float:
    """
    Estimate memory power draw.
    
    Args:
        memory_gb: Memory in use (GB)
        specs: Server specifications dict
    
    Returns:
        Estimated memory power in watts
    """
    specs = specs or SERVER_SPECS
    
    watts_per_gb = specs.get("memory_power_per_gb_watts", 0.375)
    estimated_power = memory_gb * watts_per_gb
    
    return round(estimated_power, 4)


def calculate_network_power(network_gb: float, duration_hours: float, 
                           specs: Optional[Dict] = None) -> float:
    """
    Estimate network-related energy consumption.
    
    Args:
        network_gb: Data transferred in GB
        duration_hours: Duration of transfer in hours
        specs: Server specifications dict
    
    Returns:
        Total network energy in kWh
    """
    specs = specs or SERVER_SPECS
    
    watts_per_gb_per_second = specs.get("network_power_per_gb_watts", 0.05)
    
    # Network energy is proportional to data transferred
    # 0.05W per GB/s = energy needed for transmitting 1GB
    # For total data transferred over duration, calculate average power
    avg_power_watts = network_gb * watts_per_gb_per_second / 3600  # Per second rate
    energy_kwh = (avg_power_watts * duration_hours) / 1000
    
    return round(energy_kwh, 10)


def calculate_total_energy(
    deployment_metrics: Dict,
    specs: Optional[Dict] = None
) -> Dict:
    """
    Calculate total energy consumption for a deployment.
    
    Args:
        deployment_metrics: Dict from profiler.py containing:
            - duration_minutes: Deployment duration
            - avg_cpu: Average CPU utilization %
            - avg_memory: Average memory utilization %
            - network_gb (optional): Network data transferred in GB
        specs: Server specifications dict
    
    Returns:
        {
            "duration_hours": float,
            "cpu_energy_kwh": float,
            "memory_energy_kwh": float,
            "network_energy_kwh": float,
            "baseline_energy_kwh": float,
            "total_energy_kwh": float,
            "breakdown_percent": {
                "cpu": float,
                "memory": float,
                "network": float,
                "baseline": float
            }
        }
    """
    specs = specs or SERVER_SPECS
    
    # Extract metrics
    duration_minutes = deployment_metrics.get("duration_minutes", 0)
    avg_cpu = deployment_metrics.get("avg_cpu", 0)
    avg_memory = deployment_metrics.get("avg_memory", 0)
    network_gb = deployment_metrics.get("network_gb", 0)
    
    # Convert duration to hours
    duration_hours = duration_minutes / 60.0
    
    # 1. CPU Energy
    cpu_power_watts = calculate_cpu_power(avg_cpu, specs)
    cpu_energy_kwh = (cpu_power_watts * duration_hours) / 1000
    
    # 2. Memory Energy
    # Convert memory % to GB if total RAM is known
    # Assuming 16GB total RAM (adjust based on your system)
    total_ram_gb = 16.0  # Run: free -h to check
    memory_gb = (avg_memory / 100.0) * total_ram_gb if avg_memory <= 100 else avg_memory
    memory_power_watts = calculate_memory_power(memory_gb, specs)
    memory_energy_kwh = (memory_power_watts * duration_hours) / 1000
    
    # 3. Network Energy
    network_energy_kwh = calculate_network_power(network_gb, duration_hours, specs)
    
    # 4. Baseline Energy (always-on components)
    baseline_power_watts = specs.get("baseline_power_watts", 10.0)
    baseline_energy_kwh = (baseline_power_watts * duration_hours) / 1000
    
    # 5. Total Energy (with PSU efficiency and cooling overhead)
    raw_total_kwh = cpu_energy_kwh + memory_energy_kwh + network_energy_kwh + baseline_energy_kwh
    
    # Account for PSU efficiency loss
    psu_efficiency = specs.get("psu_efficiency", 0.85)
    total_energy_kwh = raw_total_kwh / psu_efficiency
    
    # Account for cooling overhead
    cooling_multiplier = specs.get("cooling_multiplier", 1.0)
    total_energy_kwh *= cooling_multiplier
    
    # Calculate percentage breakdown
    total = total_energy_kwh if total_energy_kwh > 0 else 1  # Avoid division by zero
    breakdown = {
        "cpu": round((cpu_energy_kwh / total) * 100, 1),
        "memory": round((memory_energy_kwh / total) * 100, 1),
        "network": round((network_energy_kwh / total) * 100, 1),
        "baseline": round((baseline_energy_kwh / total) * 100, 1),
    }
    
    return {
        "duration_hours": round(duration_hours, 4),
        "cpu_power_watts": cpu_power_watts,
        "cpu_energy_kwh": round(cpu_energy_kwh, 10),
        "memory_power_watts": memory_power_watts,
        "memory_energy_kwh": round(memory_energy_kwh, 10),
        "network_energy_kwh": round(network_energy_kwh, 10),
        "baseline_energy_kwh": round(baseline_energy_kwh, 10),
        "total_energy_kwh": round(total_energy_kwh, 10),
        "breakdown_percent": breakdown,
        "psu_efficiency": psu_efficiency,
        "cooling_multiplier": cooling_multiplier,
    }


# ─── Utility: Estimate your server specs ──────────────────────────────────────

def estimate_server_specs():
    """
    Try to auto-detect server specifications.
    Run this to get values for SERVER_SPECS.
    """
    import subprocess
    import re
    
    print("=" * 60)
    print("  Server Hardware Detection")
    print("=" * 60)
    
    try:
        # CPU Info
        result = subprocess.run(['lscpu'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'Model name' in line:
                cpu_model = line.split(':')[1].strip()
                print(f"\n  CPU Model: {cpu_model}")
            if 'CPU MHz' in line:
                cpu_mhz = line.split(':')[1].strip()
                print(f"  CPU MHz: {cpu_mhz}")
        
        # Memory Info
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'Mem:' in line:
                total_ram = line.split()[1]
                print(f"\n  Total RAM: {total_ram}")
        
        # CPU TDP estimation based on model
        if 'i5-1235U' in cpu_model:
            print(f"  Estimated TDP: 15W (base) / 55W (turbo)")
            print(f"  CPU Family: Alder Lake U-series (15W)")
        elif 'i7' in cpu_model and 'U' in cpu_model:
            print(f"  Estimated TDP: 15-28W (U-series)")
        elif 'i5' in cpu_model and 'U' in cpu_model:
            print(f"  Estimated TDP: 15W (U-series)")
        elif 'i9' in cpu_model:
            print(f"  Estimated TDP: 45-125W (H-series)")
        
        print("\n  Suggested SERVER_SPECS:")
        print("  {")
        print(f'      "cpu_model": "{cpu_model}",')
        print('      "cpu_tdp_watts": 15.0,  # Adjust based on your CPU')
        print('      "baseline_power_watts": 10.0,  # Motherboard + fans + SSD')
        print('      "psu_efficiency": 0.85,  # Laptop adapter efficiency')
        print('      "cooling_multiplier": 1.05,  # Minimal for laptops')
        print("  }")
        
    except Exception as e:
        print(f"  Could not auto-detect: {e}")
        print("  Please manually set SERVER_SPECS based on your hardware")
    
    print("\n" + "=" * 60)


# ─── Self-test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  energy_calculator.py — self-test")
    print("=" * 60)
    
    # Test 1: CPU power calculation
    print("\n[Test 1] CPU Power at different utilizations:")
    for util in [0, 25, 50, 75, 100]:
        power = calculate_cpu_power(util)
        print(f"  CPU {util}% → {power}W")
    
    # Test 2: Full deployment energy calculation
    print("\n[Test 2] Full deployment energy calculation:")
    sample_metrics = {
        "duration_minutes": 10.0,
        "avg_cpu": 45.0,
        "avg_memory": 6.5,
        "network_gb": 0.1,
    }
    
    energy = calculate_total_energy(sample_metrics)
    print(f"  Duration: {energy['duration_hours']:.4f} hours")
    print(f"  CPU Energy: {energy['cpu_energy_kwh']:.10f} kWh")
    print(f"  Memory Energy: {energy['memory_energy_kwh']:.10f} kWh")
    print(f"  Network Energy: {energy['network_energy_kwh']:.10f} kWh")
    print(f"  Baseline Energy: {energy['baseline_energy_kwh']:.10f} kWh")
    print(f"  TOTAL: {energy['total_energy_kwh']:.10f} kWh")
    print(f"  Breakdown: {energy['breakdown_percent']}")
    
    # Test 3: Hardware detection
    print("\n[Test 3] Hardware detection:")
    estimate_server_specs()
    
    print("\n✅ energy_calculator.py tests complete.\n")
