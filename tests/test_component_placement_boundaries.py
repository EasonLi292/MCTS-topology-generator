#!/usr/bin/env python3
"""
Test suite for component placement boundary rules in can_place_component().

These tests explicitly verify placement constraints:
1. Components cannot be placed ON VIN_ROW
2. Components cannot be placed ON VOUT_ROW
3. Multi-pin components cannot span VIN_ROW
4. Components CAN be placed adjacent to VIN (exception path)
5. Components CAN be placed adjacent to VOUT (exception path)
6. Work area boundaries are enforced
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard


def test_cannot_place_component_on_vin_row():
    """Test that components cannot be placed directly on VIN_ROW."""
    print("\n=== Test 1: Cannot Place Component on VIN_ROW ===")

    b = Breadboard()

    # VIN is at row 1 (VIN_ROW)
    # Try to place a resistor (2 pins) starting at VIN_ROW
    can_place = b.can_place_component('resistor', b.VIN_ROW, 2)

    assert not can_place, "Resistor should not be placeable on VIN_ROW"

    # Try with other component types
    can_place_cap = b.can_place_component('capacitor', b.VIN_ROW, 3)
    assert not can_place_cap, "Capacitor should not be placeable on VIN_ROW"

    can_place_nmos = b.can_place_component('nmos3', b.VIN_ROW, 4)
    assert not can_place_nmos, "NMOS should not be placeable on VIN_ROW"

    print("✅ PASSED: Components correctly prevented from VIN_ROW placement")


def test_cannot_place_component_on_vout_row():
    """Test that components cannot be placed directly on VOUT_ROW."""
    print("\n=== Test 2: Cannot Place Component on VOUT_ROW ===")

    b = Breadboard()

    # VOUT is at row ROWS-2 (VOUT_ROW)
    # Try to place a resistor (2 pins) starting at VOUT_ROW
    can_place = b.can_place_component('resistor', b.VOUT_ROW, 2)

    assert not can_place, "Resistor should not be placeable on VOUT_ROW"

    # Try with other component types
    can_place_cap = b.can_place_component('capacitor', b.VOUT_ROW, 3)
    assert not can_place_cap, "Capacitor should not be placeable on VOUT_ROW"

    can_place_nmos = b.can_place_component('nmos3', b.VOUT_ROW, 4)
    assert not can_place_nmos, "NMOS should not be placeable on VOUT_ROW"

    # Also try placing just before VOUT_ROW where it would end ON VOUT_ROW
    # A 2-pin component starting at VOUT_ROW-1 would occupy rows [VOUT_ROW-1, VOUT_ROW]
    can_place_spanning = b.can_place_component('resistor', b.VOUT_ROW - 1, 2)
    assert not can_place_spanning, "Resistor spanning onto VOUT_ROW should be rejected"

    print("✅ PASSED: Components correctly prevented from VOUT_ROW placement")


def test_cannot_place_multipin_spanning_vin_row():
    """Test that multi-pin components cannot span across VIN_ROW."""
    print("\n=== Test 3: Cannot Place Multi-pin Spanning VIN_ROW ===")

    b = Breadboard()

    # VIN_ROW is at row 1
    # VSS_ROW is at row 0
    # A 2-pin resistor starting at row 0 (VSS) would span rows [0, 1], including VIN_ROW
    can_place_from_vss = b.can_place_component('resistor', b.VSS_ROW, 2)

    assert not can_place_from_vss, "Component should not span from VSS_ROW across VIN_ROW"

    # A 3-pin transistor starting at row 0 would span [0, 1, 2], including VIN_ROW
    can_place_nmos_from_vss = b.can_place_component('nmos3', b.VSS_ROW, 3)

    assert not can_place_nmos_from_vss, "NMOS should not span from VSS_ROW across VIN_ROW"

    print("✅ PASSED: Multi-pin components correctly prevented from spanning VIN_ROW")


def test_can_place_adjacent_to_vin():
    """Test that components require wire connections before placement (no adjacency exception)."""
    print("\n=== Test 4: Components Require Active Net Connection ===")

    b = Breadboard()

    # VIN_ROW is at row 1, so VIN_ROW + 1 = row 2 (WORK_START_ROW)
    # Components cannot be placed without active net connection (adjacency removed)
    can_place_without_wire = b.can_place_component('resistor', b.VIN_ROW + 1, 2)

    # This should be FALSE because no wire has activated the row yet
    assert not can_place_without_wire, "Component should NOT be placeable without wire activation"

    # Now wire from VIN to activate the row
    b = b.apply_action(('wire', b.VIN_ROW, 0, b.VIN_ROW + 1, 2))

    # Now placement should work
    can_place_with_wire = b.can_place_component('resistor', b.VIN_ROW + 1, 2)
    assert can_place_with_wire, "Component should be placeable after wire activation"

    print("✅ PASSED: Component placement requires wire activation")


def test_can_place_adjacent_to_vout():
    """Test that components near VOUT also require wire connections."""
    print("\n=== Test 5: Components Near VOUT Require Active Net ===")

    b = Breadboard()

    # VOUT_ROW is at row ROWS-2, so VOUT_ROW - 1 = row ROWS-3 (WORK_END_ROW)
    # A 2-pin component ENDING at WORK_END_ROW should NOT be placeable without activation
    start_row = b.VOUT_ROW - 2  # This will end at VOUT_ROW - 1 (just before VOUT)

    can_place_without_wire = b.can_place_component('resistor', start_row, 2)

    # This should be FALSE because no wire has activated the rows yet
    assert not can_place_without_wire, "Component should NOT be placeable near VOUT without activation"

    # Wire from VIN through the work area to activate the target row
    b = b.apply_action(('wire', b.VIN_ROW, 0, start_row, 2))

    # Now placement should work
    can_place_with_wire = b.can_place_component('resistor', start_row, 2)
    assert can_place_with_wire, "Component should be placeable after wire activation"

    print("✅ PASSED: Components near VOUT require wire activation")


def test_work_area_boundaries_enforced():
    """Test comprehensive work area boundary enforcement."""
    print("\n=== Test 6: Work Area Boundaries Enforced ===")

    b = Breadboard()

    # Work area is from WORK_START_ROW (2) to WORK_END_ROW (ROWS-3)
    print(f"  Work area: rows {b.WORK_START_ROW} to {b.WORK_END_ROW}")
    print(f"  Board: {b.ROWS} rows total")
    print(f"  VIN_ROW={b.VIN_ROW}, VOUT_ROW={b.VOUT_ROW}")
    print(f"  VSS_ROW={b.VSS_ROW}, VDD_ROW={b.VDD_ROW}")

    # Test placement at various boundary positions
    # Note: Component placement requires pins_touch_active (wire connection required)

    # 1. Cannot place at start of work area without wire activation
    can_place_without_wire = b.can_place_component('resistor', b.WORK_START_ROW, 1)
    assert not can_place_without_wire, f"Should NOT be able to place at WORK_START_ROW without wire activation"

    # 1b. Wire from VIN to activate the row, then place component
    b = b.apply_action(('wire', b.VIN_ROW, 0, b.WORK_START_ROW, 1))
    can_place_start = b.can_place_component('resistor', b.WORK_START_ROW, 1)
    assert can_place_start, f"Should be able to place at WORK_START_ROW ({b.WORK_START_ROW}) after wire activation"

    # 2. Valid placement in middle of work area (after activating the row)
    # First, place a component on the already-activated row
    b = b.apply_action(('resistor', b.WORK_START_ROW, 1))

    # Now wire to middle row to activate it
    mid_row = b.WORK_START_ROW + 3
    b = b.apply_action(('wire', b.WORK_START_ROW, 1, mid_row, 2))

    # Now we should be able to place on the activated middle row
    can_place_middle = b.can_place_component('capacitor', mid_row, 3)
    assert can_place_middle, f"Should be able to place in middle of work area after activation (row {mid_row})"

    # 3. Valid placement ending at end of work area (after activation)
    # A 2-pin component at WORK_END_ROW - 1 ends at WORK_END_ROW
    # First need to activate the row via wire
    b = b.apply_action(('wire', mid_row, 2, b.WORK_END_ROW - 1, 4))
    can_place_end = b.can_place_component('inductor', b.WORK_END_ROW - 1, 4)
    assert can_place_end, f"Should be able to place ending at WORK_END_ROW ({b.WORK_END_ROW}) after activation"

    # 4. Invalid: Component extending beyond WORK_END_ROW
    # A 2-pin component at WORK_END_ROW would extend to WORK_END_ROW + 1 (which is VOUT_ROW)
    can_place_beyond_end = b.can_place_component('resistor', b.WORK_END_ROW, 1)
    assert not can_place_beyond_end, "Should NOT be able to place component extending beyond WORK_END_ROW"

    # 5. Invalid: Component starting before WORK_START_ROW (on VIN_ROW)
    # WORK_START_ROW - 1 = VIN_ROW, which is not allowed
    can_place_before_start = b.can_place_component('resistor', b.WORK_START_ROW - 1, 5)
    assert not can_place_before_start, f"Should NOT be able to place component starting at VIN_ROW ({b.WORK_START_ROW - 1})"

    # 6. Invalid: Component on power rails
    can_place_vss = b.can_place_component('resistor', b.VSS_ROW, 1)
    assert not can_place_vss, "Should NOT be able to place component on VSS_ROW"

    can_place_vdd = b.can_place_component('resistor', b.VDD_ROW - 1, 1)
    assert not can_place_vdd, "Should NOT be able to place component ending on VDD_ROW"

    print("✅ PASSED: Work area boundaries comprehensively enforced")


if __name__ == '__main__':
    test_cannot_place_component_on_vin_row()
    test_cannot_place_component_on_vout_row()
    test_cannot_place_multipin_spanning_vin_row()
    test_can_place_adjacent_to_vin()
    test_can_place_adjacent_to_vout()
    test_work_area_boundaries_enforced()

    print("\n" + "=" * 60)
    print("✅ ALL COMPONENT PLACEMENT BOUNDARY TESTS PASSED")
    print("=" * 60)
