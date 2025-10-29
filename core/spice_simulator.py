"""
SPICE simulation and reward calculation for circuit topologies.

This module handles running ngspice simulations on circuit netlists and
calculating reward scores based on the electrical behavior of circuits.

Refactored to follow SOLID principles with focused, well-documented functions.
"""

import numpy as np
import tempfile
import os
import subprocess
import re
from typing import Optional, Tuple

# Set library path for ngspice before importing PySpice
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')

# Import the Circuit class from PySpice
try:
    from PySpice.Spice.Netlist import Circuit
    from PySpice.Spice.NgSpice.Shared import NgSpiceShared
    PYSPICE_AVAILABLE = True
except ImportError as e:
    PYSPICE_AVAILABLE = False
    print(f"Warning: PySpice not available: {e}")

def run_ac_simulation(netlist: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Runs an AC simulation on a given netlist and returns the frequency and output voltage.

    Uses ngspice directly via subprocess for maximum compatibility.

    Args:
        netlist: SPICE netlist string

    Returns:
        Tuple of (frequencies, complex_voltages) or (None, None) if simulation fails
    """
    if not PYSPICE_AVAILABLE:
        # Mock implementation for testing without PySpice
        return None, None

    try:
        # Write netlist to temporary file
        netlist_path = _write_netlist_to_file(netlist)

        # Run ngspice simulation
        output = _run_ngspice(netlist_path)

        # Clean up temporary file
        os.unlink(netlist_path)

        # Parse simulation results
        if output is None:
            return None, None

        return _parse_ac_results(output)

    except subprocess.TimeoutExpired:
        print("SPICE Error: Simulation timeout")
        return None, None
    except Exception as e:
        # A malformed netlist or simulation error means the circuit is invalid
        print(f"SPICE Error: {e}")
        return None, None


def _write_netlist_to_file(netlist: str) -> str:
    """
    Writes netlist to a temporary file.

    Args:
        netlist: SPICE netlist string

    Returns:
        Path to temporary file
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
        f.write(netlist)
        return f.name


def _run_ngspice(netlist_path: str) -> Optional[str]:
    """
    Runs ngspice in batch mode on a netlist file.

    Args:
        netlist_path: Path to netlist file

    Returns:
        Simulation output string, or None if simulation failed
    """
    result = subprocess.run(
        ['/opt/homebrew/bin/ngspice', '-b', netlist_path],
        capture_output=True,
        text=True,
        timeout=5
    )

    # Check if simulation failed
    if result.returncode != 0:
        return None

    # Check for fatal errors in output
    if _has_fatal_errors(result.stdout):
        return None

    return result.stdout


def _has_fatal_errors(output: str) -> bool:
    """
    Checks if simulation output contains fatal errors.

    Args:
        output: ngspice output string

    Returns:
        True if fatal errors are present
    """
    output_lower = output.lower()

    # Check for incomplete/empty netlist
    if 'error' in output_lower and 'incomplete or empty netlist' in output_lower:
        return True

    # Check for fatal errors
    if 'fatal' in output_lower:
        return True

    return False


def _parse_ac_results(output: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Parses AC analysis results from ngspice output.

    The output format is:
        Index   frequency       v(out)
        0       1.000000e+00    9.999605e-01,   -6.28294e-03
        ...

    Args:
        output: ngspice output string

    Returns:
        Tuple of (frequency_array, complex_voltage_array) or (None, None) if parsing fails
    """
    frequencies = []
    voltages_real = []
    voltages_imag = []

    lines = output.split('\n')
    in_data_section = False

    for line in lines:
        # Look for data section header
        if 'Index' in line and 'frequency' in line:
            in_data_section = True
            continue

        # Parse data lines
        if in_data_section and line.strip():
            parsed_values = _parse_ac_data_line(line)
            if parsed_values:
                freq, real, imag = parsed_values
                frequencies.append(freq)
                voltages_real.append(real)
                voltages_imag.append(imag)

    # Check if we got any valid data
    if len(frequencies) == 0:
        return None, None

    # Convert to numpy arrays and combine into complex voltage
    freq_array = np.array(frequencies)
    voltage_array = np.array(voltages_real) + 1j * np.array(voltages_imag)

    return freq_array, voltage_array


def _parse_ac_data_line(line: str) -> Optional[Tuple[float, float, float]]:
    """
    Parses a single AC data line.

    Expected format: Index frequency real,imag
    Example: 0  1.000000e+00  9.999605e-01,  -6.28294e-03

    Args:
        line: Data line string

    Returns:
        Tuple of (frequency, real_voltage, imaginary_voltage) or None if parsing fails
    """
    parts = line.split()

    # Need at least 4 parts: index, frequency, real, imag
    if len(parts) < 4:
        return None

    try:
        freq = float(parts[1])
        # Remove trailing comma from real part
        real = float(parts[2].rstrip(','))
        imag = float(parts[3])
        return (freq, real, imag)
    except (ValueError, IndexError):
        # Not a valid data line
        return None

def calculate_reward_from_simulation(frequency: Optional[np.ndarray],
                                    output_voltage: Optional[np.ndarray]) -> float:
    """
    Calculates a reward score based on the AC analysis results.

    SPICE rewards are designed to MASSIVELY DOMINATE heuristic rewards.
    Any valid, interesting circuit should get 100-5000+ points.

    The reward is based on multiple metrics:
    1. Baseline reward for any working circuit
    2. Frequency-dependent behavior (spread/standard deviation)
    3. Dynamic range (variation in output)
    4. Non-monotonic behavior (peaks and valleys)
    5. Signal presence (non-zero output)

    Args:
        frequency: Array of frequency points (Hz)
        output_voltage: Array of complex output voltages

    Returns:
        Reward score (0 if simulation failed, 100+ for valid circuits)
    """
    # Check for failed simulation
    if frequency is None or output_voltage is None:
        return 0.0

    # Convert to voltage magnitude
    output_magnitude = np.abs(output_voltage)

    # Check for numerical instability
    if _has_numerical_instability(output_magnitude):
        return 0.0

    # Check for trivial/boring circuits
    trivial_reward = _check_trivial_circuit(output_magnitude)
    if trivial_reward is not None:
        return trivial_reward

    # Calculate individual reward metrics
    spread_reward = _calculate_spread_reward(output_magnitude)
    range_reward = _calculate_range_reward(output_magnitude)
    non_monotonic_bonus = _calculate_non_monotonic_bonus(output_magnitude)
    signal_presence_bonus = _calculate_signal_presence_bonus(output_magnitude)

    # Baseline reward for any working circuit
    baseline_reward = 100.0

    # Combine all metrics
    total_reward = (baseline_reward +
                   spread_reward +
                   range_reward +
                   non_monotonic_bonus +
                   signal_presence_bonus)

    # Ensure minimum reward for any circuit that simulates
    return max(total_reward, 100.0)


def _has_numerical_instability(magnitude: np.ndarray) -> bool:
    """
    Checks if the voltage magnitude has numerical instability (NaN or Inf).

    Args:
        magnitude: Array of voltage magnitudes

    Returns:
        True if unstable
    """
    return np.any(np.isnan(magnitude)) or np.any(np.isinf(magnitude))


def _check_trivial_circuit(magnitude: np.ndarray) -> Optional[float]:
    """
    Checks if circuit is trivial (no output or flat response).

    Args:
        magnitude: Array of voltage magnitudes

    Returns:
        Small reward if circuit is trivial, None if circuit is non-trivial
    """
    # Check for no output (open circuit)
    if np.all(magnitude < 1e-6):
        return 10.0  # Tiny reward - circuit simulates but does nothing

    # Check for completely flat response (boring circuit)
    if np.std(magnitude) < 1e-9:
        return 10.0  # Flat response = boring

    return None  # Circuit is non-trivial


def _calculate_spread_reward(magnitude: np.ndarray) -> float:
    """
    Calculates reward for frequency-dependent behavior.

    Circuits with high standard deviation show interesting frequency dependence
    (e.g., filters, resonators).

    Args:
        magnitude: Array of voltage magnitudes

    Returns:
        Reward score for spread
    """
    spread = np.std(magnitude)
    # Spread is THE MOST IMPORTANT - filters have high spread
    return spread * 500.0


def _calculate_range_reward(magnitude: np.ndarray) -> float:
    """
    Calculates reward for dynamic range.

    How much does the output vary across the frequency sweep?

    Args:
        magnitude: Array of voltage magnitudes

    Returns:
        Reward score for range
    """
    voltage_range = np.max(magnitude) - np.min(magnitude)
    # Range also very important
    return voltage_range * 250.0


def _calculate_non_monotonic_bonus(magnitude: np.ndarray) -> float:
    """
    Calculates bonus for non-monotonic behavior.

    Circuits with peaks/valleys are more interesting than simple slopes.
    Counts direction changes in the magnitude.

    Args:
        magnitude: Array of voltage magnitudes

    Returns:
        Bonus score for non-monotonic behavior
    """
    # Calculate differences between consecutive points
    diff = np.diff(magnitude)

    # Count sign changes (direction reversals)
    sign_changes = np.sum(np.diff(np.sign(diff)) != 0)

    # Reward peaks and valleys
    return sign_changes * 20.0


def _calculate_signal_presence_bonus(magnitude: np.ndarray) -> float:
    """
    Calculates bonus for signal presence.

    Any output signal at all is valuable.

    Args:
        magnitude: Array of voltage magnitudes

    Returns:
        Bonus score for signal presence
    """
    mean_output = np.mean(magnitude)
    return mean_output * 100.0
