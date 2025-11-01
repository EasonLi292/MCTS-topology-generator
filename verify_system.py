#!/usr/bin/env python3
"""
Comprehensive system verification:
1. Build a known-good circuit
2. Validate it passes all rules
3. Verify SPICE simulation works
4. Calculate final reward

This proves the entire pipeline works end-to-end.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard
from spice_simulator import run_ac_simulation, calculate_reward_from_simulation
import tempfile


def choose_row(board, offset, height=1):
    min_start = board.WORK_START_ROW
    max_start = board.WORK_END_ROW - (height - 1)
    clamped = max(0, min(offset, max_start - min_start))
    return min_start + clamped


def attach_vin_via_gate(board, target_row, target_col, driver_col=5):
    """Drive target node from VIN using NMOS gate."""
    driver_row = min(target_row, board.WORK_END_ROW - 2)
    board = board.apply_action(('nmos3', driver_row, driver_col))
    board = board.apply_action(('wire', board.VIN_ROW, 0, driver_row + 1, driver_col))
    board = board.apply_action(('wire', driver_row, driver_col, target_row, target_col))
    board = board.apply_action(('wire', driver_row + 2, driver_col, target_row, target_col))
    return board


def build_verified_circuit():
    """Build the exact circuit from test_netlist_output.py that we know works."""
    print("="*70)
    print("BUILDING VERIFIED RC FILTER CIRCUIT")
    print("="*70)
    print("\nThis circuit is known to work (from test_netlist_output.py)")

    board = Breadboard()

    resistor_row = choose_row(board, 3, height=2)
    capacitor_row = choose_row(board, 6, height=2)

    print(f"\n1. Place resistor at rows {resistor_row}-{resistor_row+1}, col 1")
    board = board.apply_action(('resistor', resistor_row, 1))

    print(f"2. Attach VIN via NMOS gate to resistor")
    board = attach_vin_via_gate(board, resistor_row, 1, driver_col=5)

    print(f"3. Place capacitor at rows {capacitor_row}-{capacitor_row+1}, col 1")
    board = board.apply_action(('capacitor', capacitor_row, 1))

    print(f"4. Wire resistor bottom to capacitor top")
    board = board.apply_action(('wire', resistor_row + 1, 1, capacitor_row, 1))

    # Supply resistor to VDD
    supply_res_row = capacitor_row
    print(f"5. Add supply resistor to VDD (col 2)")
    board = board.apply_action(('resistor', supply_res_row, 2))
    board = board.apply_action(('wire', supply_res_row, 2, capacitor_row, 1))
    board = board.apply_action(('wire', supply_res_row + 1, 2, board.VDD_ROW, 0))

    # Ground resistor
    ground_res_row = capacitor_row
    print(f"6. Add ground resistor (col 3)")
    board = board.apply_action(('resistor', ground_res_row, 3))
    board = board.apply_action(('wire', ground_res_row, 3, capacitor_row + 1, 1))
    board = board.apply_action(('wire', ground_res_row + 1, 3, board.VSS_ROW, 0))

    print(f"7. Connect output to VOUT")
    board = board.apply_action(('wire', capacitor_row + 1, 1, board.VOUT_ROW, 0))

    print("\n✅ Circuit built successfully!")
    return board


def main():
    print("="*70)
    print("MCTS TOPOLOGY GENERATOR - SYSTEM VERIFICATION")
    print("="*70)

    # Build circuit
    board = build_verified_circuit()

    # Validate
    print("\n" + "="*70)
    print("VALIDATION CHECK")
    print("="*70)

    is_valid = board.is_complete_and_valid()
    print(f"\n✅ Circuit is complete and valid: {is_valid}")

    if not is_valid:
        print("❌ Validation failed!")
        return False

    # Generate netlist
    print("\n" + "="*70)
    print("NETLIST GENERATION")
    print("="*70)

    netlist = board.to_netlist()
    if not netlist:
        print("❌ Failed to generate netlist!")
        return False

    print("\n📄 Generated SPICE netlist:")
    print("-" * 70)
    print(netlist)
    print("-" * 70)

    # Run SPICE
    print("\n" + "="*70)
    print("SPICE SIMULATION")
    print("="*70)

    print("\n🔧 Running ngspice AC analysis...")
    frequency, output_voltage = run_ac_simulation(netlist)

    if frequency is None or output_voltage is None:
        print("❌ SPICE simulation failed!")
        print("   (ngspice may not be installed or circuit has errors)")
        return False

    print(f"✅ SPICE simulation successful!")
    print(f"   Frequency points: {len(frequency)}")
    print(f"   Output samples: {len(output_voltage)}")

    # Calculate reward
    print("\n" + "="*70)
    print("REWARD CALCULATION")
    print("="*70)

    reward = calculate_reward_from_simulation(frequency, output_voltage)
    print(f"\n🎯 Final reward: {reward:.2f}")

    if reward >= 100:
        print(f"✅ Achieved SPICE baseline reward (100+)")
    else:
        print(f"ℹ️  Got {reward:.2f} points (baseline is 100)")

    # Summary
    print("\n" + "="*70)
    print("SYSTEM VERIFICATION COMPLETE")
    print("="*70)

    print("\n✅ ALL SYSTEMS OPERATIONAL:")
    print("  ✓ Circuit building")
    print("  ✓ Validation rules")
    print("  ✓ Netlist generation")
    print("  ✓ SPICE integration")
    print("  ✓ Reward calculation")

    print("\n✨ The MCTS topology generator is working correctly!")
    print("📚 System is ready for:")
    print("  • GNN integration")
    print("  • Extended search experiments")
    print("  • Custom reward functions")
    print("  • Additional component types")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
