#!/usr/bin/env python3
"""
Test suite for ComponentInfo metadata enforcement.

Tests verify that metadata fields are properly enforced in component placement:
1. can_place_multiple enforcement for VIN/VOUT
2. can_place_multiple allows multiple instances for regular components
3. pin_count is properly used in placement logic
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard, COMPONENT_CATALOG


def test_can_place_multiple_prevents_duplicate_vin_vout():
    """Test that can_place_multiple=False prevents duplicate VIN/VOUT placement."""
    print("\n=== Test 1: can_place_multiple Prevents Duplicate VIN/VOUT ===")

    # Verify metadata is configured correctly
    assert not COMPONENT_CATALOG['vin'].can_place_multiple, "VIN should have can_place_multiple=False"
    assert not COMPONENT_CATALOG['vout'].can_place_multiple, "VOUT should have can_place_multiple=False"

    b = Breadboard()

    # VIN and VOUT are automatically placed during board initialization
    assert b.vin_placed, "VIN should be placed at initialization"
    assert b.vout_placed, "VOUT should be placed at initialization"

    # Try to place another VIN (should fail due to can_place_multiple=False)
    work_row = b.WORK_START_ROW
    can_place_second_vin = b.can_place_component('vin', work_row, 2)

    assert not can_place_second_vin, "Should not be able to place second VIN (can_place_multiple=False)"

    # Try to place another VOUT (should also fail)
    can_place_second_vout = b.can_place_component('vout', work_row + 2, 3)

    assert not can_place_second_vout, "Should not be able to place second VOUT (can_place_multiple=False)"

    print("✅ PASSED: can_place_multiple correctly prevents duplicate VIN/VOUT")


def test_can_place_multiple_allows_multiple_regular_components():
    """Test that can_place_multiple=True allows multiple instances of regular components."""
    print("\n=== Test 2: can_place_multiple Allows Multiple Regular Components ===")

    # Verify metadata is configured correctly
    assert COMPONENT_CATALOG['resistor'].can_place_multiple, "Resistor should have can_place_multiple=True"
    assert COMPONENT_CATALOG['capacitor'].can_place_multiple, "Capacitor should have can_place_multiple=True"

    b = Breadboard()

    # First activate a row by wiring from VIN
    r1_row = b.WORK_START_ROW
    b = b.apply_action(('wire', b.VIN_ROW, 0, r1_row, 1))  # Activate r1_row first

    # Now place first resistor on the activated row
    can_place_r1 = b.can_place_component('resistor', r1_row, 1)
    assert can_place_r1, "Should be able to place first resistor on active row"

    b = b.apply_action(('resistor', r1_row, 1))

    # Try to place second resistor (should succeed)
    r2_row = r1_row + 3
    b = b.apply_action(('wire', r1_row, 1, r2_row, 2))  # Activate r2_row

    can_place_r2 = b.can_place_component('resistor', r2_row, 2)
    assert can_place_r2, "Should be able to place second resistor (can_place_multiple=True)"

    b = b.apply_action(('resistor', r2_row, 2))

    # Verify both resistors are placed
    resistor_count = sum(1 for c in b.placed_components if c.type == 'resistor')
    assert resistor_count == 2, f"Should have 2 resistors placed, got {resistor_count}"

    # Try to place third resistor (should also succeed)
    r3_row = r2_row + 3
    b = b.apply_action(('wire', r2_row, 2, r3_row, 3))  # Activate r3_row

    can_place_r3 = b.can_place_component('resistor', r3_row, 3)
    assert can_place_r3, "Should be able to place third resistor (can_place_multiple=True)"

    print("✅ PASSED: can_place_multiple allows multiple regular components")


def test_pin_count_used_in_placement():
    """Test that pin_count is properly used to determine component size."""
    print("\n=== Test 3: pin_count Used in Placement Logic ===")

    # Verify pin_count metadata
    assert COMPONENT_CATALOG['resistor'].pin_count == 2, "Resistor should have pin_count=2"
    assert COMPONENT_CATALOG['nmos3'].pin_count == 3, "NMOS should have pin_count=3"

    b = Breadboard()
    work_row = b.WORK_START_ROW

    # Place 2-pin resistor (occupies 2 rows)
    b = b.apply_action(('resistor', work_row, 1))
    b = b.apply_action(('wire', b.VIN_ROW, 0, work_row, 1))

    # Check that the resistor occupies rows [work_row, work_row+1]
    cell_top = b.grid[work_row][1]
    cell_bottom = b.grid[work_row + 1][1]

    assert cell_top is not None, "Resistor top pin should occupy grid cell"
    assert cell_bottom is not None, "Resistor bottom pin should occupy grid cell"

    resistor_comp = cell_top[0]
    assert resistor_comp.type == 'resistor', "Component should be a resistor"
    assert len(resistor_comp.pins) == 2, "Resistor should have 2 pins"

    # Try to place 3-pin NMOS (should occupy 3 rows)
    nmos_row = work_row + 3
    b = b.apply_action(('wire', work_row, 1, nmos_row, 2))  # Activate nmos_row
    b = b.apply_action(('nmos3', nmos_row, 2))

    # Check that NMOS occupies rows [nmos_row, nmos_row+1, nmos_row+2]
    cell_nmos_1 = b.grid[nmos_row][2]
    cell_nmos_2 = b.grid[nmos_row + 1][2]
    cell_nmos_3 = b.grid[nmos_row + 2][2]

    assert cell_nmos_1 is not None, "NMOS pin 1 should occupy grid cell"
    assert cell_nmos_2 is not None, "NMOS pin 2 should occupy grid cell"
    assert cell_nmos_3 is not None, "NMOS pin 3 should occupy grid cell"

    nmos_comp = cell_nmos_1[0]
    assert nmos_comp.type == 'nmos3', "Component should be an NMOS"
    assert len(nmos_comp.pins) == 3, "NMOS should have 3 pins"

    print("✅ PASSED: pin_count correctly determines component size in placement")


if __name__ == '__main__':
    test_can_place_multiple_prevents_duplicate_vin_vout()
    test_can_place_multiple_allows_multiple_regular_components()
    test_pin_count_used_in_placement()

    print("\n" + "=" * 60)
    print("✅ ALL COMPONENT METADATA TESTS PASSED")
    print("=" * 60)
