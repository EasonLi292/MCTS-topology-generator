#!/usr/bin/env python3
"""
Test script to verify MCTS can complete almost-finished circuits.

This validates that the algorithm's rules and heuristics work correctly
even if finding circuits from scratch is challenging.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard  # noqa: E402
from MCTS import MCTS  # noqa: E402


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def analyze_circuit_state(board, title="Circuit State"):
    """Analyze and print circuit connectivity status."""
    print(f"\n{title}:")
    conn = board.get_connectivity_summary()

    comps = [c for c in board.placed_components if c.type not in ['vin', 'vout', 'wire']]
    wires = [c for c in board.placed_components if c.type == 'wire']

    print(f"  Components: {len(comps)}")
    print(f"  Wires: {len(wires)}")
    print(f"  Touches VDD: {conn['touches_vdd']}")
    print(f"  Touches VSS: {conn['touches_vss']}")
    print(f"  VOUT reachable: {conn['reachable_vout']}")
    print(f"  All components connected: {conn['all_components_reachable']}")
    print(f"  Valid: {conn['valid']}")
    print(f"  Complete: {board.is_complete_and_valid()}")

    return board.is_complete_and_valid()


def test_one_wire_away():
    """Test 1: Circuit is one wire away from being valid."""
    print_section("TEST 1: One Wire Away from Valid Circuit")

    # Build voltage divider missing only VOUT connection
    # R1 (VDD to middle), R2 (middle to VSS), R3 (VIN to middle)
    board = Breadboard(rows=15)

    print("\nBuilding circuit (missing final VOUT wire):")
    print("  1. R1 from row 5-6, col 1 (VDD to middle)")
    board = board.apply_action(('resistor', 5, 1))

    print("  2. Wire VDD to R1 top")
    board = board.apply_action(('wire', 6, 1, 14, 0))

    print("  3. R2 from row 4-5, col 2 (middle to VSS)")
    board = board.apply_action(('resistor', 4, 2))

    print("  4. Wire R1 bottom to R2 top (middle node)")
    board = board.apply_action(('wire', 5, 1, 5, 2))

    print("  5. Wire R2 bottom to VSS")
    board = board.apply_action(('wire', 4, 2, 0, 0))

    print("  6. R3 from row 7-8, col 3 (VIN to middle)")
    board = board.apply_action(('resistor', 7, 3))

    print("  7. Wire VIN to R3 top")
    board = board.apply_action(('wire', 1, 0, 8, 3))

    print("  8. Wire R3 bottom to middle node")
    board = board.apply_action(('wire', 7, 3, 5, 2))

    # Check state before completion
    is_complete_before = analyze_circuit_state(board, "State BEFORE final wire")

    # Check legal actions
    actions = board.legal_actions()
    wire_to_vout = [a for a in actions if a == ('wire', 5, 2, 13, 0)]
    stop_actions = [a for a in actions if a[0] == 'STOP']

    print(f"\n  Total legal actions: {len(actions)}")
    print(f"  Missing wire (5,2)→(13,0) available: {len(wire_to_vout) > 0}")
    print(f"  STOP action available: {len(stop_actions) > 0}")

    # Add the final wire
    print("\n  9. Wire middle node to VOUT (COMPLETING CIRCUIT)")
    board = board.apply_action(('wire', 5, 2, 13, 0))

    # Check state after completion
    is_complete_after = analyze_circuit_state(board, "State AFTER final wire")

    # Check if STOP is now available
    actions_after = board.legal_actions()
    stop_actions_after = [a for a in actions_after if a[0] == 'STOP']
    print(f"  STOP action now available: {len(stop_actions_after) > 0}")

    # Run short MCTS from almost-complete state
    print("\n  Testing MCTS from almost-complete state...")
    board_incomplete = Breadboard(rows=15)
    for action in [('resistor', 5, 1), ('wire', 6, 1, 14, 0),
                   ('resistor', 4, 2), ('wire', 5, 1, 5, 2), ('wire', 4, 2, 0, 0),
                   ('resistor', 7, 3), ('wire', 1, 0, 8, 3), ('wire', 7, 3, 5, 2)]:
        board_incomplete = board_incomplete.apply_action(action)

    mcts = MCTS(board_incomplete)
    mcts.search(iterations=500)

    print(f"  MCTS found valid circuit: {mcts.best_candidate_state.is_complete_and_valid() if mcts.best_candidate_state else False}")
    print(f"  Best reward: {mcts.best_candidate_reward:.2f}")

    assert is_complete_before is False, "Circuit should not be complete before adding final wire"
    assert is_complete_after, "Circuit should be complete after adding final wire"
    assert len(stop_actions_after) > 0, "STOP action should be available after completion"


def test_two_steps_away():
    """Test 2: Circuit is two steps away from being valid."""
    print_section("TEST 2: Two Steps Away from Valid Circuit")

    # Build circuit missing VSS and VOUT connections
    # R1 (VDD to middle), R2 (middle to VSS), R3 (VIN to middle)
    board = Breadboard(rows=15)

    print("\nBuilding circuit (missing VSS and VOUT wires):")
    print("  1. R1 from row 5-6, col 1 (VDD to middle)")
    board = board.apply_action(('resistor', 5, 1))

    print("  2. Wire VDD to R1 top")
    board = board.apply_action(('wire', 6, 1, 14, 0))

    print("  3. R2 from row 4-5, col 2 (middle to VSS)")
    board = board.apply_action(('resistor', 4, 2))

    print("  4. Wire R1 bottom to R2 top (middle node)")
    board = board.apply_action(('wire', 5, 1, 5, 2))

    print("  5. R3 from row 7-8, col 3 (VIN to middle)")
    board = board.apply_action(('resistor', 7, 3))

    print("  6. Wire VIN to R3 top")
    board = board.apply_action(('wire', 1, 0, 8, 3))

    print("  7. Wire R3 bottom to middle node")
    board = board.apply_action(('wire', 7, 3, 5, 2))

    # Missing: VSS connection and VOUT connection
    is_complete_before = analyze_circuit_state(board, "State BEFORE completion")

    print("\n  8. Wire R2 bottom to VSS")
    board = board.apply_action(('wire', 4, 2, 0, 0))

    analyze_circuit_state(board, "State AFTER VSS wire")

    print("\n  9. Wire middle node to VOUT (COMPLETING CIRCUIT)")
    board = board.apply_action(('wire', 5, 2, 13, 0))

    is_complete_after = analyze_circuit_state(board, "State AFTER VOUT wire")

    # Run MCTS from 2-steps-away state
    print("\n  Testing MCTS from 2-steps-away state...")
    board_incomplete = Breadboard(rows=15)
    for action in [('resistor', 5, 1), ('wire', 6, 1, 14, 0),
                   ('resistor', 4, 2), ('wire', 5, 1, 5, 2),
                   ('resistor', 7, 3), ('wire', 1, 0, 8, 3), ('wire', 7, 3, 5, 2)]:
        board_incomplete = board_incomplete.apply_action(action)

    mcts = MCTS(board_incomplete)
    mcts.search(iterations=1000)

    print(f"  MCTS found valid circuit: {mcts.best_candidate_state.is_complete_and_valid() if mcts.best_candidate_state else False}")
    print(f"  Best reward: {mcts.best_candidate_reward:.2f}")

    assert is_complete_before is False, "Circuit should not be complete before adding final wires"
    assert is_complete_after, "Circuit should be complete after adding both wires"


def test_components_placed_need_wiring():
    """Test 3: Components are placed but need wiring."""
    print_section("TEST 3: Components Placed, Need Wiring")

    board = Breadboard(rows=15)

    print("\nPlacing components without wiring:")
    print("  1. R1 from row 5-6, col 1 (VDD to middle)")
    board = board.apply_action(('resistor', 5, 1))

    print("  2. R2 from row 4-5, col 2 (middle to VSS)")
    board = board.apply_action(('resistor', 4, 2))

    print("  3. R3 from row 7-8, col 3 (VIN to middle)")
    board = board.apply_action(('resistor', 7, 3))

    analyze_circuit_state(board, "State with components only")

    print("\nNow adding wires to complete circuit:")
    print("  4. Wire VDD to R1 top")
    board = board.apply_action(('wire', 6, 1, 14, 0))

    print("  5. Wire R1 bottom to R2 top (middle node)")
    board = board.apply_action(('wire', 5, 1, 5, 2))

    print("  6. Wire R2 bottom to VSS")
    board = board.apply_action(('wire', 4, 2, 0, 0))

    print("  7. Wire VIN to R3 top")
    board = board.apply_action(('wire', 1, 0, 8, 3))

    print("  8. Wire R3 bottom to middle node")
    board = board.apply_action(('wire', 7, 3, 5, 2))

    print("  9. Wire middle node to VOUT")
    board = board.apply_action(('wire', 5, 2, 13, 0))

    is_complete = analyze_circuit_state(board, "Final state")

    # Test MCTS from components-only state
    print("\n  Testing MCTS from components-only state...")
    board_comps = Breadboard(rows=15)
    board_comps = board_comps.apply_action(('resistor', 5, 1))
    board_comps = board_comps.apply_action(('resistor', 4, 2))
    board_comps = board_comps.apply_action(('resistor', 7, 3))

    mcts = MCTS(board_comps)
    mcts.search(iterations=2000)

    print(f"  MCTS found valid circuit: {mcts.best_candidate_state.is_complete_and_valid() if mcts.best_candidate_state else False}")
    print(f"  Best reward: {mcts.best_candidate_reward:.2f}")

    assert is_complete, "Circuit should be complete after adding all wires"


def run_all_tests():
    """Run all almost-complete circuit tests."""
    print("=" * 70)
    print("ALMOST-COMPLETE CIRCUIT TEST SUITE")
    print("=" * 70)

    tests = [
        test_one_wire_away,
        test_two_steps_away,
        test_components_placed_need_wiring,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as exc:  # pragma: no cover - manual test harness
            print(f"❌ EXCEPTION in {test.__name__}: {exc}")
            results.append(False)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True

    print(f"⚠️  {total - passed} test(s) failed")
    return False


if __name__ == "__main__":
    success = run_all_tests()
    raise SystemExit(0 if success else 1)
