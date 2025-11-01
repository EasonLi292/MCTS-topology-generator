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

# Build partial circuit
board = Breadboard()

resistor_row = choose_row(board, 3, height=2)
capacitor_row = choose_row(board, 6, height=2)

board = board.apply_action(('resistor', resistor_row, 1))        # Resistor rows
board = board.apply_action(('wire', board.VIN_ROW, 0, resistor_row, 1))      # Wire VIN to resistor pin 1
board = board.apply_action(('capacitor', capacitor_row, 1))       # Capacitor rows (same column)
board = board.apply_action(('wire', resistor_row + 1, 1, capacitor_row, 1))      # Wire resistor pin 2 to capacitor pin 1

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
