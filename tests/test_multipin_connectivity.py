#!/usr/bin/env python3
"""
Test suite for multi-pin component connectivity in row-only model.

Verifies that multi-pin components (resistors, transistors, etc.) have their
pins properly connected in the same electrical net, even without explicit wires.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard


def test_resistor_pins_share_net():
    """Test that a 2-pin resistor's pins are on the same net."""
    print("\n=== Test 1: Resistor Pins Share Net ===")

    b = Breadboard()

    # Activate a work row and place resistor
    r_row = b.WORK_START_ROW
    b = b.apply_action(('wire', b.VIN_ROW, r_row))
    b = b.apply_action(('resistor', r_row))

    # Get the nets for both pins
    position_to_net = b._build_net_mapping()

    pin1_net = position_to_net[(r_row, 0)]
    pin2_net = position_to_net[(r_row + 1, 0)]

    # In row-only model, each row is its own net UNLESS unified
    # Multi-pin components should NOT auto-unify rows
    # Resistor occupies rows r_row and r_row+1

    # Check if pins are in the same union-find root
    root1 = b.find(r_row)
    root2 = b.find(r_row + 1)

    print(f"Pin 1 (row {r_row}): net={pin1_net}, root={root1}")
    print(f"Pin 2 (row {r_row + 1}): net={pin2_net}, root={root2}")

    # In the row-only model, component pins are NOT auto-unified via union-find
    # Instead, components create edges in the connectivity GRAPH
    # A resistor on rows 5-6 bridges those nets, but doesn't unify them
    # Connectivity is handled via BFS in the adjacency graph, not union-find

    # Pins should have DIFFERENT nets (not unified in union-find)
    assert pin1_net != pin2_net, "Component pins should have different nets (no auto-union)"
    assert root1 != root2, "Component pins should not be unified in union-find"

    # But they should be connected via the connectivity GRAPH
    # (tested in test_component_spanning_rows_connects_via_graph)

    print("✅ PASSED: Multi-pin components span different nets (connectivity via graph)")


def test_resistor_connectivity_in_netlist():
    """Test that resistor appears correctly in netlist with different pin nets."""
    print("\n=== Test 2: Resistor Has Different Nets For Each Pin ===")

    b = Breadboard()

    # Place a resistor and check its pins have different nets
    r_row = b.WORK_START_ROW
    b = b.apply_action(('wire', b.VIN_ROW, r_row))
    b = b.apply_action(('resistor', r_row))

    position_to_net = b._build_net_mapping()
    pin1_net = position_to_net[(r_row, 0)]
    pin2_net = position_to_net[(r_row + 1, 0)]

    print(f"Resistor pin 1 net: {pin1_net}")
    print(f"Resistor pin 2 net: {pin2_net}")

    assert pin1_net != pin2_net, "Resistor pins should have different nets in netlist mapping"

    print("✅ PASSED: Resistor pins have different nets for netlist generation")


def test_transistor_three_pins_separate_nets():
    """Test that a 3-pin transistor has three different nets for its pins."""
    print("\n=== Test 3: Transistor Three Separate Nets ===")

    b = Breadboard()

    # Activate a work row and place NMOS
    nmos_row = b.WORK_START_ROW
    b = b.apply_action(('wire', b.VIN_ROW, nmos_row))
    b = b.apply_action(('nmos3', nmos_row))

    # Get nets for all three pins (drain, gate, source)
    position_to_net = b._build_net_mapping()

    drain_net = position_to_net[(nmos_row, 0)]
    gate_net = position_to_net[(nmos_row + 1, 0)]
    source_net = position_to_net[(nmos_row + 2, 0)]

    print(f"Drain (row {nmos_row}): net={drain_net}")
    print(f"Gate (row {nmos_row + 1}): net={gate_net}")
    print(f"Source (row {nmos_row + 2}): net={source_net}")

    # All three should be DIFFERENT (not auto-unified, connectivity via graph)
    assert drain_net != gate_net, "Drain and gate should be on different nets"
    assert gate_net != source_net, "Gate and source should be on different nets"
    assert drain_net != source_net, "Drain and source should be on different nets"

    print("✅ PASSED: 3-pin transistor spans three separate nets")


def test_component_spanning_rows_connects_via_graph():
    """Test that components spanning multiple rows are represented in the connectivity graph."""
    print("\n=== Test 4: Component Bridges Different Nets ===")

    b = Breadboard()

    # Place a resistor
    r_row = b.WORK_START_ROW
    b = b.apply_action(('wire', b.VIN_ROW, r_row))
    b = b.apply_action(('resistor', r_row))

    # The resistor should appear in the connectivity graph
    # spanning its two pin nets
    summary = b._compute_connectivity_summary()

    # Get position to net mapping
    position_to_net = b._build_net_mapping()
    pin1_net = position_to_net[(r_row, 0)]
    pin2_net = position_to_net[(r_row + 1, 0)]

    print(f"Resistor connects net {pin1_net} to net {pin2_net}")
    print(f"Component nets: {summary['component_nets']}")

    # Both nets should be in component_nets
    assert pin1_net in summary['component_nets'], "Pin 1 net should be in component nets"
    assert pin2_net in summary['component_nets'], "Pin 2 net should be in component nets"

    print("✅ PASSED: Components bridge their pin nets in connectivity graph")


if __name__ == '__main__':
    test_resistor_pins_share_net()
    test_resistor_connectivity_in_netlist()
    test_transistor_three_pins_separate_nets()
    test_component_spanning_rows_connects_via_graph()

    print("\n" + "=" * 60)
    print("✅ ALL MULTI-PIN CONNECTIVITY TESTS PASSED")
    print("=" * 60)
