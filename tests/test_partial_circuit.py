#!/usr/bin/env python3
"""
Test MCTS ability to complete a partially-built circuit.

We'll build: VIN -> Resistor -> [MISSING CAPACITOR] -> VOUT
Then let MCTS try to complete it.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard
from MCTS import MCTS

print("="*70)
print("BUILDING PARTIAL CIRCUIT")
print("="*70)

# Build partial circuit: VIN -> Resistor -> (need to add capacitor) -> VOUT
board = Breadboard()

print("\nStep 1: Place resistor at (1,1)-(2,1)")
board = board.apply_action(('resistor', 1, 1))
print(f"  Resistor placed: {[c for c in board.placed_components if c.type == 'resistor']}")

print("\nStep 2: Wire VIN (1,0) to resistor top pin (1,1)")
board = board.apply_action(('wire', 1, 0, 1, 1))
print("  Wire placed")

print("\nStep 3: Place capacitor at (5,2)-(6,2)")
board = board.apply_action(('capacitor', 5, 2))
print(f"  Capacitor placed: {[c for c in board.placed_components if c.type == 'capacitor']}")

print("\nStep 4: Wire resistor bottom (2,1) to capacitor top (5,2)")
board = board.apply_action(('wire', 2, 1, 5, 2))
print("  Wire placed")

print("\n--- CIRCUIT IS ALMOST COMPLETE ---")
print("Missing: Wire from capacitor bottom (6,2) to VOUT (28,0)")

# Check current state
print(f"\nCurrent state:")
print(f"  Total components: {len(board.placed_components)}")
print(f"  Non-wire components: {len([c for c in board.placed_components if c.type not in ['wire', 'vin', 'vout']])}")
print(f"  Circuit complete: {board.is_complete_and_valid()}")

# Check what we need
position_to_net = board._build_net_mapping()
vin_comp = next((c for c in board.placed_components if c.type == 'vin'), None)
vout_comp = next((c for c in board.placed_components if c.type == 'vout'), None)

vin_net = position_to_net[vin_comp.pins[0]]
vout_net = position_to_net[vout_comp.pins[0]]

print(f"\n  VIN net: {vin_net}")
print(f"  VOUT net: {vout_net}")
print(f"  Capacitor bottom (6,2) net: {position_to_net.get((6,2), '?')}")
print(f"  Connected: {vin_net == vout_net}")

# Check legal actions - should include the wire we need
actions = board.legal_actions()
print(f"\nLegal actions available: {len(actions)}")

# Look for the winning move
winning_wire = ('wire', 6, 2, 28, 0)
if winning_wire in actions:
    print(f"✓ Winning wire IS available: {winning_wire}")
else:
    print(f"✗ Winning wire NOT in actions")
    # Check if similar wires exist
    wires_from_6_2 = [a for a in actions if a[0] == 'wire' and a[1] == 6 and a[2] == 2]
    wires_to_28_0 = [a for a in actions if a[0] == 'wire' and a[3] == 28 and a[4] == 0]
    print(f"  Wires from (6,2): {len(wires_from_6_2)}")
    print(f"  Wires to (28,0): {len(wires_to_28_0)}")

    # Why isn't this wire allowed? Let's check
    print(f"\n  Checking can_place_wire(6, 2, 28, 0):")
    can_place = board.can_place_wire(6, 2, 28, 0)
    print(f"  Result: {can_place}")

    if not can_place:
        # Debug why
        print(f"  Debug info:")
        print(f"    Row 6 active: {board.is_row_active(6)}")
        print(f"    Row 28 active: {board.is_row_active(28)}")
        print(f"    At least one active: {board.is_row_active(6) or board.is_row_active(28)}")

print("\n" + "="*70)
print("RUNNING MCTS TO COMPLETE CIRCUIT")
print("="*70)

# Run MCTS from this state
mcts = MCTS(initial_state=board)

print(f"\nRunning MCTS search for {5000} iterations...")
mcts.search(5000)

# Get best solution
path, reward = mcts.get_best_solution()

print("\n" + "="*70)
print("RESULTS")
print("="*70)

print(f"\nBest path length: {len(path)} actions")
print(f"Average reward: {reward:.2f}")

print(f"\nActions taken:")
for i, action in enumerate(path, 1):
    print(f"  {i}. {action}")

# Reconstruct the final board by applying the path
final_board = board
for action in path:
    final_board = final_board.apply_action(action)

print(f"\nFinal board state:")
print(f"  Total components: {len(final_board.placed_components)}")
print(f"  Non-wire components: {len([c for c in final_board.placed_components if c.type not in ['wire', 'vin', 'vout']])}")
print(f"  Circuit complete: {final_board.is_complete_and_valid()}")

if final_board.is_complete_and_valid():
    print("\n✓ SUCCESS! Circuit completed!")

    netlist = final_board.to_netlist()
    if netlist:
        print("\nGenerated netlist:")
        print("-"*70)
        print(netlist)
        print("-"*70)
else:
    print("\n✗ Circuit not completed yet")

    # Debug info
    position_to_net = final_board._build_net_mapping()
    vin_comp = next((c for c in final_board.placed_components if c.type == 'vin'), None)
    vout_comp = next((c for c in final_board.placed_components if c.type == 'vout'), None)

    if vin_comp and vout_comp:
        vin_net = position_to_net[vin_comp.pins[0]]
        vout_net = position_to_net[vout_comp.pins[0]]
        print(f"  VIN-VOUT connected: {vin_net == vout_net}")
