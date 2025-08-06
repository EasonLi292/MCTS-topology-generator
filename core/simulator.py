"""Utilities for simulating generated circuits via PySpice."""

from typing import Optional
import PySpice

# ``Breadboard`` lives in the same package; use a relative import so that
# this module works whether ``core`` is imported as a package or executed
# directly from the repository root.
from .topology_game_board import Breadboard

def generate_netlist(breadboard: Breadboard) -> str:
    """Converts Breadboard to SPICE netlist."""
    netlist_lines = []
    # Add components, nodes, etc.
    return "\n".join(netlist_lines)

def evaluate_circuit(breadboard: Breadboard) -> float:
    """Runs PySpice simulation and returns reward."""
    netlist = generate_netlist(breadboard)
    try:
        # Configure PySpice simulation
        simulator = PySpice.Spice.Netlist.Circuit(netlist)
        analysis = simulator.ac(...)
        return _calculate_reward(analysis)
    except Exception as e:
        return 0.0

def _calculate_reward(analysis) -> float: ...