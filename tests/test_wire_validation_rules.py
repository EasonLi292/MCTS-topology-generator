#!/usr/bin/env python3
"""
Test suite for wire validation rules in can_place_wire().

These tests explicitly verify all wire placement constraints:
1. Same-row wire rejection
2. VIN/VOUT column leak prevention (critical electrical safety)
3. Forbidden VIN→VSS direct wire
4. Forbidden VOUT→VDD direct wire
5. Duplicate wire detection
6. Inactive net wire blocking
7. Wire requires one active endpoint
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard


def test_same_row_wire_rejected():
    """Test that wires on the same row are rejected."""
    print("\n=== Test 1: Same-Row Wire Rejection ===")

    b = Breadboard()

    # Try to place a wire on the same row (should fail)
    # Choose a work area row
    work_row = b.WORK_START_ROW

    # Same row connections should always be rejected
    can_place = b.can_place_wire(work_row, 1, work_row, 3)

    assert not can_place, "Same-row wire should be rejected"
    print("✅ PASSED: Same-row wire correctly rejected")


def test_vin_vout_column_leak_prevention():
    """Test that wires cannot connect to VIN/VOUT rows at columns != 0."""
    print("\n=== Test 2: VIN/VOUT Column Leak Prevention ===")

    b = Breadboard()
    work_row = b.WORK_START_ROW

    # VIN is at (VIN_ROW, 0). Trying to wire to (VIN_ROW, 1) should fail
    can_place_vin_col1 = b.can_place_wire(work_row, 1, b.VIN_ROW, 1)
    assert not can_place_vin_col1, "Wire to VIN_ROW at column != 0 should be rejected"

    # Try another column on VIN row
    can_place_vin_col3 = b.can_place_wire(work_row, 2, b.VIN_ROW, 3)
    assert not can_place_vin_col3, "Wire to VIN_ROW at column 3 should be rejected"

    # VOUT is at (VOUT_ROW, 0). Trying to wire to (VOUT_ROW, 2) should fail
    can_place_vout_col2 = b.can_place_wire(work_row, 1, b.VOUT_ROW, 2)
    assert not can_place_vout_col2, "Wire to VOUT_ROW at column != 0 should be rejected"

    # Try another column on VOUT row
    can_place_vout_col5 = b.can_place_wire(work_row, 3, b.VOUT_ROW, 5)
    assert not can_place_vout_col5, "Wire to VOUT_ROW at column 5 should be rejected"

    # But wiring to (VIN_ROW, 0) should work (that's where VIN is)
    can_place_vin_col0 = b.can_place_wire(work_row, 1, b.VIN_ROW, 0)
    assert can_place_vin_col0, "Wire to VIN_ROW at column 0 should be allowed"

    # And wiring to (VOUT_ROW, 0) should work (that's where VOUT is)
    can_place_vout_col0 = b.can_place_wire(work_row, 1, b.VOUT_ROW, 0)
    assert can_place_vout_col0, "Wire to VOUT_ROW at column 0 should be allowed"

    print("✅ PASSED: VIN/VOUT column leak prevention working correctly")


def test_forbidden_vin_vss_direct_wire():
    """Test that direct VIN→VSS wire is forbidden."""
    print("\n=== Test 3: Forbidden VIN→VSS Direct Wire ===")

    b = Breadboard()

    # Try to wire VIN (row 1, col 0) directly to VSS (row 0, col 0)
    can_place = b.can_place_wire(b.VIN_ROW, 0, b.VSS_ROW, 0)

    assert not can_place, "Direct VIN→VSS wire should be forbidden"

    # Try reverse order (should also fail)
    can_place_reverse = b.can_place_wire(b.VSS_ROW, 0, b.VIN_ROW, 0)

    assert not can_place_reverse, "Direct VSS→VIN wire should be forbidden"

    print("✅ PASSED: VIN→VSS direct wire correctly forbidden")


def test_forbidden_vout_vdd_direct_wire():
    """Test that direct VOUT→VDD wire is forbidden."""
    print("\n=== Test 4: Forbidden VOUT→VDD Direct Wire ===")

    b = Breadboard()

    # Try to wire VOUT (row ROWS-2, col 0) directly to VDD (row ROWS-1, col 0)
    can_place = b.can_place_wire(b.VOUT_ROW, 0, b.VDD_ROW, 0)

    assert not can_place, "Direct VOUT→VDD wire should be forbidden"

    # Try reverse order (should also fail)
    can_place_reverse = b.can_place_wire(b.VDD_ROW, 0, b.VOUT_ROW, 0)

    assert not can_place_reverse, "Direct VDD→VOUT wire should be forbidden"

    print("✅ PASSED: VOUT→VDD direct wire correctly forbidden")


def test_duplicate_wire_detection():
    """Test that duplicate wires are detected and rejected."""
    print("\n=== Test 5: Duplicate Wire Detection ===")

    b = Breadboard()
    work_row1 = b.WORK_START_ROW
    work_row2 = b.WORK_START_ROW + 1

    # Place first wire
    b = b.apply_action(('wire', work_row1, 1, work_row2, 2))

    # Try to place the exact same wire again
    can_place_exact = b.can_place_wire(work_row1, 1, work_row2, 2)
    assert not can_place_exact, "Exact duplicate wire should be rejected"

    # Try to place the same wire in reverse order (should also be detected as duplicate)
    can_place_reverse = b.can_place_wire(work_row2, 2, work_row1, 1)
    assert not can_place_reverse, "Reverse duplicate wire should be rejected"

    # But a different wire should be allowed
    work_row3 = b.WORK_START_ROW + 2
    can_place_different = b.can_place_wire(work_row1, 1, work_row3, 3)
    assert can_place_different, "Different wire should be allowed"

    print("✅ PASSED: Duplicate wire detection working correctly")


def test_inactive_net_wire_blocked():
    """Test that wires between two inactive nets are blocked."""
    print("\n=== Test 6: Inactive Net Wire Blocking ===")

    b = Breadboard()

    # At the start, only VSS and VDD rows are active nets
    # VIN and VOUT rows are active (VIN and VOUT are placed by default)
    # Work area rows are initially inactive

    work_row1 = b.WORK_START_ROW
    work_row2 = b.WORK_START_ROW + 1

    # Check that both rows are initially inactive
    assert not b.is_row_active(work_row1), "Work row 1 should be inactive initially"
    assert not b.is_row_active(work_row2), "Work row 2 should be inactive initially"

    # Try to place wire between two inactive rows (should fail)
    can_place = b.can_place_wire(work_row1, 1, work_row2, 1)

    assert not can_place, "Wire between two inactive nets should be blocked"

    print("✅ PASSED: Inactive net wire blocking working correctly")


def test_wire_requires_one_active_endpoint():
    """Test that at least one wire endpoint must be on an active net."""
    print("\n=== Test 7: Wire Requires One Active Endpoint ===")

    b = Breadboard()
    work_row = b.WORK_START_ROW

    # VIN_ROW is active (VIN is placed there)
    assert b.is_row_active(b.VIN_ROW), "VIN row should be active"

    # Work row is initially inactive
    assert not b.is_row_active(work_row), "Work row should be inactive initially"

    # Wire from active VIN to inactive work row should be ALLOWED
    # (this is how we expand the circuit - connecting to inactive areas)
    can_place_to_inactive = b.can_place_wire(b.VIN_ROW, 0, work_row, 1)
    assert can_place_to_inactive, "Wire from active net to inactive net should be allowed"

    # After placing the wire, the work row should become active
    b = b.apply_action(('wire', b.VIN_ROW, 0, work_row, 1))
    assert b.is_row_active(work_row), "Work row should be active after wiring"

    # Now wire from active work_row to another inactive row should work
    work_row2 = b.WORK_START_ROW + 1
    assert not b.is_row_active(work_row2), "Work row 2 should be inactive"
    can_place_expand = b.can_place_wire(work_row, 2, work_row2, 2)
    assert can_place_expand, "Wire from active to inactive net should expand the circuit"

    # But two completely inactive rows should still be blocked
    work_row3 = b.WORK_START_ROW + 2
    work_row4 = b.WORK_START_ROW + 3
    assert not b.is_row_active(work_row3), "Work row 3 should be inactive"
    assert not b.is_row_active(work_row4), "Work row 4 should be inactive"
    can_place_both_inactive = b.can_place_wire(work_row3, 1, work_row4, 1)
    assert not can_place_both_inactive, "Wire between two inactive nets should be blocked"

    print("✅ PASSED: Wire active endpoint requirement working correctly")


if __name__ == '__main__':
    test_same_row_wire_rejected()
    test_vin_vout_column_leak_prevention()
    test_forbidden_vin_vss_direct_wire()
    test_forbidden_vout_vdd_direct_wire()
    test_duplicate_wire_detection()
    test_inactive_net_wire_blocked()
    test_wire_requires_one_active_endpoint()

    print("\n" + "=" * 60)
    print("✅ ALL WIRE VALIDATION TESTS PASSED")
    print("=" * 60)
