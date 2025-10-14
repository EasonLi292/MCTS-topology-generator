#!/usr/bin/env python3
"""
Main entry point for MCTS topology generator.

Usage:
    python3 main.py [--iterations N]
"""

import argparse
from topology_game_board import Breadboard
from MCTS import MCTS


def main():
    parser = argparse.ArgumentParser(description='MCTS Circuit Topology Generator')
    parser.add_argument('--iterations', type=int, default=10000,
                        help='Number of MCTS iterations to run (default: 10000)')
    parser.add_argument('--exploration', type=float, default=1.41,
                        help='UCT exploration constant (default: 1.41)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print verbose output')

    args = parser.parse_args()

    print("="*70)
    print("MCTS CIRCUIT TOPOLOGY GENERATOR")
    print("="*70)
    print(f"Iterations: {args.iterations}")
    print(f"Exploration constant: {args.exploration}")
    print("="*70)

    # Initialize MCTS
    initial_board = Breadboard()
    mcts = MCTS(initial_board)

    # Run search
    print("\nStarting MCTS search...")
    mcts.search(iterations=args.iterations)

    # Get best solution
    path, reward = mcts.get_best_solution()

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Best path length: {len(path)} actions")
    print(f"Average reward: {reward:.4f}")

    # Reconstruct final circuit
    final_board = initial_board
    for i, action in enumerate(path, 1):
        try:
            final_board = final_board.apply_action(action)
            if args.verbose:
                print(f"  {i}. {action}")
        except Exception as e:
            print(f"Error applying action {i}: {e}")
            break

    # Show final circuit
    print(f"\nFinal circuit:")
    print(f"  Components: {len(final_board.placed_components)}")
    print(f"  Complete: {final_board.is_complete_and_valid()}")

    if final_board.is_complete_and_valid():
        netlist = final_board.to_netlist()
        if netlist:
            print("\nGenerated SPICE netlist:")
            print("-" * 70)
            print(netlist)
            print("-" * 70)

            # Optionally save to file
            output_file = "generated_circuit.sp"
            with open(output_file, 'w') as f:
                f.write(netlist)
            print(f"\nNetlist saved to: {output_file}")

    print("\n" + "="*70)
    print("Search complete!")
    print("="*70)


if __name__ == "__main__":
    main()
