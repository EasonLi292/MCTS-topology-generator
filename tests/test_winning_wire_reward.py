#!/usr/bin/env python3
"""Test what reward the winning wire gets."""
import sys
import os
# Add parent directory's core module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard
from MCTS import MCTS

def choose_row(board: Breadboard, offset: int, height: int = 1) -> int:
    """Helper to select a valid row within the work area."""
    min_start = board.WORK_START_ROW
    max_start = board.WORK_END_ROW - (height - 1)
    if max_start < min_start:
        raise ValueError("Breadboard lacks sufficient work rows")
    clamped_offset = max(0, min(offset, max_start - min_start))
    return min_start + clamped_offset


def attach_vin_via_gate(board: Breadboard, target_row: int, target_col: int, driver_col: int = 5) -> Breadboard:
    """Connect VIN to the target node through an NMOS gate."""
    driver_row = min(target_row, board.WORK_END_ROW - 2)
    board = board.apply_action(('nmos3', driver_row, driver_col))
    board = board.apply_action(('wire', board.VIN_ROW, 0, driver_row + 1, driver_col))
    board = board.apply_action(('wire', driver_row, driver_col, target_row, target_col))
    board = board.apply_action(('wire', driver_row + 2, driver_col, target_row, target_col))
    return board

# Build partial circuit
board = Breadboard()

resistor_row = choose_row(board, 3, height=2)
capacitor_row = choose_row(board, 6, height=2)

board = board.apply_action(('resistor', resistor_row, 1))        # Resistor rows
board = attach_vin_via_gate(board, resistor_row, 1, driver_col=5)
board = board.apply_action(('capacitor', capacitor_row, 1))       # Capacitor rows (same column)
board = board.apply_action(('wire', resistor_row + 1, 1, capacitor_row, 1))      # Wire resistor pin 2 to capacitor pin 1

# Add resistor from signal path to VDD in column 2
power_res_row = capacitor_row
board = board.apply_action(('resistor', power_res_row, 2))
board = board.apply_action(('wire', power_res_row, 2, capacitor_row, 1))
board = board.apply_action(('wire', power_res_row + 1, 2, board.VDD_ROW, 0))

# Add resistor from signal path to ground in column 3
ground_res_row = capacitor_row
board = board.apply_action(('resistor', ground_res_row, 3))
board = board.apply_action(('wire', ground_res_row, 3, capacitor_row + 1, 1))
board = board.apply_action(('wire', ground_res_row + 1, 3, board.VSS_ROW, 0))

print("Partial circuit built")
print(f"  Components: {len(board.placed_components)}")
print(f"  Complete: {board.is_complete_and_valid()}")
print()

# Apply the winning wire
final_board = board.apply_action(('wire', capacitor_row + 1, 1, board.VOUT_ROW, 0))  # Wire capacitor pin 2 to VOUT

print(f"After adding winning wire ({capacitor_row + 1},1) -> ({board.VOUT_ROW},0):")
print(f"  Components: {len(final_board.placed_components)}")
print(f"  Complete: {final_board.is_complete_and_valid()}")
print()

# Evaluate with MCTS reward function
from MCTS import CircuitStatistics

mcts = MCTS(initial_state=board)
stats = CircuitStatistics()
reward = mcts._evaluate_circuit(final_board, stats)

print(f"Reward for completed circuit: {reward}")
print(f"  SPICE successes: {stats.spice_success_count}")
print(f"  SPICE failures: {stats.spice_fail_count}")
print()

if final_board.is_complete_and_valid():
    netlist = final_board.to_netlist()
    if netlist:
        print("Generated netlist:")
        print(netlist)
