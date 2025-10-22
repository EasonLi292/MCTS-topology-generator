# spice_simulator.py
# SPICE simulation and reward calculation for circuit topologies

import numpy as np
import tempfile
import os

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

def run_ac_simulation(netlist: str):
    """
    Runs an AC simulation on a given netlist and returns the frequency and output voltage.
    Uses ngspice directly via subprocess for maximum compatibility.
    """
    if not PYSPICE_AVAILABLE:
        # Mock implementation for testing without PySpice
        return None, None

    try:
        import subprocess
        import re

        # Write netlist to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
            f.write(netlist)
            netlist_path = f.name

        # Run ngspice in batch mode
        result = subprocess.run(
            ['/opt/homebrew/bin/ngspice', '-b', netlist_path],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Clean up temp file
        os.unlink(netlist_path)

        if result.returncode != 0:
            # Simulation failed
            return None, None

        # Parse output to extract frequency and voltage data
        output = result.stdout

        # Check for errors
        if 'error' in output.lower() and 'incomplete or empty netlist' in output.lower():
            return None, None
        if 'fatal' in output.lower():
            return None, None

        # Parse the AC analysis table
        # Format: Index frequency v(out)
        # Example: 0	1.000000e+00	9.999605e-01,	-6.28294e-03
        frequencies = []
        voltages_real = []
        voltages_imag = []

        lines = output.split('\n')
        in_data = False
        for line in lines:
            # Look for data section (starts after "Index   frequency")
            if 'Index' in line and 'frequency' in line:
                in_data = True
                continue

            if in_data and line.strip():
                # Parse data line: Index frequency real,imag
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        freq = float(parts[1])
                        # Remove trailing comma from real part
                        real = float(parts[2].rstrip(','))
                        imag = float(parts[3])
                        frequencies.append(freq)
                        voltages_real.append(real)
                        voltages_imag.append(imag)
                    except (ValueError, IndexError):
                        # Not a data line, skip
                        continue

        if len(frequencies) == 0:
            # No valid data found
            return None, None

        # Convert to numpy arrays
        frequencies = np.array(frequencies)
        voltage = np.array(voltages_real) + 1j * np.array(voltages_imag)

        return frequencies, voltage

    except subprocess.TimeoutExpired:
        print("SPICE Error: Simulation timeout")
        return None, None
    except Exception as e:
        # A malformed netlist or simulation error means the circuit is invalid
        print(f"SPICE Error: {e}")
        return None, None

def calculate_reward_from_simulation(frequency, output_voltage):
    """
    Calculates a reward score based on the AC analysis results.

    SPICE rewards are designed to MASSIVELY DOMINATE heuristic rewards.
    Any valid, interesting circuit should get 500-5000+ points.
    """
    if frequency is None or output_voltage is None:
        return 0.0  # Failed simulation

    # Convert to Voltage Magnitude
    output_magnitude = np.abs(output_voltage)

    # Check for numerical instability (NaN or Inf values)
    if np.any(np.isnan(output_magnitude)) or np.any(np.isinf(output_magnitude)):
        return 0.0  # Just return 0 for unstable circuits

    # **Metric 1: Avoid Trivial Shorts/Opens**
    # Circuits where output is always ~0 (open) or constant (boring)
    if np.all(output_magnitude < 1e-6):
        return 10.0  # Tiny reward - circuit simulates but does nothing

    # Check if output is completely flat (boring circuit)
    if np.std(output_magnitude) < 1e-9:
        return 10.0  # Flat response = boring

    # **Metric 2: Reward Frequency Dependence** 📈
    # A circuit is "interesting" if its behavior changes with frequency.
    # Filters, amplifiers, oscillators all show frequency dependence.
    spread = np.std(output_magnitude)

    # **Metric 3: Reward Dynamic Range**
    # How much does the output vary across the frequency sweep?
    voltage_range = np.max(output_magnitude) - np.min(output_magnitude)

    # **Metric 4: Reward Non-Monotonic Behavior**
    # Circuits with peaks/valleys are more interesting than simple slopes
    # Count direction changes in the magnitude
    diff = np.diff(output_magnitude)
    sign_changes = np.sum(np.diff(np.sign(diff)) != 0)
    non_monotonic_bonus = sign_changes * 20.0  # Reward peaks and valleys

    # **Metric 5: Reward Signal Presence**
    # Any output signal at all is valuable
    mean_output = np.mean(output_magnitude)
    signal_presence_bonus = mean_output * 100.0

    # **Metric 6: MASSIVE baseline for any working circuit**
    # This ensures SPICE circuits always dominate heuristics
    baseline_reward = 100.0

    # **CRITICAL: Make SPICE rewards DOMINATE everything**
    # Typical heuristic rewards: 20-60 points
    # SPICE rewards should be: 500-5000+ points for interesting circuits

    # Spread is THE MOST IMPORTANT - filters have high spread
    spread_reward = spread * 500.0  # 10x increase from 50

    # Range also very important
    range_reward = voltage_range * 250.0  # 10x increase from 25

    # Combine all metrics
    total_reward = (baseline_reward +
                   spread_reward +
                   range_reward +
                   non_monotonic_bonus +
                   signal_presence_bonus)

    # Ensure minimum reward for any circuit that simulates
    total_reward = max(total_reward, 100.0)

    return total_reward
