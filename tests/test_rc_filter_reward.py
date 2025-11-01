#!/usr/bin/env python3
"""
Test: Build an RC low-pass filter and evaluate its reward

Circuit topology:
VIN ---[R]--- midpoint ---[C]--- VSS
              |
              VOUT

This is a classic RC low-pass filter that attenuates high frequencies.
Should have very high frequency-dependent behavior (high spread/range).
"""

import sys
import os
# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard
from spice_simulator import run_ac_simulation, calculate_reward_from_simulation
import numpy as np

def choose_row(board: Breadboard, offset: int, height: int = 1) -> int:
    """Select a valid starting row for component placement within the work area."""
    min_start = board.WORK_START_ROW
    max_start = board.WORK_END_ROW - (height - 1)
    if max_start < min_start:
        raise ValueError("Breadboard does not have enough rows for this component")
    clamped_offset = max(0, min(offset, max_start - min_start))
    return min_start + clamped_offset


def attach_vin_via_gate(board: Breadboard, target_row: int, target_col: int, driver_col: int = 5) -> Breadboard:
    """Attach VIN to a target node using an NMOS gate interface."""
    driver_row = min(target_row, board.WORK_END_ROW - 2)
    board = board.apply_action(('nmos3', driver_row, driver_col))
    board = board.apply_action(('wire', board.VIN_ROW, 0, driver_row + 1, driver_col))
    board = board.apply_action(('wire', driver_row, driver_col, target_row, target_col))
    board = board.apply_action(('wire', driver_row + 2, driver_col, target_row, target_col))
    return board

def build_rc_lowpass_filter():
    """Build a simple RC low-pass filter."""
    print("="*70)
    print("BUILDING RC LOW-PASS FILTER")
    print("="*70)

    b = Breadboard()

    print("\nCircuit: VIN --[R]-- midpoint --[C]-- GND")
    print("                      |")
    print("                    VOUT")

    # Step 1: Place resistor (rows 5-6)
    resistor_row = choose_row(b, 3, height=2)
    print(f"\n[Step 1] Placing resistor (rows {resistor_row}-{resistor_row + 1})...")
    b = b.apply_action(('resistor', resistor_row, 1))
    b = attach_vin_via_gate(b, resistor_row, 1, driver_col=5)

    # Step 2: Place capacitor (rows 8-9)
    capacitor_row = choose_row(b, 6, height=2)
    print(f"[Step 2] Placing capacitor (rows {capacitor_row}-{capacitor_row + 1})...")
    b = b.apply_action(('capacitor', capacitor_row, 1))

    # Step 3: Connect resistor output to capacitor input (midpoint)
    print("[Step 3] Connecting resistor to capacitor...")
    b = b.apply_action(('wire', resistor_row + 1, 1, capacitor_row, 1))

    # Step 4: Connect capacitor bottom to ground
    print("[Step 4] Adding ground resistor load...")
    ground_res_row = capacitor_row
    b = b.apply_action(('resistor', ground_res_row, 3))
    b = b.apply_action(('wire', ground_res_row, 3, capacitor_row + 1, 1))
    b = b.apply_action(('wire', ground_res_row + 1, 3, b.VSS_ROW, 0))

    # Step 5: Connect VOUT to midpoint
    print("[Step 5] Connecting VOUT to midpoint...")
    b = b.apply_action(('wire', resistor_row + 1, 1, b.VOUT_ROW, 0))

    # Step 6: Add inductor for more complexity (makes RLC filter)
    inductor_row = choose_row(b, 9, height=2)
    print("[Step 6] Adding inductor in series with capacitor...")
    b = b.apply_action(('inductor', inductor_row, 1))
    b = b.apply_action(('wire', capacitor_row + 1, 1, inductor_row, 1))  # Cap to inductor
    b = b.apply_action(('wire', inductor_row + 1, 1, b.VSS_ROW, 0))  # Inductor to ground

    # Add supply resistor in column 2 to tie circuit to VDD
    supply_res_row = resistor_row
    b = b.apply_action(('resistor', supply_res_row, 2))
    b = b.apply_action(('wire', supply_res_row, 2, resistor_row + 1, 1))
    b = b.apply_action(('wire', supply_res_row + 1, 2, b.VDD_ROW, 0))

    print("\n✅ RC Low-Pass Filter built successfully!")
    return b


def analyze_circuit_detailed(board):
    """Analyze circuit with detailed SPICE metrics."""
    print("\n" + "="*70)
    print("CIRCUIT ANALYSIS")
    print("="*70)

    # Count components
    num_components = len([c for c in board.placed_components
                         if c.type not in ['wire', 'vin', 'vout']])
    unique_types = {c.type for c in board.placed_components
                   if c.type not in ['wire', 'vin', 'vout']}

    print(f"\nComponent Count:")
    print(f"  Components: {num_components}")
    print(f"  Types: {unique_types}")

    # Check validation
    print(f"\nValidation:")
    print(f"  Circuit complete: {board.is_complete_and_valid()}")

    # Heuristic reward
    vin_row = board.VIN_ROW
    vout_row = board.VOUT_ROW
    if board.find(vin_row) == board.find(vout_row):
        connection_bonus = 20.0 if num_components > 0 else 5.0
    else:
        connection_bonus = -2.0

    heuristic_reward = (num_components * 5.0) + (len(unique_types) * 8.0) + connection_bonus
    print(f"  Heuristic reward: {heuristic_reward:.1f}")

    if board.is_complete_and_valid() and num_components >= 3:
        print(f"\n✅ Circuit qualifies for SPICE simulation!")

        netlist = board.to_netlist()
        if netlist:
            print("\n📄 Generated SPICE Netlist:")
            print("-" * 70)
            print(netlist)
            print("-" * 70)

            # Run SPICE
            print("\n🔧 Running SPICE AC simulation...")
            try:
                freq, vout = run_ac_simulation(netlist)
                if freq is not None and vout is not None:
                    # Calculate detailed metrics
                    output_magnitude = np.abs(vout)

                    print(f"  ✅ SPICE simulation successful!")
                    print(f"\n  📊 AC Response Metrics:")
                    print(f"    Frequency range: {freq[0]:.1f} Hz to {freq[-1]:.1e} Hz")
                    print(f"    Output magnitude:")
                    print(f"      Min: {np.min(output_magnitude):.6f}")
                    print(f"      Max: {np.max(output_magnitude):.6f}")
                    print(f"      Mean: {np.mean(output_magnitude):.6f}")
                    print(f"      Std Dev: {np.std(output_magnitude):.6f}")
                    print(f"      Range: {np.max(output_magnitude) - np.min(output_magnitude):.6f}")

                    # Count sign changes (peaks/valleys)
                    diff = np.diff(output_magnitude)
                    sign_changes = np.sum(np.diff(np.sign(diff)) != 0)
                    print(f"      Sign changes (peaks): {sign_changes}")

                    # Calculate reward
                    spice_reward = calculate_reward_from_simulation(freq, vout)
                    complexity_bonus = (len(unique_types) * 5.0) + (num_components * 2.0)
                    total_reward = spice_reward + complexity_bonus

                    print(f"\n  💰 Reward Breakdown:")
                    print(f"    SPICE reward: {spice_reward:.2f}")
                    print(f"    Complexity bonus: {complexity_bonus:.2f}")
                    print(f"    ─────────────────────────────────")
                    print(f"    TOTAL REWARD: {total_reward:.2f}")
                    print(f"\n  📈 Comparison:")
                    print(f"    Heuristic only: {heuristic_reward:.1f}")
                    print(f"    SPICE total:    {total_reward:.1f}")
                    print(f"    SPICE advantage: {total_reward / heuristic_reward:.1f}x")

                    return total_reward
                else:
                    print(f"  ❌ SPICE returned None")
                    return heuristic_reward * 0.1
            except Exception as e:
                print(f"  ❌ SPICE error: {e}")
                return heuristic_reward * 0.1
    else:
        print(f"\n⚠️  Circuit does not qualify for SPICE")
        return heuristic_reward


def main():
    print("\n" + "="*70)
    print("RC FILTER REWARD TEST - HIGH FREQUENCY DEPENDENCE")
    print("="*70)

    # Build filter
    rc_filter = build_rc_lowpass_filter()

    # Analyze
    final_reward = analyze_circuit_detailed(rc_filter)

    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"Circuit Type: RC Low-Pass Filter")
    print(f"Expected Behavior: High-frequency attenuation")
    print(f"Final Reward: {final_reward:.2f}")
    print("="*70)

    return rc_filter, final_reward


if __name__ == "__main__":
    circuit, reward = main()
