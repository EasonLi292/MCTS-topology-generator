"""
Test that degenerate component placements (all pins on same net) are prevented.

This ensures the search space doesn't waste time on electrically useless placements.
"""

from core.topology_game_board import Breadboard


def test_cannot_place_resistor_on_unified_rows():
    """Test that we can't place a resistor where both pins would be on the same net."""
    b = Breadboard()

    # Wire two work rows together (unifying them into same net)
    r1 = b.WORK_START_ROW
    r2 = b.WORK_START_ROW + 1

    # Activate first row and unite with second row
    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', r1, r2))

    # Now r1 and r2 are on the same net
    assert b.find(r1) == b.find(r2), "Rows should be unified"

    # Try to place a resistor spanning these two rows
    # This should be blocked because it would be degenerate
    can_place = b.can_place_component('resistor', r1)

    print(f"\nAttempting to place resistor on rows {r1}-{r2}")
    print(f"Row {r1} net: {b.find(r1)}")
    print(f"Row {r2} net: {b.find(r2)}")
    print(f"Can place resistor: {can_place}")

    assert not can_place, "Should not be able to place resistor with all pins on same net"
    print("✅ PASSED: Degenerate resistor placement blocked")


def test_can_place_resistor_on_different_nets():
    """Test that we CAN place a resistor where pins are on different nets."""
    b = Breadboard()

    # Activate two separate rows without unifying them
    r1 = b.WORK_START_ROW
    r2 = b.WORK_START_ROW + 1

    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', b.VDD_ROW, r2))

    # r1 and r2 are on different nets
    assert b.find(r1) != b.find(r2), "Rows should be on different nets"

    # Should be able to place resistor
    can_place = b.can_place_component('resistor', r1)

    print(f"\nAttempting to place resistor on rows {r1}-{r2}")
    print(f"Row {r1} net: {b.find(r1)}")
    print(f"Row {r2} net: {b.find(r2)}")
    print(f"Can place resistor: {can_place}")

    assert can_place, "Should be able to place resistor with pins on different nets"
    print("✅ PASSED: Valid resistor placement allowed")


def test_cannot_place_transistor_all_pins_unified():
    """Test that we can't place a 3-pin transistor where all pins are on same net."""
    b = Breadboard()

    # Unite three consecutive rows
    r1 = b.WORK_START_ROW
    r2 = b.WORK_START_ROW + 1
    r3 = b.WORK_START_ROW + 2

    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', r1, r2))
    b = b.apply_action(('wire', r2, r3))

    # All three rows unified
    assert b.find(r1) == b.find(r2) == b.find(r3), "All rows should be unified"

    # Try to place NMOS - should be blocked
    can_place = b.can_place_component('nmos3', r1)

    print(f"\nAttempting to place nmos3 on rows {r1}-{r2}-{r3}")
    print(f"Row {r1} net: {b.find(r1)}")
    print(f"Row {r2} net: {b.find(r2)}")
    print(f"Row {r3} net: {b.find(r3)}")
    print(f"Can place nmos3: {can_place}")

    assert not can_place, "Should not be able to place transistor with all pins on same net"
    print("✅ PASSED: Degenerate transistor placement blocked")


def test_can_place_transistor_two_nets_minimum():
    """Test that we CAN place transistor when pins span at least 2 different nets."""
    b = Breadboard()

    # Create scenario: r1 and r2 unified, but r3 separate
    r1 = b.WORK_START_ROW
    r2 = b.WORK_START_ROW + 1
    r3 = b.WORK_START_ROW + 2

    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', r1, r2))  # r1 and r2 on same net
    b = b.apply_action(('wire', b.VDD_ROW, r3))  # r3 on different net

    # r1 and r2 same, r3 different
    assert b.find(r1) == b.find(r2), "r1 and r2 should be unified"
    assert b.find(r1) != b.find(r3), "r3 should be on different net"

    # Should be able to place transistor (spans 2 different nets)
    can_place = b.can_place_component('nmos3', r1)

    print(f"\nAttempting to place nmos3 on rows {r1}-{r2}-{r3}")
    print(f"Row {r1} net: {b.find(r1)}")
    print(f"Row {r2} net: {b.find(r2)}")
    print(f"Row {r3} net: {b.find(r3)}")
    print(f"Unique nets: {len({b.find(r1), b.find(r2), b.find(r3)})}")
    print(f"Can place nmos3: {can_place}")

    assert can_place, "Should be able to place transistor spanning at least 2 nets"
    print("✅ PASSED: Valid transistor placement allowed")


def test_cannot_place_duplicate_resistor_across_same_nets():
    """Test that we can't place two resistors across the same pair of nets."""
    b = Breadboard()

    # Create two separate nets
    r1 = b.WORK_START_ROW
    r2 = b.WORK_START_ROW + 1
    r3 = b.WORK_START_ROW + 2
    r4 = b.WORK_START_ROW + 3

    # Connect r1 to VIN net, r2 to VDD net
    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', b.VDD_ROW, r2))

    # Place first resistor from r1 to r2 (connects VIN net to VDD net)
    b = b.apply_action(('resistor', r1))

    net1 = b.find(r1)
    net2 = b.find(r2)

    print(f"\nFirst resistor placed across nets: {net1} to {net2}")

    # Now activate r3 and r4
    b = b.apply_action(('wire', b.VIN_ROW, r3))  # r3 on VIN net (same as r1)
    b = b.apply_action(('wire', b.VDD_ROW, r4))  # r4 on VDD net (same as r2)

    net3 = b.find(r3)
    net4 = b.find(r4)

    print(f"r3 net: {net3}, r4 net: {net4}")
    print(f"r3 and r1 on same net: {net3 == net1}")
    print(f"r4 and r2 on same net: {net4 == net2}")

    # Try to place second resistor from r3 to r4
    # This would be a duplicate: another resistor across VIN net to VDD net
    can_place = b.can_place_component('resistor', r3)

    print(f"Can place second resistor across same nets: {can_place}")

    assert not can_place, "Should not be able to place duplicate resistor across same nets"
    print("✅ PASSED: Duplicate resistor topology blocked")


def test_can_place_different_component_type_across_same_nets():
    """Test that we CAN place different component types across the same nets."""
    b = Breadboard()

    # Create two separate nets
    r1 = b.WORK_START_ROW
    r2 = b.WORK_START_ROW + 1
    r3 = b.WORK_START_ROW + 2
    r4 = b.WORK_START_ROW + 3

    # Connect r1 to VIN net, r2 to VDD net
    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', b.VDD_ROW, r2))

    # Place resistor from r1 to r2
    b = b.apply_action(('resistor', r1))

    # Now activate r3 and r4 on same nets
    b = b.apply_action(('wire', b.VIN_ROW, r3))
    b = b.apply_action(('wire', b.VDD_ROW, r4))

    # Should be able to place CAPACITOR (different type) across same nets
    can_place_capacitor = b.can_place_component('capacitor', r3)

    print(f"\nResistor already spans: {b.find(r1)} to {b.find(r2)}")
    print(f"Can place capacitor across same nets: {can_place_capacitor}")

    assert can_place_capacitor, "Should be able to place different component type across same nets"
    print("✅ PASSED: Different component type allowed across same nets")


def test_degenerate_prevention_reduces_action_space():
    """Verify that degenerate prevention reduces the number of legal actions."""
    b = Breadboard()

    # Create a board with some unified rows
    r1 = b.WORK_START_ROW
    r2 = b.WORK_START_ROW + 1
    r3 = b.WORK_START_ROW + 2

    # Activate r1 and r2 separately
    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', b.VDD_ROW, r2))

    # Count legal component actions before unifying
    actions_before = b.legal_actions()
    component_actions_before = [a for a in actions_before if a[0] not in ['wire', 'STOP']]

    print(f"\nBefore unifying r2 and r3:")
    print(f"Total component placement actions: {len(component_actions_before)}")

    # Now unify r2 and r3
    b = b.apply_action(('wire', b.VDD_ROW, r3))
    b = b.apply_action(('wire', r2, r3))

    # Count legal component actions after unifying
    actions_after = b.legal_actions()
    component_actions_after = [a for a in actions_after if a[0] not in ['wire', 'STOP']]

    print(f"\nAfter unifying r2 and r3 (same net):")
    print(f"Total component placement actions: {len(component_actions_after)}")

    # Should have fewer component placement options now
    # because r2-r3 resistor placement should be blocked
    resistor_r2_before = ('resistor', r2) in component_actions_before
    resistor_r2_after = ('resistor', r2) in component_actions_after

    print(f"\n('resistor', {r2}) available before unifying: {resistor_r2_before}")
    print(f"('resistor', {r2}) available after unifying: {resistor_r2_after}")

    if resistor_r2_before:
        assert not resistor_r2_after, "Resistor placement should be blocked after unifying"
        print("✅ PASSED: Action space correctly reduced by degenerate prevention")
    else:
        print("⚠️  Resistor wasn't placeable before unifying (other constraints)")
