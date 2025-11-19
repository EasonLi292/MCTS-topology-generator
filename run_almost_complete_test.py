#!/usr/bin/env python3
"""
Run the almost-complete MCTS test (2 moves away from completion).
"""

import sys
import os

# Ensure core is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

# Now import and run the test
from topology_game_board import Breadboard
from MCTS import MCTS


def build_almost_complete_board():
    """Build a board that's 2 moves away from completion."""
    b = Breadboard(rows=15)
    mid = b.WORK_START_ROW + 3

    # Place first resistor and wire it to VIN
    b = b.apply_action(("resistor", mid))
    b = b.apply_action(("wire", b.VIN_ROW, mid))

    # Place second resistor (gate)
    g_row = mid + 2
    b = b.apply_action(("resistor", g_row))
    b = b.apply_action(("wire", g_row, mid + 1))
    b = b.apply_action(("wire", g_row + 1, b.VSS_ROW))

    # Place third resistor (source)
    s_row = g_row + 2
    b = b.apply_action(("resistor", s_row))
    b = b.apply_action(("wire", s_row, mid + 1))
    # NOTE: Removed the wire to VDD, making it 2 moves away:
    # Move 1: wire from s_row + 1 to VDD
    # Move 2: wire from mid + 1 to VOUT_ROW

    return b, mid


def main():
    print("="*70)
    print("MCTS Test: Almost Complete Circuit (2 moves away)")
    print("="*70)

    # Build the almost-complete board
    initial_board, mid = build_almost_complete_board()

    print(f"\nInitial board state:")
    print(f"  Components placed: {len(initial_board.placed_components)}")
    print(f"  Circuit complete: {initial_board.is_complete_and_valid()}")

    # Check what happens if we manually complete it
    print(f"\nVerifying completion path...")
    test_board = initial_board
    print(f"  Initial state - Complete: {test_board.is_complete_and_valid()}")

    # Calculate s_row the same way as in build function
    s_row = (initial_board.WORK_START_ROW + 3) + 2 + 2

    # Try adding first wire (to VDD)
    test_board_1 = test_board.apply_action(("wire", s_row + 1, test_board.VDD_ROW))
    print(f"  After wire to VDD - Complete: {test_board_1.is_complete_and_valid()}")

    # Try adding second wire (to VOUT)
    test_board_2 = test_board_1.apply_action(("wire", mid + 1, test_board_1.VOUT_ROW))
    print(f"  After wire to VOUT - Complete: {test_board_2.is_complete_and_valid()}")
    print(f"  Components: {len(test_board_2.placed_components)}")

    if test_board_2.is_complete_and_valid() and not test_board_1.is_complete_and_valid():
        print(f"\n✓ Confirmed: Circuit is 2 moves away from completion")
        moves_needed = 2
    elif test_board_1.is_complete_and_valid():
        print(f"\n✓ Confirmed: Circuit is 1 move away from completion")
        moves_needed = 1
    else:
        print(f"\n  Need more than 2 moves...")
        moves_needed = 3

    # Run MCTS
    print(f"\n{'='*70}")
    print(f"Starting MCTS search (max 50000 iterations)...")
    print(f"{'='*70}")

    mcts = MCTS(initial_board)

    max_iterations = 50000
    for i in range(1, max_iterations + 1):
        mcts.search(iterations=1)

        # Check progress every 1000 iterations
        if i % 1000 == 0:
            path, reward = mcts.get_best_solution()
            print(f"\nIteration {i}:")
            print(f"  Best path length: {len(path)} actions")
            print(f"  Average reward: {reward:.4f}")

            # Try to reconstruct and check if complete
            final_board = initial_board
            for action in path:
                try:
                    final_board = final_board.apply_action(action)
                except Exception as e:
                    break

            if final_board.is_complete_and_valid():
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
                output_path = 'outputs/mcts_almost_complete_result.txt'
                with open(output_path, 'w') as f:
                    f.write(f"Success at iteration {i}\n")
                    f.write(f"Action sequence:\n")
                    for j, action in enumerate(path, 1):
                        f.write(f"{j}. {action}\n")
                    f.write(f"\nNetlist:\n{netlist}\n")

                return True

    # If we get here, we didn't complete in 50000 iterations
    print(f"\n{'='*70}")
    print(f"Reached {max_iterations} iterations without completion")
    print(f"{'='*70}")

    path, reward = mcts.get_best_solution()
    print(f"\nBest solution found:")
    print(f"  Path length: {len(path)} actions")
    print(f"  Average reward: {reward:.4f}")
    print(f"\nAction sequence:")
    for j, action in enumerate(path, 1):
        print(f"  {j}. {action}")

    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
