#!/usr/bin/env python3
"""
Test to verify that a valid circuit can be constructed through legal actions.

This test follows the design rule: components are placed in the leftmost
available column only (to reduce action space complexity).
"""

import sys
from pathlib import Path

# Add core directory to path
core_dir = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(core_dir))

from topology_game_board import Breadboard


def test_simple_valid_circuit():
    """
    Build a simple valid circuit following the leftmost-column rule.

    Circuit strategy:
    - Place all components in column 1 (leftmost available)
    - Use wires to connect components and rails
    - Create VIN → R1 → midpoint → R2 → VDD path
    - Connect R3 from midpoint to VSS
    - VOUT probes midpoint
    """
    print("="*70)
    print("TEST: Simple Valid Circuit (Following Leftmost-Column Rule)")
    print("="*70)
    print("\nBuilding circuit with all components in column 1.\n")

    board = Breadboard(rows=15)
    step = 0
    all_actions_legal = True

    # All components will be placed in column 1
    # We need to carefully arrange rows to create the right connectivity
    actions_sequence = [
        # Step 1: Wire VIN to work row 5
        ('wire', 1, 0, 5, 1, "Wire VIN (1,0) → (5,1)"),

        # Step 2: Place R1 at rows 5-6 (VIN side)
        ('resistor', 5, 1, "Place R1 at (5,1)-(6,1)"),

        # Step 3: Wire from R1 pin 2 to activate row 7
        ('wire', 6, 1, 7, 1, "Wire R1 pin 2 (6,1) → row 7 to activate it"),

        # Step 4: Place R2 at rows 7-8 (now row 7 is active!)
        ('resistor', 7, 1, "Place R2 at (7,1)-(8,1)"),

        # Step 5: Wire R2 pin 2 to VDD
        ('wire', 8, 1, 14, 1, "Wire R2 (8,1) → VDD (14,1)"),

        # Step 6: Wire VSS to activate row 9
        ('wire', 0, 0, 9, 1, "Wire VSS (0,0) → row 9 to activate it"),

        # Step 7: Place R3 at rows 9-10 (for VSS connection, row 9 now active)
        ('resistor', 9, 1, "Place R3 at (9,1)-(10,1)"),

        # Step 8: Wire midpoint to R3 pin 2 (connect to R1-R2 junction)
        ('wire', 6, 1, 10, 1, "Wire midpoint (6,1) → R3 (10,1)"),

        # Step 9: Wire midpoint to VOUT
        ('wire', 6, 1, 13, 0, "Wire midpoint (6,1) → VOUT (13,0)"),
    ]

    for action_data in actions_sequence:
        step += 1

        # Extract action and description
        if len(action_data) == 4:
            action = action_data[:3]
            description = action_data[3]
        else:
            action = action_data[:5]
            description = action_data[5]

        print(f"Step {step}: {description}")

        # Get legal actions
        legal_actions = board.legal_actions()

        # Check if action is legal
        if action in legal_actions:
            print(f"  ✓ Action is LEGAL")

            # Apply the action
            new_board = board.apply_action(action)
            if new_board is None:
                print(f"  ❌ ERROR: apply_action returned None!")
                all_actions_legal = False
                break

            board = new_board
            print(f"  ✓ Applied successfully")

        else:
            print(f"  ❌ Action {action} is NOT in legal actions!")
            print(f"  Total legal actions: {len(legal_actions)}")

            # Show what component column is available
            target_col = board._find_target_column()
            print(f"  Target column for components: {target_col}")

            # Show active rows
            print(f"\n  Active rows:")
            for r in range(board.ROWS):
                if board.is_row_active(r):
                    print(f"    Row {r}")

            # If component action, check why it can't be placed
            if action[0] not in ['wire', 'stop']:
                comp_type, start_row, col = action[0], action[1], action[2]
                can_place = board.can_place_component(comp_type, start_row, col)
                print(f"\n  can_place_component({comp_type}, {start_row}, {col}): {can_place}")

                from topology_game_board import COMPONENT_CATALOG
                info = COMPONENT_CATALOG.get(comp_type)
                if info:
                    pin_rows = list(range(start_row, start_row + info.pin_count))
                    print(f"  Pin rows: {pin_rows}")
                    print(f"  Rows active: {[board.is_row_active(r) for r in pin_rows]}")
                    print(f"  Cells empty: {[board.is_empty(r, col) for r in pin_rows]}")

            # Debug info
            if action[0] == 'wire':
                wire_actions = [a for a in legal_actions if a[0] == 'wire']
                print(f"  Available wire actions: {len(wire_actions)}")
                # Check for reverse wire
                reverse = ('wire', action[3], action[4], action[1], action[2])
                if reverse in legal_actions:
                    print(f"  ⚠ Reverse wire IS available: {reverse}")
            else:
                comp_type = action[0]
                comp_actions = [a for a in legal_actions if a[0] == comp_type]
                print(f"  Available {comp_type} actions: {len(comp_actions)}")
                if comp_actions:
                    print(f"  Sample actions: {comp_actions[:3]}")

            all_actions_legal = False
            break

        print()

    # Final validation
    print("="*70)
    print("FINAL VALIDATION")
    print("="*70)

    if all_actions_legal:
        print(f"\n✓ All {step} actions were legal!")

        is_valid = board.is_complete_and_valid()
        print(f"\nFinal circuit is_complete_and_valid(): {is_valid}")

        if is_valid:
            print("\n🎉 SUCCESS! Valid circuit reachable through legal actions!")

            summary = board.get_connectivity_summary()
            print(f"\nConnectivity:")
            print(f"  touches_vdd: {summary.get('touches_vdd', False)}")
            print(f"  touches_vss: {summary.get('touches_vss', False)}")
            print(f"  vin_vout_distinct: {summary.get('vin_vout_distinct', False)}")
            print(f"  all_components_connected: {summary.get('all_components_connected', False)}")

            # Try to get netlist
            netlist = board.to_netlist()
            if netlist:
                print(f"\n✓ Circuit generates valid SPICE netlist")
            else:
                print(f"\n⚠ No netlist generated")

            return True
        else:
            print("\n❌ Circuit reached but not valid!")
            summary = board.get_connectivity_summary()
            print(f"\nWhy invalid:")
            for key in ['touches_vdd', 'touches_vss', 'vin_vout_distinct',
                       'all_components_connected', 'vin_on_power_rail',
                       'vout_on_power_rail']:
                print(f"  {key}: {summary.get(key, False)}")
            return False
    else:
        print(f"\n❌ FAILURE at step {step}!")
        print("Search space insufficient even with leftmost-column rule.")
        return False


if __name__ == "__main__":
    print("TESTING SEARCH SPACE (LEFTMOST-COLUMN RULE)\n")

    result = test_simple_valid_circuit()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if result:
        print("\n✓ Valid circuits ARE reachable following the leftmost-column rule!")
        print("  MCTS should be able to discover valid circuits.")
        print("  If it's not finding them, the issue is search strategy/iterations.")
    else:
        print("\n❌ Valid circuits are NOT reachable even with leftmost-column rule!")
        print("  There are still fundamental blockers in the action space.")
