#!/usr/bin/env python3
"""Debug validation issue with Test 6."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard

print("Building Test 6 circuit step by step...")
b = Breadboard()

# Build a simple RC circuit with all components connected
# VIN -> Resistor -> Capacitor -> Inductor -> VOUT
print("\n1. Place resistor at (5,1)-(6,1)")
b = b.apply_action(('resistor', 5, 1))
print(f"   Resistor pins: {[c.pins for c in b.placed_components if c.type == 'resistor']}")

print("\n2. Wire VIN (1,0) to resistor (5,1)")
b = b.apply_action(('wire', 1, 0, 5, 1))

print("\n3. Place capacitor at (8,2)-(9,2)")
b = b.apply_action(('capacitor', 8, 2))

print("\n4. Wire resistor (6,1) to capacitor (8,2)")
b = b.apply_action(('wire', 6, 1, 8, 2))

print("\n5. Place inductor at (11,3)-(12,3)")
b = b.apply_action(('inductor', 11, 3))

print("\n6. Wire capacitor (9,2) to inductor (11,3)")
b = b.apply_action(('wire', 9, 2, 11, 3))

print("\n7. Wire inductor (12,3) to VOUT (28,0)")
b = b.apply_action(('wire', 12, 3, 28, 0))

print("\n" + "="*60)
print("Building position-to-net mapping...")
position_to_net = b._build_net_mapping()

print("\nAll component positions and their nets:")
for comp in b.placed_components:
    if comp.type in ['vin', 'vout']:
        print(f"  {comp.type:10s}: {comp.pins[0]} -> net {position_to_net.get(comp.pins[0], '?')}")
    elif comp.type != 'wire':
        print(f"  {comp.type:10s}: {comp.pins} -> nets {[position_to_net.get(p, '?') for p in comp.pins]}")

print("\nWire connections:")
for comp in b.placed_components:
    if comp.type == 'wire':
        p1, p2 = comp.pins
        net1 = position_to_net.get(p1, '?')
        net2 = position_to_net.get(p2, '?')
        print(f"  Wire: {p1} [{net1}] <-> {p2} [{net2}]")

vin_comp = next((c for c in b.placed_components if c.type == 'vin'), None)
vout_comp = next((c for c in b.placed_components if c.type == 'vout'), None)

vin_net = position_to_net[vin_comp.pins[0]]
vout_net = position_to_net[vout_comp.pins[0]]

print(f"\nVIN net: {vin_net}")
print(f"VOUT net: {vout_net}")
print(f"VIN == VOUT: {vin_net == vout_net}")

print("\nChecking if all components are on the main net:")
main_net = vin_net
for comp in b.placed_components:
    if comp.type in ['vin', 'vout', 'wire']:
        continue

    component_nets = [position_to_net[p] for p in comp.pins]
    on_main_net = any(net == main_net for net in component_nets)
    print(f"  {comp.type:10s}: nets {component_nets}, on_main_net: {on_main_net}")

print("\n" + "="*60)
print(f"is_complete_and_valid(): {b.is_complete_and_valid()}")
print(f"_all_components_connected(): {b._all_components_connected()}")
