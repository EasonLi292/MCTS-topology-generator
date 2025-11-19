#!/usr/bin/env python3
"""
Test the new heuristic scaling to verify it works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard
from MCTS import MCTS, HEURISTIC_SCALE_FACTOR, MAX_RAW_HEURISTIC, INCOMPLETE_REWARD_CAP


def test_heuristic_scaling():
    print("="*70)
    print("Testing Heuristic Scaling")
    print("="*70)

    print(f"\nScaling Configuration:")
    print(f"  MAX_RAW_HEURISTIC: {MAX_RAW_HEURISTIC}")
    print(f"  INCOMPLETE_REWARD_CAP: {INCOMPLETE_REWARD_CAP}")
    print(f"  HEURISTIC_SCALE_FACTOR: {HEURISTIC_SCALE_FACTOR:.6f}")
    print(f"  Expected max scaled reward: {MAX_RAW_HEURISTIC * HEURISTIC_SCALE_FACTOR:.2f}")

    # Test with different board states
    print(f"\n{'='*70}")
    print("Testing different circuit states:")
    print(f"{'='*70}")

    # Empty board
    board = Breadboard(rows=15)
    mcts = MCTS(board)
    metrics = mcts._calculate_circuit_metrics(board)
    heuristic = mcts._calculate_heuristic_reward(metrics)
    print(f"\n1. Empty board:")
    print(f"   Heuristic reward: {heuristic:.4f}")
    print(f"   (Should be small/negative)")

    # Add a resistor
    board = Breadboard(rows=15)
    board = board.apply_action(("resistor", board.WORK_START_ROW + 2))
    mcts = MCTS(board)
    metrics = mcts._calculate_circuit_metrics(board)
    heuristic = mcts._calculate_heuristic_reward(metrics)
    print(f"\n2. One resistor:")
    print(f"   Components: {metrics['num_components']}")
    print(f"   Heuristic reward: {heuristic:.4f}")

    # Add multiple components with connections
    board = Breadboard(rows=15)
    mid = board.WORK_START_ROW + 3

    board = board.apply_action(("resistor", mid))
    board = board.apply_action(("wire", board.VIN_ROW, mid))
    board = board.apply_action(("resistor", mid + 2))
    board = board.apply_action(("wire", mid + 1, mid + 2))
    board = board.apply_action(("wire", mid + 3, board.VDD_ROW))

    mcts = MCTS(board)
    metrics = mcts._calculate_circuit_metrics(board)
    heuristic = mcts._calculate_heuristic_reward(metrics)
    conn = metrics.get('connectivity', {})

    print(f"\n3. Multiple components with some connections:")
    print(f"   Components: {metrics['num_components']}")
    print(f"   Unique types: {metrics['unique_types']}")
    print(f"   VIN-VOUT connected: {metrics['vin_vout_connected']}")
    print(f"   Touches VDD: {conn.get('touches_vdd', False)}")
    print(f"   Touches VSS: {conn.get('touches_vss', False)}")
    print(f"   Reachable VOUT: {conn.get('reachable_vout', False)}")
    print(f"   Heuristic reward: {heuristic:.4f}")
    print(f"   (Should be larger but still ≤ {INCOMPLETE_REWARD_CAP})")

    # Build near-complete circuit (from test_almost_complete)
    board = Breadboard(rows=15)
    mid = board.WORK_START_ROW + 3

    board = board.apply_action(("resistor", mid))
    board = board.apply_action(("wire", board.VIN_ROW, mid))

    g_row = mid + 2
    board = board.apply_action(("resistor", g_row))
    board = board.apply_action(("wire", g_row, mid + 1))
    board = board.apply_action(("wire", g_row + 1, board.VSS_ROW))

    s_row = g_row + 2
    board = board.apply_action(("resistor", s_row))
    board = board.apply_action(("wire", s_row, mid + 1))
    board = board.apply_action(("wire", s_row + 1, board.VDD_ROW))

    mcts = MCTS(board)
    metrics = mcts._calculate_circuit_metrics(board)
    heuristic = mcts._calculate_heuristic_reward(metrics)
    conn = metrics.get('connectivity', {})

    print(f"\n4. Almost-complete circuit (1 wire away):")
    print(f"   Components: {metrics['num_components']}")
    print(f"   Unique types: {metrics['unique_types']}")
    print(f"   VIN-VOUT connected: {metrics['vin_vout_connected']}")
    print(f"   Touches VDD: {conn.get('touches_vdd', False)}")
    print(f"   Touches VSS: {conn.get('touches_vss', False)}")
    print(f"   Reachable VOUT: {conn.get('reachable_vout', False)}")
    print(f"   All components reachable: {conn.get('all_components_reachable', False)}")
    print(f"   Heuristic reward: {heuristic:.4f}")
    print(f"   (Should be high, close to {INCOMPLETE_REWARD_CAP})")

    print(f"\n{'='*70}")
    print("Verification:")
    print(f"{'='*70}")
    print(f"All heuristic values should be ≤ {INCOMPLETE_REWARD_CAP}")
    print(f"Different circuit qualities should have different rewards")
    print(f"More complete circuits should have higher rewards")
    print(f"\n✓ Heuristic scaling test complete!")


if __name__ == "__main__":
    test_heuristic_scaling()
