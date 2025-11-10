#!/usr/bin/env python3
"""
Test to verify that a valid circuit can be constructed through legal actions.

This test builds a simple valid circuit step-by-step and checks that each
action is available in the legal action space at each step. This verifies
that MCTS has a path to discover valid circuits.
"""

import sys
from pathlib import Path

# Add core directory to path
core_dir = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(core_dir))

from topology_game_board import Breadboard


def test_search_space_reachability():
    """
    Build a simple valid circuit step-by-step, checking that each action
    is in the legal action space.

    Circuit: VIN → R1 → R2 → VDD, with R3 to VSS, VOUT probing midpoint

    This is the simplest possible valid circuit.
    """
    print("="*70)
    print("TEST: Search Space Reachability")
    print("="*70)
    print("\nBuilding a valid circuit step-by-step and verifying each")
    print("action is available in the legal action space.\n")

    board = Breadboard(rows=15)
    step = 0
    all_actions_legal = True

    # Define the sequence of actions to build a valid circuit
    actions_sequence = [
        # Step 1: Wire VIN to work row
        ('wire', 1, 0, 5, 1, "Wire VIN (1,0) → (5,1)"),

        # Step 2: Place R1
        ('resistor', 5, 1, "Place R1 at (5,1)-(6,1)"),

        # Step 3: Place R2
        ('resistor', 6, 2, "Place R2 at (6,2)-(7,2)"),

        # Step 4: Wire R1 and R2 midpoints together
        ('wire', 6, 1, 6, 2, "Wire midpoints (6,1) ↔ (6,2)"),

        # Step 5: Wire R2 to VDD
        ('wire', 7, 2, 14, 2, "Wire R2 (7,2) → VDD (14,2)"),

        # Step 6: Place R3 for VSS connection
        ('resistor', 8, 1, "Place R3 at (8,1)-(9,1)"),

        # Step 7: Wire R3 to VSS
        ('wire', 0, 0, 8, 1, "Wire VSS (0,0) → R3 (8,1)"),

        # Step 8: Wire R3 to midpoint
        ('wire', 9, 1, 6, 2, "Wire R3 (9,1) → midpoint (6,2)"),

        # Step 9: Wire VOUT to midpoint
        ('wire', 13, 0, 6, 1, "Wire VOUT (13,0) → midpoint (6,1)"),
    ]

    for action_data in actions_sequence:
        step += 1

        # Extract action and description
        if len(action_data) == 4:
            # Component placement
            action = action_data[:3]
            description = action_data[3]
        else:
            # Wire placement
            action = action_data[:5]
            description = action_data[5]

        print(f"Step {step}: {description}")

        # Get legal actions at this state
        legal_actions = board.legal_actions()

        # Check if our intended action is legal
        if action in legal_actions:
            print(f"  ✓ Action {action} is LEGAL")

            # Apply the action
            new_board = board.apply_action(action)
            if new_board is None:
                print(f"  ❌ ERROR: apply_action returned None!")
                all_actions_legal = False
                break

            board = new_board
            print(f"  ✓ Action applied successfully")

        else:
            print(f"  ❌ Action {action} is NOT in legal actions!")
            print(f"  Total legal actions at this step: {len(legal_actions)}")

            # Debug: show what rows are active
            print(f"\n  Debug - Active rows:")
            for r in range(board.ROWS):
                if board.is_row_active(r):
                    print(f"    Row {r}: active")

            # Debug: show grid state
            print(f"\n  Debug - Grid occupancy:")
            for r in range(board.ROWS):
                occupied_cols = [c for c in range(board.COLUMNS) if not board.is_empty(r, c)]
                if occupied_cols:
                    print(f"    Row {r}: columns {occupied_cols}")

            # Debug: if it's a component action, check why it can't be placed
            if action[0] not in ['wire', 'stop']:
                comp_type, start_row, col = action[0], action[1], action[2]
                print(f"\n  Debug - Checking can_place_component({comp_type}, {start_row}, {col}):")
                print(f"    WORK_START_ROW: {board.WORK_START_ROW}")
                print(f"    WORK_END_ROW: {board.WORK_END_ROW}")

                from topology_game_board import COMPONENT_CATALOG
                info = COMPONENT_CATALOG.get(comp_type)
                if info:
                    pin_rows = range(start_row, start_row + info.pin_count)
                    print(f"    Pin rows: {list(pin_rows)}")
                    print(f"    pin_rows.start: {pin_rows.start}")
                    print(f"    pin_rows.stop - 1: {pin_rows.stop - 1}")
                    print(f"    Cells empty: {[board.is_empty(r, col) for r in pin_rows]}")
                    print(f"    Rows active: {[board.is_row_active(r) for r in pin_rows]}")
                    print(f"    Any active: {any(board.is_row_active(r) for r in pin_rows)}")

                    # Call the actual method
                    can_place = board.can_place_component(comp_type, start_row, col)
                    print(f"    can_place_component result: {can_place}")

            # Show similar actions for debugging
            if action[0] == 'wire':
                wire_actions = [a for a in legal_actions if a[0] == 'wire']
                print(f"  Available wire actions: {len(wire_actions)}")

                # Check if reverse wire is available
                reverse_action = ('wire', action[3], action[4], action[1], action[2])
                if reverse_action in legal_actions:
                    print(f"  ⚠ Reverse wire {reverse_action} IS available")

                # Show a few sample wire actions
                print(f"  Sample wire actions:")
                for sample in list(wire_actions)[:5]:
                    print(f"    {sample}")
            else:
                comp_actions = [a for a in legal_actions if a[0] == action[0]]
                print(f"  Available {action[0]} actions: {len(comp_actions)}")
                print(f"  Sample {action[0]} actions:")
                for sample in list(comp_actions)[:5]:
                    print(f"    {sample}")

            all_actions_legal = False
            break

        print()

    # Final validation
    print("="*70)
    print("FINAL VALIDATION")
    print("="*70)

    if all_actions_legal:
        print(f"\n✓ All {step} actions were legal!")

        # Check if final circuit is valid
        is_valid = board.is_complete_and_valid()
        print(f"\nFinal circuit is_complete_and_valid(): {is_valid}")

        if is_valid:
            print("\n🎉 SUCCESS! Valid circuit is reachable through legal actions!")
            summary = board.get_connectivity_summary()
            print(f"\nConnectivity summary:")
            print(f"  touches_vdd: {summary.get('touches_vdd', False)}")
            print(f"  touches_vss: {summary.get('touches_vss', False)}")
            print(f"  vin_vout_distinct: {summary.get('vin_vout_distinct', False)}")
            print(f"  all_components_connected: {summary.get('all_components_connected', False)}")
            return True
        else:
            print("\n❌ Circuit reached but not valid!")
            summary = board.get_connectivity_summary()
            print(f"\nConnectivity summary:")
            for key, val in summary.items():
                if key not in ['component_nets', 'visited_nets', 'vin_net', 'vout_net']:
                    print(f"  {key}: {val}")
            return False
    else:
        print(f"\n❌ FAILURE at step {step}!")
        print("The search space does NOT contain a path to valid circuits!")
        print("MCTS cannot discover valid circuits with current action space.")
        return False


def test_alternative_simple_circuit():
    """
    Try an even simpler circuit: just one resistor from VIN to VDD.

    Circuit: VIN → R → VDD, with another R to VSS, VOUT at VDD
    """
    print("\n" + "="*70)
    print("TEST: Alternative Simple Circuit")
    print("="*70)
    print("\nTrying an even simpler valid circuit.\n")

    board = Breadboard(rows=15)
    step = 0
    all_actions_legal = True

    actions_sequence = [
        # Step 1: Wire VIN to work row
        ('wire', 1, 0, 5, 1, "Wire VIN (1,0) → (5,1)"),

        # Step 2: Place R1 VIN to intermediate
        ('resistor', 5, 1, "Place R1 at (5,1)-(6,1)"),

        # Step 3: Wire intermediate to VDD
        ('wire', 6, 1, 14, 1, "Wire (6,1) → VDD (14,1)"),

        # Step 4: Place R2 for VSS
        ('resistor', 7, 1, "Place R2 at (7,1)-(8,1)"),

        # Step 5: Wire R2 to VSS
        ('wire', 0, 0, 7, 1, "Wire VSS (0,0) → R2 (7,1)"),

        # Step 6: Wire R2 to intermediate (connect to R1)
        ('wire', 8, 1, 6, 1, "Wire R2 (8,1) → intermediate (6,1)"),

        # Step 7: Wire VOUT to intermediate
        ('wire', 13, 0, 6, 1, "Wire VOUT (13,0) → intermediate (6,1)"),
    ]

    for action_data in actions_sequence:
        step += 1

        if len(action_data) == 4:
            action = action_data[:3]
            description = action_data[3]
        else:
            action = action_data[:5]
            description = action_data[5]

        print(f"Step {step}: {description}")

        legal_actions = board.legal_actions()

        if action in legal_actions:
            print(f"  ✓ Action is LEGAL")
            new_board = board.apply_action(action)
            if new_board is None:
                print(f"  ❌ ERROR: apply_action returned None!")
                all_actions_legal = False
                break
            board = new_board
        else:
            print(f"  ❌ Action {action} is NOT in legal actions!")
            all_actions_legal = False
            break

        print()

    print("="*70)
    print("FINAL VALIDATION")
    print("="*70)

    if all_actions_legal:
        is_valid = board.is_complete_and_valid()
        print(f"\nFinal circuit is_complete_and_valid(): {is_valid}")

        if is_valid:
            print("\n🎉 Alternative circuit is also reachable!")
            return True
        else:
            print("\n❌ Circuit reached but not valid!")
            return False
    else:
        print(f"\n❌ FAILURE at step {step}!")
        return False


if __name__ == "__main__":
    print("TESTING SEARCH SPACE REACHABILITY\n")

    result1 = test_search_space_reachability()
    result2 = test_alternative_simple_circuit()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Main circuit test: {'PASS' if result1 else 'FAIL'}")
    print(f"Alternative circuit test: {'PASS' if result2 else 'FAIL'}")

    if result1 and result2:
        print("\n✓ Search space is sufficient - MCTS can discover valid circuits!")
        print("  If MCTS isn't finding circuits, the issue is search strategy,")
        print("  not action space limitations.")
    elif result1 or result2:
        print("\n⚠ Some circuits reachable, but search space may be limited.")
    else:
        print("\n❌ Search space is insufficient - valid circuits are NOT reachable!")
        print("  MCTS cannot discover valid circuits with current constraints.")
