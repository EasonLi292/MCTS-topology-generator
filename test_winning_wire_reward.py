#!/usr/bin/env python3
"""Test what reward the winning wire gets."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard
from MCTS import MCTS

# Build partial circuit
board = Breadboard()
board = board.apply_action(('resistor', 1, 1))
board = board.apply_action(('wire', 1, 0, 1, 1))
board = board.apply_action(('capacitor', 5, 2))
board = board.apply_action(('wire', 2, 1, 5, 2))

print("Partial circuit built")
print(f"  Components: {len(board.placed_components)}")
print(f"  Complete: {board.is_complete_and_valid()}")
print()

# Apply the winning wire
final_board = board.apply_action(('wire', 6, 2, 28, 0))

print("After adding winning wire (6,2) -> (28,0):")
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
