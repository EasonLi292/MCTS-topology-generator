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
from datetime import datetime
from pathlib import Path
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

    # Initialize MCTS
    mcts = _initialize_mcts(initial_board)

    # Run until valid circuit is found (if --until-valid flag is set)
    if args.until_valid:
        total_iterations = _run_until_valid_circuit(mcts, args.checkpoint_interval)
    else:
        _run_mcts_search(mcts, args.iterations)
        total_iterations = args.iterations

    # Get and display results
    path, reward = mcts.get_best_solution()
    _display_search_results(path, reward)

    # Reconstruct and save final circuit
    final_board = _reconstruct_circuit(initial_board.clone(), path, args.verbose)
    _save_final_circuit(final_board)

    # Save best candidate circuit
    _save_best_candidate(mcts, total_iterations)

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
    parser.add_argument('--until-valid', action='store_true',
                        help='Run continuously until a valid circuit is found')
    parser.add_argument('--checkpoint-interval', type=int, default=20000,
                        help='Report progress every N iterations when using --until-valid (default: 20000)')
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

    if args.until_valid:
        print(f"Mode: Run until valid circuit found")
        print(f"Checkpoint interval: {args.checkpoint_interval:,} iterations")
    else:
        print(f"Iterations: {args.iterations:,}")

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


def _run_until_valid_circuit(mcts: MCTS, checkpoint_interval: int) -> int:
    """
    Runs MCTS continuously until a valid circuit is found.

    Reports progress every checkpoint_interval iterations.
    Does not reset the MCTS tree between checkpoints - continues building on previous exploration.

    Args:
        mcts: MCTS instance
        checkpoint_interval: Number of iterations between progress reports

    Returns:
        Total number of iterations run
    """
    print("\nStarting MCTS search (running until valid circuit found)...")
    print(f"Progress checkpoints every {checkpoint_interval:,} iterations\n")

    total_iterations = 0
    checkpoint_count = 0

    while True:
        checkpoint_count += 1

        # Run another batch of iterations (continues from existing tree state)
        print(f"{'='*70}")
        print(f"CHECKPOINT {checkpoint_count}: Running iterations {total_iterations:,} to {total_iterations + checkpoint_interval:,}")
        print(f"{'='*70}")

        mcts.search(iterations=checkpoint_interval)
        total_iterations += checkpoint_interval

        # Check if we found a valid circuit
        if mcts.best_candidate_state and mcts.best_candidate_state.is_complete_and_valid():
            print(f"\n{'='*70}")
            print(f"✓ VALID CIRCUIT FOUND!")
            print(f"{'='*70}")
            print(f"Total iterations: {total_iterations:,}")
            print(f"Best candidate reward: {mcts.best_candidate_reward:.2f}")

            # Get SPICE stats
            spice_success = mcts.stats.spice_success_count if mcts.stats else 0
            spice_fail = mcts.stats.spice_fail_count if mcts.stats else 0
            total_spice = spice_success + spice_fail

            if total_spice > 0:
                success_rate = (spice_success / total_spice) * 100
                print(f"SPICE success rate: {success_rate:.2f}% ({spice_success}/{total_spice})")

            break
        else:
            # Report progress
            print(f"\nCheckpoint {checkpoint_count} complete:")
            print(f"  Total iterations so far: {total_iterations:,}")
            print(f"  Best candidate reward: {mcts.best_candidate_reward:.2f}")
            print(f"  Best candidate valid: {mcts.best_candidate_state.is_complete_and_valid() if mcts.best_candidate_state else False}")

            # Get SPICE stats
            spice_success = mcts.stats.spice_success_count if mcts.stats else 0
            spice_fail = mcts.stats.spice_fail_count if mcts.stats else 0
            total_spice = spice_success + spice_fail

            if total_spice > 0:
                success_rate = (spice_success / total_spice) * 100
                print(f"  SPICE success rate: {success_rate:.2f}% ({spice_success}/{total_spice})")
            else:
                print(f"  SPICE runs: 0 (no complete circuits attempted yet)")

            print(f"\nContinuing search...")
            print()

    return total_iterations


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
    Displays and saves the final circuit netlist and visualization.

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

            # Generate and save visualization
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            reward = board.get_reward()
            visualization = _generate_circuit_visualization(board, reward)
            _write_visualization_to_file(visualization, f"final_circuit_{timestamp}.txt")


def _save_best_candidate(mcts: MCTS, iterations: int):
    """
    Displays and saves the best candidate circuit found during search.

    Args:
        mcts: MCTS instance with search results
        iterations: Number of iterations that were run
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

            # Generate and save visualization with MCTS stats
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # Get SPICE stats from MCTS stats object
            spice_success = mcts.stats.spice_success_count if mcts.stats else 0
            spice_fail = mcts.stats.spice_fail_count if mcts.stats else 0
            visualization = _generate_circuit_visualization(
                mcts.best_candidate_state,
                mcts.best_candidate_reward,
                iterations=iterations,
                spice_success=spice_success,
                spice_fail=spice_fail
            )
            _write_visualization_to_file(visualization, f"best_circuit_{timestamp}.txt")


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


def _generate_circuit_visualization(board: Breadboard, reward: float,
                                     iterations: int = 0, spice_success: int = 0,
                                     spice_fail: int = 0) -> str:
    """
    Generates a comprehensive text visualization of the circuit.

    Args:
        board: Breadboard state to visualize
        reward: Reward score for this circuit
        iterations: Total MCTS iterations run
        spice_success: Number of successful SPICE validations
        spice_fail: Number of failed SPICE validations

    Returns:
        Formatted visualization string
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("MCTS CIRCUIT VISUALIZATION")
    lines.append("=" * 80)
    lines.append("")

    # Performance metrics
    lines.append("PERFORMANCE METRICS:")
    lines.append(f"  Reward: {reward:.2f}")
    lines.append(f"  Valid: {board.is_complete_and_valid()}")
    if iterations > 0:
        lines.append(f"  Iterations: {iterations}")
        lines.append(f"  SPICE Successes: {spice_success}")
        lines.append(f"  SPICE Failures: {spice_fail}")
        if iterations > 0:
            success_rate = (spice_success / iterations) * 100
            lines.append(f"  Success Rate: {success_rate:.2f}%")
    lines.append("")

    # Grid visualization
    lines.append("=" * 80)
    lines.append("CIRCUIT VISUALIZATION")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Grid Layout (rows x cols):")

    # Create grid visualization
    grid_vis = [[' . ' for _ in range(board.COLUMNS)] for _ in range(board.ROWS)]

    # Mark special rows
    for c in range(board.COLUMNS):
        grid_vis[board.VSS_ROW][c] = 'VSS'
        grid_vis[board.VDD_ROW][c] = 'VDD'
        grid_vis[board.VIN_ROW][c] = 'VIN'
        grid_vis[board.VOUT_ROW][c] = 'OUT'

    # Mark components
    comp_symbols = {
        'resistor': 'R',
        'capacitor': 'C',
        'inductor': 'L',
        'diode': 'D',
        'nmos3': 'M',
        'pmos3': 'P',
        'npn': 'Q',
        'pnp': 'Q'
    }

    comp_counter = {}
    for comp in board.placed_components:
        if comp.type in ['vin', 'vout', 'wire']:
            continue

        symbol = comp_symbols.get(comp.type, 'X')
        if symbol not in comp_counter:
            comp_counter[symbol] = 0
        comp_counter[symbol] += 1
        comp_id = f'{symbol}{comp_counter[symbol]}'

        for i, r in enumerate(comp.pins):
            # In row-based model, there's only one column (index 0)
            grid_vis[r][0] = f'{comp_id}{i+1}'

    # Print grid header
    header = "      "
    for c in range(board.COLUMNS):
        header += f"  {c} "
    lines.append(header)
    lines.append("   " + "-" * (board.COLUMNS * 4 + 1))

    # Print grid rows
    for r in range(board.ROWS):
        row_str = f'{r:2} |'
        for c in range(board.COLUMNS):
            row_str += f'{grid_vis[r][c]:>3} '
        lines.append(row_str)

    lines.append("")
    lines.append("Legend:")
    lines.append("  VSS = Ground rail (row 0)")
    lines.append(f"  VDD = Power rail (row {board.VDD_ROW})")
    lines.append(f"  VIN = Input signal (row {board.VIN_ROW})")
    lines.append(f"  OUT = Output probe (row {board.VOUT_ROW})")

    # List components
    if comp_counter:
        lines.append("")
        for symbol, count in sorted(comp_counter.items()):
            comp_type = {v: k for k, v in comp_symbols.items()}.get(symbol, 'unknown')
            lines.append(f"  {symbol}  = {comp_type.capitalize()}")

    # Wiring connections
    lines.append("")
    lines.append("=" * 80)
    lines.append("WIRING CONNECTIONS")
    lines.append("=" * 80)
    lines.append("")

    wires = [c for c in board.placed_components if c.type == 'wire']
    if wires:
        for i, wire in enumerate(wires, 1):
            r1, r2 = wire.pins
            lines.append(f"W{i}: row {r1} → row {r2}")
    else:
        lines.append("  No wires placed")

    # SPICE netlist
    lines.append("")
    lines.append("=" * 80)
    lines.append("SPICE NETLIST")
    lines.append("=" * 80)
    lines.append("")

    netlist = board.to_netlist()
    if netlist:
        lines.append(netlist)
    else:
        lines.append("  (Circuit incomplete - netlist not generated)")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def _write_visualization_to_file(visualization: str, filename: str):
    """
    Writes a circuit visualization to a file.

    Args:
        visualization: Visualization string
        filename: Output file path
    """
    output_dir = Path(__file__).resolve().parent.parent / "visualizations"
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / filename
    with open(filepath, 'w') as f:
        f.write(visualization)
    print(f"Visualization saved to: {filepath}")


def _write_netlist_to_file(netlist: str, filename: str):
    """
    Writes a netlist to a file.

    Args:
        netlist: SPICE netlist string
        filename: Output file path
    """
    output_dir = Path(__file__).resolve().parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / filename
    with open(filepath, 'w') as f:
        f.write(netlist)
    print(f"\nNetlist saved to: {filepath}")


def _print_completion():
    """Prints the completion message."""
    print("\n" + "="*70)
    print("Search complete!")
    print("="*70)


if __name__ == "__main__":
    main()
