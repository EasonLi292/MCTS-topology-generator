#!/usr/bin/env python3
"""
Main entry point for MCTS topology generator.

This script runs the Monte Carlo Tree Search algorithm to generate
circuit topologies and outputs the best found circuits as SPICE netlists.

Refactored to follow SOLID principles with focused, well-documented functions.

Usage:
    python3 main.py [--iterations N] [--exploration C] [--verbose]
"""

import argparse
from typing import Tuple
from topology_game_board import Breadboard
from MCTS import MCTS


def main():
    """Main entry point for the MCTS circuit generator."""
    # Parse command-line arguments
    args = _parse_arguments()

    # Prepare initial board (customizable dimensions)
    initial_board = Breadboard(rows=args.board_rows)

    # Display header
    _print_header(args)

    # Initialize and run MCTS
    mcts = _initialize_mcts(initial_board)
    _run_mcts_search(mcts, args.iterations)

    # Get and display results
    path, reward = mcts.get_best_solution()
    _display_search_results(path, reward)

    # Reconstruct and save final circuit
    final_board = _reconstruct_circuit(initial_board.clone(), path, args.verbose)
    _save_final_circuit(final_board)

    # Save best candidate circuit
    _save_best_candidate(mcts)

    # Display completion message
    _print_completion()


def _parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description='MCTS Circuit Topology Generator')
    parser.add_argument('--iterations', type=int, default=10000,
                        help='Number of MCTS iterations to run (default: 10000)')
    parser.add_argument('--exploration', type=float, default=1.0,
                        help='UCT exploration constant (default: 1.0)')
    parser.add_argument('--board-rows', type=int, default=15,
                        help='Number of rows available on the breadboard (default: 15)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print verbose output')
    return parser.parse_args()


def _print_header(args: argparse.Namespace):
    """
    Prints the program header with configuration.

    Args:
        args: Parsed command-line arguments
    """
    print("="*70)
    print("MCTS CIRCUIT TOPOLOGY GENERATOR")
    print("="*70)
    print(f"Iterations: {args.iterations}")
    print(f"Exploration constant: {args.exploration}")
    print(f"Breadboard rows: {args.board_rows}")
    print("="*70)


def _initialize_mcts(initial_board: Breadboard) -> MCTS:
    """
    Initializes the MCTS algorithm with a fresh breadboard.

    Args:
        initial_board: Starting breadboard state

    Returns:
        Initialized MCTS instance
    """
    return MCTS(initial_board)


def _run_mcts_search(mcts: MCTS, iterations: int):
    """
    Runs the MCTS search algorithm.

    Args:
        mcts: MCTS instance
        iterations: Number of iterations to run
    """
    print("\nStarting MCTS search...")
    mcts.search(iterations=iterations)


def _display_search_results(path: list, reward: float):
    """
    Displays the search results summary.

    Args:
        path: List of actions in the best path
        reward: Average reward for the best path
    """
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Best path length: {len(path)} actions")
    print(f"Average reward: {reward:.4f}")


def _reconstruct_circuit(initial_board: Breadboard, path: list, verbose: bool) -> Breadboard:
    """
    Reconstructs the final circuit by applying actions from the path.

    Args:
        initial_board: Initial breadboard state
        path: List of actions to apply
        verbose: Whether to print each action

    Returns:
        Final breadboard state
    """
    final_board = initial_board

    for i, action in enumerate(path, 1):
        try:
            final_board = final_board.apply_action(action)
            if verbose:
                print(f"  {i}. {action}")
        except Exception as e:
            print(f"Error applying action {i}: {e}")
            break

    return final_board


def _save_final_circuit(board: Breadboard):
    """
    Displays and saves the final circuit netlist.

    Args:
        board: Final breadboard state
    """
    print(f"\nFinal circuit:")
    print(f"  Components: {len(board.placed_components)}")
    print(f"  Complete: {board.is_complete_and_valid()}")

    if board.is_complete_and_valid():
        netlist = board.to_netlist()
        if netlist:
            _print_netlist("Generated SPICE netlist", netlist)
            _write_netlist_to_file(netlist, "generated_circuit.sp")


def _save_best_candidate(mcts: MCTS):
    """
    Displays and saves the best candidate circuit found during search.

    Args:
        mcts: MCTS instance with search results
    """
    print("\n" + "="*70)
    print("BEST CANDIDATE CIRCUIT (highest reward during search)")
    print("="*70)

    if not mcts.best_candidate_state:
        print("  No candidate circuit found")
        return

    # Display candidate info
    _display_candidate_info(mcts.best_candidate_state, mcts.best_candidate_reward)

    # Save candidate netlist if valid
    if mcts.best_candidate_state.is_complete_and_valid():
        netlist = mcts.best_candidate_state.to_netlist()
        if netlist:
            _write_netlist_to_file(netlist, "best_candidate_circuit.sp")
            _print_netlist("Best candidate SPICE netlist", netlist)


def _display_candidate_info(board: Breadboard, reward: float):
    """
    Displays information about the best candidate circuit.

    Args:
        board: Candidate breadboard state
        reward: Reward score for this candidate
    """
    comp_count = len([c for c in board.placed_components
                     if c.type not in ['wire', 'vin', 'vout']])
    print(f"  Components: {comp_count}")
    print(f"  Complete: {board.is_complete_and_valid()}")
    print(f"  Reward: {reward:.4f}")


def _print_netlist(title: str, netlist: str):
    """
    Prints a netlist with a formatted header.

    Args:
        title: Title to display above the netlist
        netlist: SPICE netlist string
    """
    print(f"\n{title}:")
    print("-" * 70)
    print(netlist)
    print("-" * 70)


def _write_netlist_to_file(netlist: str, filename: str):
    """
    Writes a netlist to a file.

    Args:
        netlist: SPICE netlist string
        filename: Output file path
    """
    with open(filename, 'w') as f:
        f.write(netlist)
    print(f"\nNetlist saved to: {filename}")


def _print_completion():
    """Prints the completion message."""
    print("\n" + "="*70)
    print("Search complete!")
    print("="*70)


if __name__ == "__main__":
    main()
