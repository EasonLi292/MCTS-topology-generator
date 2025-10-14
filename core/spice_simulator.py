# spice_simulator.py
# SPICE simulation and reward calculation for circuit topologies

import numpy as np

# Import the Circuit class from PySpice
try:
    from PySpice.Spice.Netlist import Circuit
    # Set the SPICE executable path if it's not in your system's PATH
    # pyspice.setup(spice_path='/path/to/your/ngspice')
    PYSPICE_AVAILABLE = True
except ImportError:
    PYSPICE_AVAILABLE = False
    print("Warning: PySpice not available. SPICE simulations will be mocked.")

def run_ac_simulation(netlist: str):
    """
    Runs an AC simulation on a given netlist and returns the frequency and output voltage.
    """
    if not PYSPICE_AVAILABLE:
        # Mock implementation for testing without PySpice
        print("Warning: Using mock SPICE simulation (PySpice not installed)")
        return None, None

    try:
        circuit = Circuit.load(netlist)
        simulator = circuit.simulator(temperature=25, nominal_temperature=25)

        # Run an AC analysis from 1 Hz to 1 MHz with 100 points per decade
        analysis = simulator.ac(start_frequency=1, stop_frequency=1e6, number_of_points=100, variation='dec')

        return analysis.frequency, analysis.vout_alias

    except Exception as e:
        # A malformed netlist or simulation error means the circuit is invalid
        # print(f"SPICE Error: {e}")
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
