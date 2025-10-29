#!/usr/bin/env python3
"""
Debug script to understand why MCTS isn't placing components.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard

# Create initial state
board = Breadboard()

print("=" * 70)
print("INITIAL BOARD STATE")
print("=" * 70)
print(f"Is complete: {board.is_complete_and_valid()}")
print(f"Number of components: {len(board.placed_components)}")
print(f"Components: {[(c.type, c.pins) for c in board.placed_components]}")
print()

# Get legal actions
actions = board.legal_actions()
print(f"Number of legal actions: {len(actions)}")
print()

# Show some sample actions
print("First 10 actions:")
for i, action in enumerate(actions[:10]):
    print(f"  {i+1}. {action}")
print()

# Try placing VIN
vin_actions = [a for a in actions if 'vin' in str(a).lower()]
if vin_actions:
    print(f"VIN actions available: {len(vin_actions)}")
    print(f"First VIN action: {vin_actions[0]}")

    # Apply first VIN action
    board2 = board.clone()
    board2.apply_action(vin_actions[0])

    print(f"\nAfter placing VIN:")
    print(f"  Components: {len(board2.placed_components)}")
    print(f"  Component types: {[c.type for c in board2.placed_components]}")
    print(f"  Is complete: {board2.is_complete_and_valid()}")

    # Get next legal actions
    actions2 = board2.legal_actions()
    print(f"  Legal actions: {len(actions2)}")

    # Show some next actions
    vout_actions = [a for a in actions2 if 'vout' in str(a).lower()]
    if vout_actions:
        print(f"  VOUT actions available: {len(vout_actions)}")
        print(f"  First VOUT action: {vout_actions[0]}")

        # Apply VOUT
        board3 = board2.clone()
        board3.apply_action(vout_actions[0])

        print(f"\n  After placing VOUT:")
        print(f"    Components: {len(board3.placed_components)}")
        print(f"    Component types: {[c.type for c in board3.placed_components]}")
        print(f"    Is complete: {board3.is_complete_and_valid()}")

        # Get next actions
        actions3 = board3.legal_actions()
        print(f"    Legal actions: {len(actions3)}")

        # Show component actions
        comp_actions = [a for a in actions3 if a[0] not in ['vin', 'vout', 'wire']]
        print(f"    Non-wire component actions: {len(comp_actions)}")
        if comp_actions:
            print(f"    Sample component actions:")
            for i, action in enumerate(comp_actions[:5]):
                print(f"      {i+1}. {action}")

print()
print("=" * 70)
print("NETLIST GENERATION TEST")
print("=" * 70)

# Try the simplest complete circuit: VIN -> wire -> VOUT
board_simple = Breadboard()
actions = board_simple.legal_actions()

# Place VIN
vin_actions = [a for a in actions if a[0] == 'vin']
if vin_actions:
    board_simple.apply_action(vin_actions[0])
    print(f"Placed VIN at {vin_actions[0]}")

    actions = board_simple.legal_actions()
    vout_actions = [a for a in actions if a[0] == 'vout']

    if vout_actions:
        board_simple.apply_action(vout_actions[0])
        print(f"Placed VOUT at {vout_actions[0]}")

        print(f"\nBoard state:")
        print(f"  Components: {len(board_simple.placed_components)}")
        print(f"  Types: {[c.type for c in board_simple.placed_components]}")
        print(f"  Is complete: {board_simple.is_complete_and_valid()}")

        if board_simple.is_complete_and_valid():
            netlist = board_simple.to_netlist()
            if netlist:
                print(f"\nGenerated netlist:")
                print(netlist)
            else:
                print("\nNetlist generation returned None")
        else:
            print("\nCircuit not complete yet")
