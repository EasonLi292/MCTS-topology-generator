#!/usr/bin/env python3
"""
Test suite for new validation rules:
1. No floating components
2. No VDD/VSS connections to gate/base pins
3. All nets must be connected before simulation
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard

def choose_row(board: Breadboard, offset: int, height: int = 1) -> int:
    """
    Choose a starting row within the configurable work area.

    Args:
        board: Breadboard instance
        offset: Desired offset from WORK_START_ROW
        height: Number of vertical slots required by the component

    Returns:
        Valid starting row clamped within bounds
    """
    min_start = board.WORK_START_ROW
    max_start = board.WORK_END_ROW - (height - 1)
    if max_start < min_start:
        raise ValueError("Breadboard does not have enough work rows for component placement")
    clamped_offset = max(0, min(offset, max_start - min_start))
    return min_start + clamped_offset

def attach_vin_via_gate(board: Breadboard, target_row: int, target_col: int, driver_col: int = 5) -> Breadboard:
    """Connect VIN to a target node through the gate of an NMOS transistor."""
    driver_row = min(target_row, board.WORK_END_ROW - 2)
    board = board.apply_action(('nmos3', driver_row, driver_col))
    board = board.apply_action(('wire', board.VIN_ROW, 0, driver_row + 1, driver_col))  # VIN to gate
    board = board.apply_action(('wire', driver_row, driver_col, target_row, target_col))  # Drain to node
    board = board.apply_action(('wire', driver_row + 2, driver_col, target_row, target_col))  # Source to node
    return board

def test_floating_component_detection():
    """Test that floating components are properly detected and rejected."""
    print("\n=== Test 1: Floating Component Detection ===")

    # Create a circuit with a floating resistor
    b = Breadboard()

    resistor_row = choose_row(b, 3, height=2)
    floating_cap_row = choose_row(b, 7, height=2)

    # Place resistor connected to VIN
    b = b.apply_action(('resistor', resistor_row, 1))
    b = attach_vin_via_gate(b, resistor_row, 1, driver_col=5)

    # Place a floating capacitor (not connected to anything)
    b = b.apply_action(('capacitor', floating_cap_row, 1))

    # Connect resistor to VOUT (bypassing the floating capacitor)
    b = b.apply_action(('wire', resistor_row + 1, 1, b.VOUT_ROW, 0))

    # Circuit should NOT be valid because capacitor is floating
    if b.is_complete_and_valid():
        print("❌ FAILED: Floating component was not detected!")
        return False
    else:
        print("✅ PASSED: Floating component correctly detected and rejected")
        return True


def test_gate_vdd_connection_prevention():
    """Test that gates cannot be directly connected to VDD."""
    print("\n=== Test 2: Gate-VDD Connection Prevention ===")

    b = Breadboard()

    # Place NMOS transistor (drain=pin0, gate=pin1, source=pin2)
    nmos_row = choose_row(b, 3, height=3)
    b = b.apply_action(('nmos3', nmos_row, 1))

    # Try to wire gate (row 6) to VDD (row 29)
    gate_row = nmos_row + 1
    can_wire_gate_to_vdd = b.can_place_wire(gate_row, 1, b.VDD_ROW, 0)

    if can_wire_gate_to_vdd:
        print("❌ FAILED: Gate-to-VDD wire was allowed!")
        return False
    else:
        print("✅ PASSED: Gate-to-VDD wire correctly prevented")
        return True


def test_gate_vss_connection_prevention():
    """Test that gates cannot be directly connected to VSS (ground)."""
    print("\n=== Test 3: Gate-VSS Connection Prevention ===")

    b = Breadboard()

    # Place PMOS transistor
    pmos_row = choose_row(b, 3, height=3)
    b = b.apply_action(('pmos3', pmos_row, 1))

    # Try to wire gate (row 6) to VSS (row 0)
    gate_row = pmos_row + 1
    can_wire_gate_to_vss = b.can_place_wire(gate_row, 1, b.VSS_ROW, 0)

    if can_wire_gate_to_vss:
        print("❌ FAILED: Gate-to-VSS wire was allowed!")
        return False
    else:
        print("✅ PASSED: Gate-to-VSS wire correctly prevented")
        return True


def test_base_vdd_connection_prevention():
    """Test that BJT bases cannot be directly connected to VDD."""
    print("\n=== Test 4: Base-VDD Connection Prevention ===")

    b = Breadboard()

    # Place NPN transistor (collector=pin0, base=pin1, emitter=pin2)
    npn_row = choose_row(b, 3, height=3)
    b = b.apply_action(('npn', npn_row, 1))

    # Try to wire base (row 6) to VDD (row 29)
    base_row = npn_row + 1
    can_wire_base_to_vdd = b.can_place_wire(base_row, 1, b.VDD_ROW, 0)

    if can_wire_base_to_vdd:
        print("❌ FAILED: Base-to-VDD wire was allowed!")
        return False
    else:
        print("✅ PASSED: Base-to-VDD wire correctly prevented")
        return True


def test_base_vss_connection_prevention():
    """Test that BJT bases cannot be directly connected to VSS."""
    print("\n=== Test 5: Base-VSS Connection Prevention ===")

    b = Breadboard()

    # Place PNP transistor
    pnp_row = choose_row(b, 3, height=3)
    b = b.apply_action(('pnp', pnp_row, 1))

    # Try to wire base (row 6) to VSS (row 0)
    base_row = pnp_row + 1
    can_wire_base_to_vss = b.can_place_wire(base_row, 1, b.VSS_ROW, 0)

    if can_wire_base_to_vss:
        print("❌ FAILED: Base-to-VSS wire was allowed!")
        return False
    else:
        print("✅ PASSED: Base-to-VSS wire correctly prevented")
        return True


def test_valid_circuit_with_all_connected():
    """Test that a valid circuit with all components connected is accepted."""
    print("\n=== Test 6: Valid Circuit with All Components Connected ===")

    b = Breadboard()

    # Build a simple RC circuit with all components connected
    # VIN -> Resistor -> Capacitor -> Inductor -> VOUT
    resistor_row = choose_row(b, 3, height=2)
    capacitor_row = choose_row(b, 6, height=2)
    inductor_row = choose_row(b, 9, height=2)
    b = b.apply_action(('resistor', resistor_row, 1))
    b = attach_vin_via_gate(b, resistor_row, 1, driver_col=5)

    b = b.apply_action(('capacitor', capacitor_row, 1))
    b = b.apply_action(('wire', resistor_row + 1, 1, capacitor_row, 1))  # Resistor pin 2 to capacitor pin 1

    b = b.apply_action(('inductor', inductor_row, 1))
    b = b.apply_action(('wire', capacitor_row + 1, 1, inductor_row, 1))  # Capacitor pin 2 to inductor pin 1

    b = b.apply_action(('wire', inductor_row + 1, 1, b.VOUT_ROW, 0))  # Inductor pin 2 to VOUT

    # Provide a load to VDD using an additional resistor in column 2
    supply_res_row = resistor_row
    b = b.apply_action(('resistor', supply_res_row, 2))
    b = b.apply_action(('wire', supply_res_row, 2, resistor_row + 1, 1))  # Tie to signal path
    b = b.apply_action(('wire', supply_res_row + 1, 2, b.VDD_ROW, 0))      # Connect to VDD rail

    # Provide a path to ground using a second resistor in column 3
    ground_res_row = capacitor_row
    b = b.apply_action(('resistor', ground_res_row, 3))
    b = b.apply_action(('wire', ground_res_row, 3, capacitor_row + 1, 1))   # Connect to intermediate node
    b = b.apply_action(('wire', ground_res_row + 1, 3, b.VSS_ROW, 0))       # Connect to ground

    # All components are connected, circuit should be valid
    if b.is_complete_and_valid():
        print("✅ PASSED: Valid circuit with all components connected is accepted")
        return True
    else:
        print("❌ FAILED: Valid circuit was rejected!")
        print(f"  VIN-VOUT connected: {b.find(b.VIN_ROW) == b.find(b.VOUT_ROW)}")
        print(f"  All components connected: {b._all_components_connected()}")
        print(f"  Gate/base validation: {b._validate_gate_base_connections()}")
        return False


def test_transistor_circuit_with_valid_connections():
    """Test that transistors with valid (non-power-rail) gate/base connections work."""
    print("\n=== Test 7: Transistor with Valid Gate Connection ===")

    b = Breadboard()

    # Build circuit: VIN -> Resistor -> NMOS gate (valid)
    #                                 NMOS drain -> VOUT
    #                                 NMOS source -> ground

    # Place NMOS (drain, gate, source)
    nmos_row = choose_row(b, 3, height=3)
    b = b.apply_action(('nmos3', nmos_row, 1))
    gate_row = nmos_row + 1
    source_row = nmos_row + 2
    b = b.apply_action(('wire', b.VIN_ROW, 0, gate_row, 1))  # VIN to gate (valid!)
    b = b.apply_action(('wire', nmos_row, 1, b.VOUT_ROW, 0))  # Drain to VOUT
    b = b.apply_action(('wire', source_row, 1, b.VSS_ROW, 0))  # Source to ground

    # Add supply resistor to VDD
    supply_res_row = gate_row  # reuse nearby empty column
    b = b.apply_action(('resistor', supply_res_row, 2))
    b = b.apply_action(('wire', supply_res_row, 2, nmos_row, 1))  # Connect to drain
    b = b.apply_action(('wire', supply_res_row + 1, 2, b.VDD_ROW, 0))  # Connect to VDD rail

    # This should be valid - gate connected to VIN (not VDD/VSS)
    gate_validation = b._validate_gate_base_connections()

    if not gate_validation:
        print("❌ FAILED: Valid gate connection was incorrectly rejected!")
        return False

    if b.is_complete_and_valid():
        print("✅ PASSED: Transistor with valid gate connection is accepted")
        return True
    else:
        print("❌ FAILED: Valid transistor circuit was rejected!")
        print(f"  Gate/base validation: {gate_validation}")
        print(f"  All components connected: {b._all_components_connected()}")
        return False


def test_partial_circuit_not_valid():
    """Test that incomplete circuits are properly rejected."""
    print("\n=== Test 8: Incomplete Circuit Rejection ===")

    b = Breadboard()

    # Place components but don't connect VIN to VOUT
    resistor_row = choose_row(b, 3, height=2)
    b = b.apply_action(('resistor', resistor_row, 1))
    b = attach_vin_via_gate(b, resistor_row, 1, driver_col=6)
    # (Don't connect to VOUT)

    if b.is_complete_and_valid():
        print("❌ FAILED: Incomplete circuit was accepted!")
        return False
    else:
        print("✅ PASSED: Incomplete circuit correctly rejected")
        return True


def run_all_tests():
    """Run all validation tests."""
    print("="*70)
    print("VALIDATION RULES TEST SUITE")
    print("="*70)

    tests = [
        test_floating_component_detection,
        test_gate_vdd_connection_prevention,
        test_gate_vss_connection_prevention,
        test_base_vdd_connection_prevention,
        test_base_vss_connection_prevention,
        test_valid_circuit_with_all_connected,
        test_transistor_circuit_with_valid_connections,
        test_partial_circuit_not_valid,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
