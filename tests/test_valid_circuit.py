#!/usr/bin/env python3
"""
Test to verify if a manually constructed valid circuit passes validation.

This test creates a simple circuit:
  VIN → resistor → VDD
  VSS connected
  VOUT probing the midpoint

This should be a valid, complete circuit, but we expect it to fail
due to the pin auto-merging issue.
"""

import sys
from pathlib import Path

# Add core directory to path
core_dir = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(core_dir))

from topology_game_board import Breadboard


def test_simple_resistor_divider():
    """
    Test a resistor divider: VIN → R1 → midpoint → R2 → VDD

    Circuit topology:
      VIN (row 1, col 0) → wire → (row 5, col 1)
      R1 at (5,1) and (6,1)
      R2 at (6,2) and (7,2)
      (row 7, col 2) → wire → VDD (row 14, col 2)
      VOUT probes midpoint at (6,1) or (6,2)
      VSS connected

    This should form: VIN → R1 → mid → R2 → VDD with VOUT at mid

    Expected: This SHOULD be valid.
    """
    print("="*70)
    print("TEST: Resistor Divider VIN → R1 → mid → R2 → VDD")
    print("="*70)

    board = Breadboard(rows=15)

    # Step 1: Place VIN and VOUT (automatically placed by default)
    print("\n1. Initial state:")
    print(f"   VIN at row {board.VIN_ROW}")
    print(f"   VOUT at row {board.VOUT_ROW}")
    print(f"   VSS at row {board.VSS_ROW}")
    print(f"   VDD at row {board.VDD_ROW}")

    # Step 2: Wire from VIN to work row 5
    print("\n2. Wiring VIN (1,0) → (5,1)...")
    board = board.apply_action(('wire', 1, 5))
    if board is None:
        print("   ❌ FAILED: Wire action returned None")
        return False
    print("   ✓ Wire placed successfully")

    # Step 3: Place R1 on rows 5-6
    print("\n3. Placing R1 at (5,1)...")
    board = board.apply_action(('resistor', 5))
    if board is None:
        print("   ❌ FAILED: R1 placement returned None")
        return False
    print("   ✓ R1 placed successfully")

    # Step 4: Place R2 on rows 6-7 (column 2)
    print("\n4. Placing R2 at (6,2)...")
    board = board.apply_action(('resistor', 6))
    if board is None:
        print("   ❌ FAILED: R2 placement returned None")
        return False
    print("   ✓ R2 placed successfully")

    # Step 5: Wire from R2 to VDD
    print("\n5. Wiring (7,2) → VDD (14,2)...")
    board = board.apply_action(('wire', 7, 14))
    if board is None:
        print("   ❌ FAILED: Wire to VDD returned None")
        return False
    print("   ✓ Wire to VDD placed successfully")

    # Step 6: Place R3 to connect VSS
    print("\n6. Placing R3 at (8,1) to connect to VSS...")
    board = board.apply_action(('resistor', 8))
    if board is None:
        print("   ❌ FAILED: R3 placement returned None")
        return False
    print("   ✓ R3 placed successfully")

    # Step 7: Wire R3 to VSS
    print("\n7. Wiring VSS (0,0) → R3 (8,1)...")
    board = board.apply_action(('wire', 0, 8))
    if board is None:
        print("   ❌ FAILED: VSS wire returned None")
        return False
    print("   ✓ VSS wire placed successfully")

    # Step 8: Wire to connect R1 and R2 midpoints
    print("\n8. Wiring midpoints (6,1) → (6,2)...")
    board = board.apply_action(('wire', 6, 6))
    if board is None:
        print("   ❌ FAILED: Wire between midpoints returned None")
        return False
    print("   ✓ Wire between midpoints placed successfully")

    # Step 9: Wire R3 to midpoint (connect to R1-R2 junction)
    print("\n9. Wiring R3 (9,1) → midpoint (6,2)...")
    board = board.apply_action(('wire', 9, 6))
    if board is None:
        print("   ❌ FAILED: Wire from R3 to midpoint returned None")
        return False
    print("   ✓ Wire from R3 to midpoint placed successfully")

    # Step 10: Wire VOUT to midpoint between R1 and R2
    print("\n10. Wiring VOUT (13,0) → midpoint (6,1)...")
    board = board.apply_action(('wire', 13, 6))
    if board is None:
        print("   ❌ FAILED: VOUT wire returned None")
        return False
    print("   ✓ VOUT wire placed successfully")

    # Check validity
    print("\n" + "="*70)
    print("VALIDATION CHECK")
    print("="*70)

    is_valid = board.is_complete_and_valid()
    print(f"\nis_complete_and_valid(): {is_valid}")

    # Get detailed connectivity summary
    summary = board.get_connectivity_summary()

    print("\nConnectivity Summary:")
    print(f"  valid: {summary.get('valid', False)}")
    print(f"  touches_vdd: {summary.get('touches_vdd')}")
    print(f"  touches_vss: {summary.get('touches_vss', False)}")
    print(f"  vin_vout_connected: {summary.get('vin_vout_connected')}")
    print(f"  all_components_connected: {summary.get('all_components_connected', False)}")
    print(f"  vin_on_power_rail: {summary.get('vin_on_power_rail')}")
    print(f"  vout_on_power_rail: {summary.get('vout_on_power_rail', False)}")
    print(f"  vin_vout_distinct: {summary.get('vin_vout_distinct')}")

    # Debug: Print actual net mapping
    print("\n" + "="*70)
    print("NET MAPPING DEBUG")
    print("="*70)
    net_map = board._build_net_mapping()

    vin_pos = (1, 0)
    vout_pos = (13, 0)
    vdd_pos = (14, 1)
    vss_pos = (0, 0)
    resistor_pin1 = (5, 1)
    resistor_pin2 = (6, 1)

    print(f"VIN position {vin_pos}: net = {net_map.get(vin_pos, 'NOT FOUND')}")
    print(f"VOUT position {vout_pos}: net = {net_map.get(vout_pos, 'NOT FOUND')}")
    print(f"VDD position {vdd_pos}: net = {net_map.get(vdd_pos, 'NOT FOUND')}")
    print(f"VSS position {vss_pos}: net = {net_map.get(vss_pos, 'NOT FOUND')}")
    print(f"Resistor pin 1 {resistor_pin1}: net = {net_map.get(resistor_pin1, 'NOT FOUND')}")
    print(f"Resistor pin 2 {resistor_pin2}: net = {net_map.get(resistor_pin2, 'NOT FOUND')}")
    print(f"VSS wire target (7, 1): net = {net_map.get((7, 1), 'NOT FOUND')}")

    print(f"\nAll positions in net map: {sorted(net_map.keys())}")

    # Show the full summary dict
    print(f"\nFull summary dict: {summary}")

    # Check components
    print("\nComponents on board:")
    for comp in board.placed_components:
        if comp.type not in ['wire']:
            nets_for_comp = {net_map.get(pin, 'NOT FOUND') for pin in comp.pins}
            print(f"  {comp.type} (id={comp.id}): pins={comp.pins}, nets={nets_for_comp}")

    # Analyze what went wrong
    print("\n" + "="*70)
    print("DIAGNOSIS")
    print("="*70)

    return summary.get('valid', False)


def test_wire_ordering_constraint():
    """
    Test if we can wire FROM VDD to a work row.

    This tests the wire ordering constraint (r1, c1) >= (r2, c2).
    """
    print("\n" + "="*70)
    print("TEST: Wire Ordering Constraint (VDD → work row)")
    print("="*70)

    board = Breadboard(rows=15)

    # Try to wire from VDD (14, 1) to work row (5, 1)
    print(f"\nAttempting: wire from VDD ({board.VDD_ROW}, 1) → work row (5, 1)")

    # Check if this action is even available
    actions = board.legal_actions()
    wire_actions = [a for a in actions if a[0] == 'wire']

    target_wire = ('wire', 14, 5)
    reverse_wire = ('wire', 5, 14)

    if target_wire in wire_actions:
        print(f"✓ Action {target_wire} is available")
    elif reverse_wire in wire_actions:
        print(f"⚠ Action {reverse_wire} is available (reverse order)")
    else:
        print(f"❌ Neither {target_wire} nor {reverse_wire} is available")
        print("   This confirms the wire ordering constraint prevents VDD → work row")

        # Check if work row is inactive
        print(f"\n   Checking if row 5 is active: {board.is_row_active(5)}")
        print(f"   Checking if VDD row {board.VDD_ROW} is active: {board.is_row_active(board.VDD_ROW)}")

        return False

    return True


if __name__ == "__main__":
    print("TESTING VALID CIRCUIT CONSTRUCTION\n")

    # Test 1: Wire ordering constraint
    result1 = test_wire_ordering_constraint()

    # Test 2: Valid circuit construction
    result2 = test_simple_resistor_divider()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Wire ordering test: {'PASS' if result1 else 'FAIL'}")
    print(f"Valid circuit test: {'PASS' if result2 else 'FAIL'}")

    if not result1:
        print("\n⚠ Wire ordering constraint prevents VDD from seeding work rows")

    if not result2:
        print("⚠ Valid circuits are incorrectly marked as invalid")
