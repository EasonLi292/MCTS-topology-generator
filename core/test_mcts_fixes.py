#!/usr/bin/env python3
"""
Quick test to validate MCTS fixes without running full SPICE simulations.
"""

from topology_game_board import Breadboard
from MCTS import MCTS, MCTSNode

def test_basic_mcts():
    """Test that MCTS can initialize and run basic operations."""
    print("Testing MCTS initialization...")
    initial_board = Breadboard()
    mcts = MCTS(initial_board)

    assert mcts.root is not None, "Root node should be created"
    assert mcts.root.state == initial_board, "Root should contain initial state"
    print("✓ MCTS initialization successful")

    print("\nTesting node expansion...")
    # Test that we can expand a node
    root = mcts.root
    assert len(root.untried_actions) > 0, "Root should have untried actions"

    first_child = root.expand()
    assert first_child.parent == root, "Child should reference parent"
    assert first_child.action_from_parent is not None, "Child should store action"
    assert first_child in root.children, "Child should be in parent's children list"
    print(f"✓ Expanded node with action: {first_child.action_from_parent}")

    print("\nTesting reward backpropagation...")
    # Test reward update
    test_reward = 5.0
    first_child.update(test_reward)
    assert first_child.visits == 1, "Child should have 1 visit"
    assert first_child.wins == test_reward, "Child should have correct reward"
    print(f"✓ Reward backpropagation works: {first_child.wins}/{first_child.visits}")

    print("\nTesting UCT selection...")
    # Create multiple children and test selection
    for _ in range(3):
        if root.untried_actions:
            child = root.expand()
            child.update(1.0)  # Give each child some stats

    root.update(10.0)  # Give parent visits for UCT calculation
    selected = root.select_child()
    assert selected in root.children, "Selected child should be in children list"
    print(f"✓ UCT selection successful, selected child with {selected.visits} visits")

    print("\nTesting get_best_solution...")
    path, reward = mcts.get_best_solution()
    assert isinstance(path, list), "Path should be a list"
    assert isinstance(reward, float), "Reward should be a float"
    print(f"✓ get_best_solution returns path of length {len(path)} with reward {reward}")

    print("\n" + "="*60)
    print("All basic MCTS tests passed! ✓")
    print("="*60)

if __name__ == "__main__":
    test_basic_mcts()
