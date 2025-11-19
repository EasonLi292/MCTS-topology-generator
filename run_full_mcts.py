#!/usr/bin/env python3
"""
Run full MCTS search with 50,000 iterations starting from empty board.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard
from MCTS import MCTS


def main():
    print("="*70)
    print("MCTS Full Search: 50,000 Iterations from Empty Board")
    print("="*70)

    # Start with empty board
    initial_board = Breadboard(rows=15)

    print(f"\nInitial board state:")
    print(f"  Components placed: {len(initial_board.placed_components)}")
    print(f"  Circuit complete: {initial_board.is_complete_and_valid()}")

    # Run MCTS
    print(f"\n{'='*70}")
    print(f"Starting MCTS search (50,000 iterations)...")
    print(f"{'='*70}")

    mcts = MCTS(initial_board)

    max_iterations = 50000
    check_interval = 1000

    for i in range(1, max_iterations + 1):
        mcts.search(iterations=1)

        # Check progress every 1000 iterations
        if i % check_interval == 0:
            path, reward = mcts.get_best_solution()
            print(f"\nIteration {i}:")
            print(f"  Best path length: {len(path)} actions")
            print(f"  Average reward: {reward:.4f}")

            # Try to reconstruct and check if complete
            final_board = initial_board
            is_valid = False
            for action in path:
                try:
                    final_board = final_board.apply_action(action)
                except Exception as e:
                    break

            if final_board.is_complete_and_valid():
                is_valid = True
                print(f"  Status: COMPLETE CIRCUIT FOUND!")
            else:
                print(f"  Status: Searching... ({len(final_board.placed_components)} components)")

            if is_valid and i >= check_interval:
                print(f"\n{'='*70}")
                print(f"✓✓✓ SUCCESS! Circuit completed at iteration {i} ✓✓✓")
                print(f"{'='*70}")
                print(f"\nWinning action sequence:")
                for j, action in enumerate(path, 1):
                    print(f"  {j}. {action}")

                print(f"\nFinal board statistics:")
                print(f"  Components placed: {len(final_board.placed_components)}")
                print(f"  Circuit complete: {final_board.is_complete_and_valid()}")

                # Generate netlist
                netlist = final_board.to_netlist()
                if netlist:
                    print(f"\n{'='*70}")
                    print("Generated Netlist:")
                    print(f"{'='*70}")
                    print(netlist)

                # Save to file
                output_path = 'outputs/mcts_full_search_result.txt'
                with open(output_path, 'w') as f:
                    f.write(f"Success at iteration {i}\n")
                    f.write(f"Action sequence ({len(path)} actions):\n")
                    for j, action in enumerate(path, 1):
                        f.write(f"{j}. {action}\n")
                    f.write(f"\nNetlist:\n{netlist}\n")

                print(f"\n{'='*70}")
                print(f"Results saved to {output_path}")
                print(f"{'='*70}")

                return True

    # If we get here, we didn't complete in 50000 iterations
    print(f"\n{'='*70}")
    print(f"Reached {max_iterations} iterations")
    print(f"{'='*70}")

    path, reward = mcts.get_best_solution()
    print(f"\nBest solution found:")
    print(f"  Path length: {len(path)} actions")
    print(f"  Average reward: {reward:.4f}")
    print(f"\nAction sequence:")
    for j, action in enumerate(path, 1):
        print(f"  {j}. {action}")

    # Reconstruct final state
    final_board = initial_board
    for action in path:
        try:
            final_board = final_board.apply_action(action)
        except Exception:
            break

    print(f"\nFinal board state:")
    print(f"  Components placed: {len(final_board.placed_components)}")
    print(f"  Circuit complete: {final_board.is_complete_and_valid()}")

    # Save partial results
    output_path = 'outputs/mcts_full_search_partial.txt'
    with open(output_path, 'w') as f:
        f.write(f"Completed {max_iterations} iterations without finding complete circuit\n")
        f.write(f"Best path length: {len(path)}\n")
        f.write(f"Best reward: {reward:.4f}\n")
        f.write(f"Action sequence ({len(path)} actions):\n")
        for j, action in enumerate(path, 1):
            f.write(f"{j}. {action}\n")

    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
