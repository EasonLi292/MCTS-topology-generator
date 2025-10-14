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
    """
    if frequency is None or output_voltage is None:
        return 0.0  # Failed simulation

    # Convert to Voltage Magnitude
    output_magnitude = np.abs(output_voltage)

    # Check for numerical instability (NaN or Inf values)
    if np.any(np.isnan(output_magnitude)) or np.any(np.isinf(output_magnitude)):
        return -5.0  # Penalize unstable circuits

    # **Metric 1: Avoid Trivial Shorts/Opens**
    # Punish circuits where the output is always ~0 (open) or ~1 (short to input)
    if np.all(output_magnitude < 1e-6) or np.all(np.isclose(output_magnitude, 1.0)):
        return 0.01  # Give a tiny reward to distinguish from failed sims

    # **Metric 2: Reward Frequency Dependence** 📈
    # A circuit is "interesting" if its behavior changes with frequency.
    # We can measure this with the standard deviation of the output magnitude.
    # A flat response (boring) will have a low std dev. A filter (interesting) will have a high std dev.
    spread = np.std(output_magnitude)

    # **Metric 3: Reward Attenuation/Gain**
    # Reward circuits where the output isn't just the input.
    # We can use the range of the output magnitude.
    voltage_range = np.max(output_magnitude) - np.min(output_magnitude)

    # Combine metrics for a final score
    # The spread is the most important factor for finding filters.
    reward = (spread * 10) + (voltage_range * 5)

    return reward
