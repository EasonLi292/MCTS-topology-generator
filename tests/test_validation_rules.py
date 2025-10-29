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

def test_floating_component_detection():
    """Test that floating components are properly detected and rejected."""
    print("\n=== Test 1: Floating Component Detection ===")

    # Create a circuit with a floating resistor
    b = Breadboard()

    # Place resistor connected to VIN
    b = b.apply_action(('resistor', 5, 1))
    b = b.apply_action(('wire', 1, 0, 5, 1))  # VIN to resistor

    # Place a floating capacitor (not connected to anything)
    b = b.apply_action(('capacitor', 10, 2))

    # Connect resistor to VOUT (bypassing the floating capacitor)
    b = b.apply_action(('wire', 6, 1, 28, 0))

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
    b = b.apply_action(('nmos3', 5, 1))

    # Try to wire gate (row 6) to VDD (row 29)
    can_wire_gate_to_vdd = b.can_place_wire(6, 1, 29, 0)

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
    b = b.apply_action(('pmos3', 5, 1))

    # Try to wire gate (row 6) to VSS (row 0)
    can_wire_gate_to_vss = b.can_place_wire(6, 1, 0, 0)

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
    b = b.apply_action(('npn', 5, 1))

    # Try to wire base (row 6) to VDD (row 29)
    can_wire_base_to_vdd = b.can_place_wire(6, 1, 29, 0)

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
    b = b.apply_action(('pnp', 5, 1))

    # Try to wire base (row 6) to VSS (row 0)
    can_wire_base_to_vss = b.can_place_wire(6, 1, 0, 0)

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
    # VIN -> Resistor -> Capacitor -> VOUT
    b = b.apply_action(('resistor', 5, 1))
    b = b.apply_action(('wire', 1, 0, 5, 1))  # VIN to resistor pin 1

    b = b.apply_action(('capacitor', 8, 2))
    b = b.apply_action(('wire', 6, 1, 8, 2))  # Resistor pin 2 to capacitor pin 1

    b = b.apply_action(('inductor', 11, 3))
    b = b.apply_action(('wire', 9, 2, 11, 3))  # Capacitor pin 2 to inductor pin 1

    b = b.apply_action(('wire', 12, 3, 28, 0))  # Inductor pin 2 to VOUT

    # All components are connected, circuit should be valid
    if b.is_complete_and_valid():
        print("✅ PASSED: Valid circuit with all components connected is accepted")
        return True
    else:
        print("❌ FAILED: Valid circuit was rejected!")
        print(f"  VIN-VOUT connected: {b.find(1) == b.find(28)}")
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

    # Place NMOS (drain=5, gate=6, source=7)
    b = b.apply_action(('nmos3', 5, 1))
    b = b.apply_action(('wire', 1, 0, 6, 1))  # VIN to gate (valid!)
    b = b.apply_action(('wire', 5, 1, 28, 0))  # Drain to VOUT
    b = b.apply_action(('wire', 7, 1, 0, 0))  # Source to ground

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
    b = b.apply_action(('resistor', 5, 1))
    b = b.apply_action(('wire', 1, 0, 5, 1))  # VIN to resistor
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
