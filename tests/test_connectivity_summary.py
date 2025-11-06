#!/usr/bin/env python3
"""
Test suite for _compute_connectivity_summary() validation oracle.

This function is the authoritative "is this circuit valid?" oracle that also feeds MCTS heuristics.
These tests verify all computed flags and validation logic to prevent training data misalignment.

Tests cover:
1. Degenerate component detection (all pins same net)
2. VIN==VOUT short circuit detection
3. Component nets tracking
4. BFS visited nets verification
5. rails_in_component flag
6. has_active_components flag
7. Validation formula edge cases
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard


def test_degenerate_component_detection():
    """Test that degenerate components (all pins on same net) are detected."""
    print("\n=== Test 1: Degenerate Component Detection ===")

    b = Breadboard()

    # Place a resistor in work area
    work_row = b.WORK_START_ROW
    b = b.apply_action(('resistor', work_row, 1))

    # Connect VIN to both pins of the resistor (making it degenerate)
    # First wire VIN to top pin
    b = b.apply_action(('wire', b.VIN_ROW, 0, work_row, 1))
    # Then wire VIN to bottom pin (both pins now on same net)
    b = b.apply_action(('wire', b.VIN_ROW, 0, work_row + 1, 1))

    # Get connectivity summary
    summary = b.get_connectivity_summary()

    # Should detect degenerate component
    assert summary["degenerate_component"], "Degenerate component should be detected"
    assert not summary["valid"], "Circuit with degenerate component should be invalid"

    print("✅ PASSED: Degenerate component correctly detected")


def test_vin_vout_same_net_detection():
    """Test that direct VIN→VOUT short without components is detected."""
    print("\n=== Test 2: VIN==VOUT Direct Short Detection ===")

    b = Breadboard()

    # Wire VIN directly to VOUT (short circuit, no components)
    b = b.apply_action(('wire', b.VIN_ROW, 0, b.VOUT_ROW, 0))

    # Get connectivity summary
    summary = b.get_connectivity_summary()

    # Should detect that VIN and VOUT are on same net
    assert not summary["vin_vout_distinct"], "VIN and VOUT on same net should be detected"
    assert not summary["valid"], "Circuit with VIN==VOUT should be invalid"

    print("✅ PASSED: VIN==VOUT short correctly detected")


def test_component_nets_tracking():
    """Test that all component nets are properly tracked."""
    print("\n=== Test 3: Component Nets Tracking ===")

    b = Breadboard()

    # Build a simple circuit with multiple nets
    # Place resistor R1 between two nets
    r1_row = b.WORK_START_ROW
    b = b.apply_action(('resistor', r1_row, 1))

    # Connect VIN to R1 top pin (creates net1)
    b = b.apply_action(('wire', b.VIN_ROW, 0, r1_row, 1))

    # Place resistor R2 below R1
    r2_row = r1_row + 3
    b = b.apply_action(('resistor', r2_row, 2))

    # Connect R1 bottom to R2 top (creates net2)
    b = b.apply_action(('wire', r1_row + 1, 1, r2_row, 2))

    # Connect R2 bottom to VOUT (net2 continues to VOUT)
    b = b.apply_action(('wire', r2_row + 1, 2, b.VOUT_ROW, 0))

    # Get connectivity summary
    summary = b.get_connectivity_summary()

    # Should track component nets
    component_nets = summary["component_nets"]

    # We expect at least 2 distinct nets involved in components
    assert len(component_nets) >= 2, f"Should have at least 2 component nets, got {len(component_nets)}"

    # VIN net should be in component nets
    vin_net = summary["vin_net"]
    assert vin_net in component_nets, "VIN net should be in component nets"

    print(f"  Tracked {len(component_nets)} component nets: {component_nets}")
    print("✅ PASSED: Component nets correctly tracked")


def test_visited_nets_bfs():
    """Test that BFS traversal visits all reachable nets from VIN."""
    print("\n=== Test 4: BFS Visited Nets Verification ===")

    b = Breadboard()

    # Build circuit: VIN → R1 → R2 → VOUT
    r1_row = b.WORK_START_ROW
    r2_row = r1_row + 3

    b = b.apply_action(('resistor', r1_row, 1))
    b = b.apply_action(('resistor', r2_row, 2))

    # Connect VIN → R1
    b = b.apply_action(('wire', b.VIN_ROW, 0, r1_row, 1))

    # Connect R1 → R2
    b = b.apply_action(('wire', r1_row + 1, 1, r2_row, 2))

    # Connect R2 → VOUT
    b = b.apply_action(('wire', r2_row + 1, 2, b.VOUT_ROW, 0))

    # Get connectivity summary
    summary = b.get_connectivity_summary()

    visited_nets = summary["visited_nets"]
    component_nets = summary["component_nets"]
    vin_net = summary["vin_net"]
    vout_net = summary["vout_net"]

    # VIN net should be visited
    assert vin_net in visited_nets, "VIN net should be visited"

    # VOUT should be reachable
    assert summary["reachable_vout"], "VOUT should be reachable from VIN"
    assert vout_net in visited_nets, "VOUT net should be in visited nets"

    # All component nets should be visited (reachable from VIN)
    assert component_nets.issubset(visited_nets), "All component nets should be reachable from VIN"
    assert summary["all_components_reachable"], "all_components_reachable should be True"

    print(f"  Visited {len(visited_nets)} nets via BFS")
    print("✅ PASSED: BFS visited nets correctly computed")


def test_rails_in_component_flag():
    """Test rails_in_component flag for circuits touching rails."""
    print("\n=== Test 5: rails_in_component Flag ===")

    b = Breadboard()

    # Build a proper voltage divider: VIN → R1 → (middle node) → R2 → VSS, with VOUT tapping middle
    # and R3 connecting middle to VDD
    # This ensures components touch both rails and VOUT is on a distinct net

    r1_row = b.WORK_START_ROW
    r2_row = r1_row + 3
    r3_row = r2_row + 3

    # R1: VIN to middle node
    b = b.apply_action(('resistor', r1_row, 1))
    b = b.apply_action(('wire', b.VIN_ROW, 0, r1_row, 1))

    # R2: middle node to VSS
    b = b.apply_action(('resistor', r2_row, 2))
    b = b.apply_action(('wire', r1_row + 1, 1, r2_row, 2))  # Connect R1 bottom to R2 top (middle node)
    b = b.apply_action(('wire', r2_row + 1, 2, b.VSS_ROW, 0))  # R2 bottom to VSS (R2 touches VSS)

    # R3: middle node to VDD
    b = b.apply_action(('resistor', r3_row, 3))
    b = b.apply_action(('wire', r1_row + 1, 1, r3_row, 3))  # middle node to R3 top
    b = b.apply_action(('wire', r3_row + 1, 3, b.VDD_ROW, 0))  # R3 bottom to VDD (R3 touches VDD)

    # VOUT taps the middle node (between R1 and R2/R3)
    b = b.apply_action(('wire', r1_row + 1, 1, b.VOUT_ROW, 0))

    # Get connectivity summary
    summary = b.get_connectivity_summary()

    # Circuit should touch both rails (R2 touches VSS, R3 touches VDD)
    assert summary["touches_vdd"], "Circuit should touch VDD (R3 connects to VDD)"
    assert summary["touches_vss"], "Circuit should touch VSS (R2 connects to VSS)"

    # All components should be reachable from VIN
    assert summary["all_components_reachable"], "All components should be reachable"

    # VOUT should be reachable
    assert summary["reachable_vout"], "VOUT should be reachable"

    # Circuit should be valid
    assert summary["valid"], "Circuit touching both rails with all components reachable should be valid"

    # Check rails_in_component flag (rails reachable from VIN via BFS)
    assert summary["rails_in_component"]["VDD"], "VDD should be in component (reachable from VIN)"
    assert summary["rails_in_component"]["0"], "VSS should be in component (reachable from VIN)"

    print("✅ PASSED: rails_in_component flag correctly computed")


def test_has_active_components():
    """Test has_active_components flag for circuits with/without components."""
    print("\n=== Test 6: has_active_components Flag ===")

    # Test 1: Empty circuit (only VIN/VOUT, no components)
    b1 = Breadboard()
    summary1 = b1.get_connectivity_summary()

    assert not summary1["has_active_components"], "Empty circuit should have no active components"
    assert not summary1["valid"], "Empty circuit should be invalid"

    # Test 2: Circuit with only wire (no real components)
    b2 = Breadboard()
    b2 = b2.apply_action(('wire', b2.VIN_ROW, 0, b2.VOUT_ROW, 0))
    summary2 = b2.get_connectivity_summary()

    # Wire is not an active component
    assert not summary2["has_active_components"], "Circuit with only wire should have no active components"
    assert not summary2["valid"], "Circuit with only wire should be invalid"

    # Test 3: Circuit with actual component
    b3 = Breadboard()
    r_row = b3.WORK_START_ROW
    b3 = b3.apply_action(('resistor', r_row, 1))
    b3 = b3.apply_action(('wire', b3.VIN_ROW, 0, r_row, 1))
    summary3 = b3.get_connectivity_summary()

    assert summary3["has_active_components"], "Circuit with resistor should have active components"

    print("✅ PASSED: has_active_components flag correctly computed")


def test_validation_formula_edge_cases():
    """Test validation formula edge cases where different flags cause failure."""
    print("\n=== Test 7: Validation Formula Edge Cases ===")

    # Edge Case 1: Circuit missing VDD connection
    print("  Testing: Circuit without VDD connection...")
    b1 = Breadboard()
    r1_row = b1.WORK_START_ROW
    r2_row = r1_row + 3

    # VIN → R1 → middle → R2 → VSS, VOUT taps middle (no VDD connection)
    b1 = b1.apply_action(('resistor', r1_row, 1))
    b1 = b1.apply_action(('wire', b1.VIN_ROW, 0, r1_row, 1))  # VIN to R1

    b1 = b1.apply_action(('resistor', r2_row, 2))
    b1 = b1.apply_action(('wire', r1_row + 1, 1, r2_row, 2))  # R1 to R2 (middle node)
    b1 = b1.apply_action(('wire', r2_row + 1, 2, b1.VSS_ROW, 0))  # R2 to VSS (touches VSS)

    # VOUT taps middle node
    b1 = b1.apply_action(('wire', r1_row + 1, 1, b1.VOUT_ROW, 0))

    summary1 = b1.get_connectivity_summary()
    assert summary1["touches_vss"], "Should touch VSS"
    assert not summary1["touches_vdd"], "Should NOT touch VDD"
    assert summary1["reachable_vout"], "VOUT should be reachable"
    assert not summary1["valid"], "Circuit without VDD should be invalid"
    print("    ✓ Missing VDD correctly invalidates circuit")

    # Edge Case 2: Circuit missing VSS connection
    print("  Testing: Circuit without VSS connection...")
    b2 = Breadboard()
    r1b_row = b2.WORK_START_ROW
    r2b_row = r1b_row + 3

    # VIN → R1 → middle → R2 → VDD, VOUT taps middle (no VSS connection)
    b2 = b2.apply_action(('resistor', r1b_row, 1))
    b2 = b2.apply_action(('wire', b2.VIN_ROW, 0, r1b_row, 1))  # VIN to R1

    b2 = b2.apply_action(('resistor', r2b_row, 2))
    b2 = b2.apply_action(('wire', r1b_row + 1, 1, r2b_row, 2))  # R1 to R2 (middle node)
    b2 = b2.apply_action(('wire', r2b_row + 1, 2, b2.VDD_ROW, 0))  # R2 to VDD (touches VDD)

    # VOUT taps middle node
    b2 = b2.apply_action(('wire', r1b_row + 1, 1, b2.VOUT_ROW, 0))

    summary2 = b2.get_connectivity_summary()
    assert summary2["touches_vdd"], "Should touch VDD"
    assert not summary2["touches_vss"], "Should NOT touch VSS"
    assert summary2["reachable_vout"], "VOUT should be reachable"
    assert not summary2["valid"], "Circuit without VSS should be invalid"
    print("    ✓ Missing VSS correctly invalidates circuit")

    # Edge Case 3: Circuit with VOUT unreachable
    print("  Testing: Circuit with unreachable VOUT...")
    b3 = Breadboard()
    r1c_row = b3.WORK_START_ROW
    r2c_row = r1c_row + 3
    r3c_row = r2c_row + 3

    # VIN → R1 → middle, R2: middle → VDD, R3: middle → VSS (VOUT not connected)
    b3 = b3.apply_action(('resistor', r1c_row, 1))
    b3 = b3.apply_action(('wire', b3.VIN_ROW, 0, r1c_row, 1))  # VIN to R1

    # R2 to VDD
    b3 = b3.apply_action(('resistor', r2c_row, 2))
    b3 = b3.apply_action(('wire', r1c_row + 1, 1, r2c_row, 2))  # middle to R2
    b3 = b3.apply_action(('wire', r2c_row + 1, 2, b3.VDD_ROW, 0))  # R2 to VDD

    # R3 to VSS
    b3 = b3.apply_action(('resistor', r3c_row, 3))
    b3 = b3.apply_action(('wire', r1c_row + 1, 1, r3c_row, 3))  # middle to R3
    b3 = b3.apply_action(('wire', r3c_row + 1, 3, b3.VSS_ROW, 0))  # R3 to VSS

    # VOUT is NOT connected - remains isolated

    summary3 = b3.get_connectivity_summary()
    assert summary3["touches_vdd"], "Should touch VDD"
    assert summary3["touches_vss"], "Should touch VSS"
    assert not summary3["reachable_vout"], "VOUT should NOT be reachable"
    assert not summary3["valid"], "Circuit without VOUT connection should be invalid"
    print("    ✓ Unreachable VOUT correctly invalidates circuit")

    # Edge Case 4: Valid complete circuit (using voltage divider pattern from test 5)
    print("  Testing: Valid complete circuit...")
    b4 = Breadboard()
    r1d_row = b4.WORK_START_ROW
    r2d_row = r1d_row + 3
    r3d_row = r2d_row + 3

    # VIN → R1 → middle, R2: middle → VSS, R3: middle → VDD, VOUT taps middle
    b4 = b4.apply_action(('resistor', r1d_row, 1))
    b4 = b4.apply_action(('wire', b4.VIN_ROW, 0, r1d_row, 1))

    # R2 to VSS
    b4 = b4.apply_action(('resistor', r2d_row, 2))
    b4 = b4.apply_action(('wire', r1d_row + 1, 1, r2d_row, 2))
    b4 = b4.apply_action(('wire', r2d_row + 1, 2, b4.VSS_ROW, 0))

    # R3 to VDD
    b4 = b4.apply_action(('resistor', r3d_row, 3))
    b4 = b4.apply_action(('wire', r1d_row + 1, 1, r3d_row, 3))
    b4 = b4.apply_action(('wire', r3d_row + 1, 3, b4.VDD_ROW, 0))

    # VOUT taps middle
    b4 = b4.apply_action(('wire', r1d_row + 1, 1, b4.VOUT_ROW, 0))

    summary4 = b4.get_connectivity_summary()
    assert summary4["touches_vdd"], "Should touch VDD"
    assert summary4["touches_vss"], "Should touch VSS"
    assert summary4["reachable_vout"], "VOUT should be reachable"
    assert summary4["all_components_reachable"], "All components should be reachable"
    assert summary4["valid"], "Complete valid circuit should be valid"
    print("    ✓ Valid complete circuit correctly validated")

    print("✅ PASSED: Validation formula edge cases correctly handled")


if __name__ == '__main__':
    test_degenerate_component_detection()
    test_vin_vout_same_net_detection()
    test_component_nets_tracking()
    test_visited_nets_bfs()
    test_rails_in_component_flag()
    test_has_active_components()
    test_validation_formula_edge_cases()

    print("\n" + "=" * 60)
    print("✅ ALL CONNECTIVITY SUMMARY TESTS PASSED")
    print("=" * 60)
