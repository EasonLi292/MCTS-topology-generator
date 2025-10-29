#!/usr/bin/env python3
"""
Debug script to understand component placement rules.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard, COMPONENT_CATALOG

# Create initial state
board = Breadboard()

print("=" * 70)
print("INITIAL BOARD STATE")
print("=" * 70)
print(f"Components: {[(c.type, c.pins) for c in board.placed_components]}")
print()

# Check which rows are active
print("Active rows:")
for r in range(board.ROWS):
    if board.is_row_active(r):
        print(f"  Row {r} is active")
print()

# Check if we can place a resistor in column 1
print("Testing component placement in column 1:")
print(f"WORK_START_ROW: {board.WORK_START_ROW}")
print(f"WORK_END_ROW: {board.WORK_END_ROW}")
print()

for comp_type, info in COMPONENT_CATALOG.items():
    if comp_type == 'wire':
        continue

    print(f"\n{comp_type} (pins: {info.pin_count}):")

    # Try some starting rows
    for start_row in [1, 2, 3, 4, 5, 10, 15, 20, 25]:
        if start_row + info.pin_count - 1 > board.WORK_END_ROW:
            continue

        can_place = board.can_place_component(comp_type, start_row, 1)
        pin_rows = list(range(start_row, start_row + info.pin_count))
        active_pins = [board.is_row_active(r) for r in pin_rows]

        print(f"  Row {start_row}: can_place={can_place}, pins={pin_rows}, active={active_pins}")

        if can_place:
            print(f"    ✓ Can place {comp_type} at row {start_row}, col 1")
            break

print()
print("=" * 70)
print("AFTER PLACING A WIRE")
print("=" * 70)

# Try placing a wire to activate more rows
board2 = board.clone()
actions = board2.legal_actions()

# Find a wire action
wire_actions = [a for a in actions if a[0] == 'wire']
if wire_actions:
    # Place a wire from VIN (row 1) to some other row
    wire_to_row5 = [a for a in wire_actions if a[1] == 1 and a[3] == 5]
    if wire_to_row5:
        action = wire_to_row5[0]
        print(f"Placing wire: {action}")
        board2.apply_action(action)

        print(f"\nActive rows after wire:")
        for r in range(board2.ROWS):
            if board2.is_row_active(r):
                print(f"  Row {r} is active")
        print()

        # Now check if we can place components
        print("Testing component placement after wire:")
        for comp_type in ['resistor', 'capacitor', 'nmos3', 'pmos3']:
            info = COMPONENT_CATALOG[comp_type]

            for start_row in [1, 2, 3, 4, 5, 6]:
                if start_row + info.pin_count - 1 > board2.WORK_END_ROW:
                    continue

                can_place = board2.can_place_component(comp_type, start_row, 1)
                if can_place:
                    print(f"  ✓ Can place {comp_type} at row {start_row}, col 1")
                    break
            else:
                print(f"  ✗ Cannot place {comp_type} in column 1")
