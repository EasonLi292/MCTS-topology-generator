#!/usr/bin/env python3
"""
Test MCTS ability to complete a partially-built circuit.

We'll build: VIN -> Resistor -> [MISSING CAPACITOR] -> VOUT
Then let MCTS try to complete it.
"""
import sys
import os
# Add parent directory's core module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard
from MCTS import MCTS

def choose_row(board: Breadboard, offset: int, height: int = 1) -> int:
    """Select a valid starting row for components within the work area."""
    min_start = board.WORK_START_ROW
    max_start = board.WORK_END_ROW - (height - 1)
    if max_start < min_start:
        raise ValueError("Breadboard does not have enough rows for requested component")
    clamped_offset = max(0, min(offset, max_start - min_start))
    return min_start + clamped_offset

print("="*70)
print("BUILDING PARTIAL CIRCUIT")
print("="*70)

# Build partial circuit: VIN -> Resistor -> (need to add capacitor) -> VOUT
board = Breadboard()

resistor_row = choose_row(board, 3, height=2)
capacitor_row = choose_row(board, 6, height=2)

print(f"\nStep 1: Place resistor at rows {resistor_row}-{resistor_row + 1} (column 1)")
board = board.apply_action(('resistor', resistor_row, 1))
print(f"  Resistor placed: {[c for c in board.placed_components if c.type == 'resistor']}")

print(f"\nStep 2: Wire VIN ({board.VIN_ROW},0) to resistor top pin ({resistor_row},1)")
board = board.apply_action(('wire', board.VIN_ROW, 0, resistor_row, 1))
print("  Wire placed")

print(f"\nStep 3: Place capacitor at rows {capacitor_row}-{capacitor_row + 1} (column 1)")
board = board.apply_action(('capacitor', capacitor_row, 1))
print(f"  Capacitor placed: {[c for c in board.placed_components if c.type == 'capacitor']}")

print(f"\nStep 4: Wire resistor bottom ({resistor_row + 1},1) to capacitor top ({capacitor_row},1)")
board = board.apply_action(('wire', resistor_row + 1, 1, capacitor_row, 1))
print("  Wire placed")

print("\n--- CIRCUIT IS ALMOST COMPLETE ---")
print(f"Missing: Wire from capacitor bottom ({capacitor_row + 1},1) to VOUT ({board.VOUT_ROW},0)")

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
print(f"  Capacitor bottom ({capacitor_row + 1},1) net: {position_to_net.get((capacitor_row + 1,1), '?')}")
print(f"  Connected: {vin_net == vout_net}")

# Check legal actions - should include the wire we need
actions = board.legal_actions()
print(f"\nLegal actions available: {len(actions)}")

# Look for the winning move
winning_wire = ('wire', capacitor_row + 1, 1, board.VOUT_ROW, 0)
if winning_wire in actions:
    print(f"✓ Winning wire IS available: {winning_wire}")
else:
    print(f"✗ Winning wire NOT in actions")
    # Check if similar wires exist
    wires_from_cap = [a for a in actions if a[0] == 'wire' and a[1] == capacitor_row + 1 and a[2] == 1]
    wires_to_vout = [a for a in actions if a[0] == 'wire' and a[3] == board.VOUT_ROW and a[4] == 0]
    print(f"  Wires from ({capacitor_row + 1},1): {len(wires_from_cap)}")
    print(f"  Wires to ({board.VOUT_ROW},0): {len(wires_to_vout)}")

    # Why isn't this wire allowed? Let's check
    print(f"\n  Checking can_place_wire({capacitor_row + 1}, 1, {board.VOUT_ROW}, 0):")
    can_place = board.can_place_wire(capacitor_row + 1, 1, board.VOUT_ROW, 0)
    print(f"  Result: {can_place}")

    if not can_place:
        # Debug why
        print(f"  Debug info:")
        print(f"    Row {capacitor_row + 1} active: {board.is_row_active(capacitor_row + 1)}")
        print(f"    Row {board.VOUT_ROW} active: {board.is_row_active(board.VOUT_ROW)}")
        print(f"    At least one active: {board.is_row_active(capacitor_row + 1) or board.is_row_active(board.VOUT_ROW)}")

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
