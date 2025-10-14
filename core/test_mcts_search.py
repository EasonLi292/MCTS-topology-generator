#!/usr/bin/env python3
"""
Test a short MCTS search to validate the complete workflow.
"""

from topology_game_board import Breadboard
from MCTS import MCTS

def test_short_search():
    """Run a short MCTS search to validate the workflow."""
    print("="*60)
    print("Testing MCTS Search (100 iterations)")
    print("="*60)

    initial_board = Breadboard()
    mcts = MCTS(initial_board)

    # Run a short search
    print("\nStarting MCTS search...")
    mcts.search(iterations=100)

    # Get the best solution found
    print("\nRetrieving best solution...")
    path, reward = mcts.get_best_solution()

    print(f"\n{'='*60}")
    print(f"Search Results:")
    print(f"{'='*60}")
    print(f"Best path length: {len(path)} actions")
    print(f"Average reward: {reward:.4f}")
    print(f"\nAction sequence:")
    for i, action in enumerate(path, 1):
        print(f"  {i}. {action}")

    # Try to reconstruct the final board state
    print(f"\n{'='*60}")
    print("Reconstructing final circuit...")
    print(f"{'='*60}")

    final_board = initial_board
    for action in path:
        try:
            final_board = final_board.apply_action(action)
        except Exception as e:
            print(f"Error applying action {action}: {e}")
            break

    print(f"Final board statistics:")
    print(f"  Components placed: {len(final_board.placed_components)}")
    print(f"  Circuit complete: {final_board.is_complete_and_valid()}")

    if final_board.is_complete_and_valid():
        print(f"\n✓ Found a complete and valid circuit!")
        netlist = final_board.to_netlist()
        if netlist:
            print(f"\nGenerated netlist preview:")
            lines = netlist.split('\n')
            for line in lines[:20]:  # Show first 20 lines
                print(f"  {line}")
            if len(lines) > 20:
                print(f"  ... ({len(lines) - 20} more lines)")
    else:
        print(f"\n✓ Search progressed but did not complete a circuit (expected for short run)")

    print(f"\n{'='*60}")
    print("Test completed successfully!")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_short_search()
