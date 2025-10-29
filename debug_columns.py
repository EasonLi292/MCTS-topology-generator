#!/usr/bin/env python3
"""Debug column usage."""
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

print("Analyzing column usage:")
print()

# Find which columns have components
occupied_cols = set()
for r in range(board.ROWS):
    for c in range(board.COLUMNS):
        if not board.is_empty(r, c):
            occupied_cols.add(c)

print(f"Occupied columns: {sorted(occupied_cols)}")
print(f"Max occupied column: {max(occupied_cols)}")
print(f"Current target_col: {board._find_target_column()}")
print()

# Show what _find_target_column is doing
print("Checking each column for empty space in work area (rows 2-27):")
for c in range(1, board.COLUMNS):
    has_empty = not all(not board.is_empty(r, c) for r in range(board.WORK_START_ROW, board.WORK_END_ROW + 1))
    if has_empty:
        print(f"  Column {c}: HAS empty space <- _find_target_column returns this")
        break
    else:
        print(f"  Column {c}: fully occupied")

print()
print("The issue:")
print("  - Components are at columns 0, 1, 2")
print("  - target_col is 1 (first column with empty space)")
print("  - Wire generation only considers columns 0..target_col = 0..1")
print("  - So column 2 (where capacitor is) can't be a wire source!")
print()
print("Solution: Wire generation should use max_occupied_col, not target_col")
