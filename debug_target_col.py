#!/usr/bin/env python3
"""Debug target_col in partial circuit."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard

# Build partial circuit
board = Breadboard()
board = board.apply_action(('resistor', 1, 1))
board = board.apply_action(('wire', 1, 0, 1, 1))
board = board.apply_action(('capacitor', 5, 2))
board = board.apply_action(('wire', 2, 1, 5, 2))

print("Partial circuit built")
print(f"Components: {len(board.placed_components)}")

# Check target_col
target_col = board._find_target_column()
print(f"\nTarget column: {target_col}")

# Check what rows/cols are occupied
print("\nOccupied positions:")
for r in range(board.ROWS):
    for c in range(board.COLUMNS):
        if not board.is_empty(r, c):
            comp, pin_idx = board.grid[r][c]
            print(f"  ({r},{c}): {comp.type}")

print(f"\nVOUT position: {[(c.pins[0]) for c in board.placed_components if c.type == 'vout']}")
print(f"Capacitor bottom: (6, 2)")
print(f"\nWire (6,2) -> (28,0) needs to connect from col 2 to col 0")
print(f"But target_col is {target_col}, so wire targets are limited to col 0..{target_col}")
print(f"Since VOUT is at col 0, this should work...")

# Check what wire targets are actually generated
target_points = {(r, c) for c in range(target_col + 1) for r in range(board.ROWS)}
print(f"\nTotal target points generated: {len(target_points)}")
print(f"Is (28,0) in target_points? {(28,0) in target_points}")

# Check source points
source_points = {(r, c) for c in range(target_col + 1)
                for r in range(board.ROWS) if board.is_row_active(r)}
print(f"\nTotal source points generated: {len(source_points)}")
print(f"Is (6,2) in source_points? {(6,2) in source_points}")

# The issue: check the comparison
r1, c1 = 6, 2
r2, c2 = 28, 0
print(f"\nChecking wire ordering rule:")
print(f"  (r1,c1) = ({r1},{c1})")
print(f"  (r2,c2) = ({r2},{c2})")
print(f"  (r1,c1) >= (r2,c2)? {(r1, c1) >= (r2, c2)}")
print(f"  This means the wire would be SKIPPED due to ordering check!")
