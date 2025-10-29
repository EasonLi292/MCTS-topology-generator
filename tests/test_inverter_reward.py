#!/usr/bin/env python3
"""
Test: Build a CMOS inverter and evaluate its reward

Circuit topology:
VDD (row 29)
 |
 |-- PMOS source (pin 2)
     PMOS gate (pin 1) <-- VIN
     PMOS drain (pin 0)
      |
      |-- VOUT (output node)
      |
     NMOS drain (pin 0)
     NMOS gate (pin 1) <-- VIN
     NMOS source (pin 2)
      |
     VSS (row 0, ground)

This is a classic CMOS inverter - when VIN is high, NMOS conducts and pulls output low.
When VIN is low, PMOS conducts and pulls output high.
"""

import sys
import os
# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard
from spice_simulator import run_ac_simulation, calculate_reward_from_simulation

def build_cmos_inverter():
    """
    Build a CMOS inverter step by step.

    PMOS: pin 0 = drain, pin 1 = gate, pin 2 = source
    NMOS: pin 0 = drain, pin 1 = gate, pin 2 = source
    """
    print("="*70)
    print("BUILDING CMOS INVERTER")
    print("="*70)

    b = Breadboard()

    print("\nInitial board:")
    print(f"  VIN at row {b.VIN_ROW}")
    print(f"  VOUT at row {b.VOUT_ROW}")
    print(f"  VSS at row {b.VSS_ROW}")
    print(f"  VDD at row {b.VDD_ROW}")

    # Step 1: Place PMOS transistor (drain=10, gate=11, source=12)
    print("\n[Step 1] Placing PMOS at rows 10-11-12...")
    b = b.apply_action(('wire', b.VDD_ROW, 0, 12, 1))  # Activate row 12 from VDD
    b = b.apply_action(('pmos3', 10, 1))
    print(f"  PMOS pins: drain={b.placed_components[-1].pins[0]}, gate={b.placed_components[-1].pins[1]}, source={b.placed_components[-1].pins[2]}")

    # Step 2: Connect PMOS source to VDD
    print("\n[Step 2] Connecting PMOS source (row 12) to VDD (row 29)...")
    # Already connected by the wire from step 1
    print(f"  Row 12 connected to VDD: {b.find(12) == b.find(b.VDD_ROW)}")

    # Step 3: Place NMOS transistor (drain=15, gate=16, source=17)
    print("\n[Step 3] Placing NMOS at rows 15-16-17...")
    b = b.apply_action(('wire', b.VSS_ROW, 0, 17, 2))  # Activate row 17 from VSS
    b = b.apply_action(('nmos3', 15, 2))
    print(f"  NMOS pins: drain={b.placed_components[-1].pins[0]}, gate={b.placed_components[-1].pins[1]}, source={b.placed_components[-1].pins[2]}")

    # Step 4: Connect NMOS source to VSS (ground)
    print("\n[Step 4] Connecting NMOS source (row 17) to VSS (row 0)...")
    # Already connected by the wire from step 3
    print(f"  Row 17 connected to VSS: {b.find(17) == b.find(b.VSS_ROW)}")

    # Step 5: Connect both drains together (output node)
    print("\n[Step 5] Connecting PMOS drain (row 10) to NMOS drain (row 15)...")
    b = b.apply_action(('wire', 10, 1, 15, 2))
    print(f"  Drains connected: {b.find(10) == b.find(15)}")

    # Step 6: Connect both gates to VIN
    print("\n[Step 6] Connecting PMOS gate (row 11) to VIN (row 1)...")
    b = b.apply_action(('wire', b.VIN_ROW, 0, 11, 1))
    print(f"  PMOS gate connected to VIN: {b.find(11) == b.find(b.VIN_ROW)}")

    print("\n[Step 7] Connecting NMOS gate (row 16) to VIN (row 1)...")
    b = b.apply_action(('wire', b.VIN_ROW, 0, 16, 2))
    print(f"  NMOS gate connected to VIN: {b.find(16) == b.find(b.VIN_ROW)}")

    # Step 8: Connect output node (drain junction) to VOUT
    print("\n[Step 8] Connecting output node (row 10) to VOUT (row 28)...")
    b = b.apply_action(('wire', 10, 1, b.VOUT_ROW, 0))
    print(f"  Output connected to VOUT: {b.find(10) == b.find(b.VOUT_ROW)}")

    return b


def analyze_circuit(board):
    """Analyze the circuit and compute heuristic rewards."""
    print("\n" + "="*70)
    print("CIRCUIT ANALYSIS")
    print("="*70)

    # Count components
    num_components = len([c for c in board.placed_components
                         if c.type not in ['wire', 'vin', 'vout']])
    num_wires = len([c for c in board.placed_components if c.type == 'wire'])
    unique_types = {c.type for c in board.placed_components
                   if c.type not in ['wire', 'vin', 'vout']}

    print(f"\nComponent Count:")
    print(f"  Components: {num_components}")
    print(f"  Wires: {num_wires}")
    print(f"  Unique component types: {len(unique_types)} {unique_types}")

    # Check connectivity
    vin_row = board.VIN_ROW
    vout_row = board.VOUT_ROW

    print(f"\nConnectivity:")
    print(f"  VIN-VOUT connected: {board.find(vin_row) == board.find(vout_row)}")
    print(f"  All components connected: {board._all_components_connected()}")
    print(f"  Gate/base validation: {board._validate_gate_base_connections()}")
    print(f"  Circuit complete: {board.is_complete_and_valid()}")

    # Calculate heuristic reward (import sys; sys.path.append("../core")
from MCTS.py logic)
    if board.find(vin_row) == board.find(vout_row):
        if num_components > 0:
            connection_bonus = 20.0
        else:
            connection_bonus = 5.0
    else:
        connection_bonus = -2.0

    heuristic_reward = (num_components * 5.0) + (len(unique_types) * 8.0) + connection_bonus

    print(f"\nHeuristic Reward Breakdown:")
    print(f"  Component reward: {num_components} × 5.0 = {num_components * 5.0}")
    print(f"  Diversity reward: {len(unique_types)} × 8.0 = {len(unique_types) * 8.0}")
    print(f"  Connection bonus: {connection_bonus}")
    print(f"  TOTAL HEURISTIC: {heuristic_reward}")

    # Check if circuit qualifies for SPICE simulation
    if board.is_complete_and_valid() and num_components >= 3:
        print(f"\n✅ Circuit qualifies for SPICE simulation (≥3 components)")

        # Generate netlist
        netlist = board.to_netlist()
        if netlist:
            print("\nGenerated SPICE Netlist:")
            print("-" * 70)
            print(netlist)
            print("-" * 70)

            # Try to run SPICE simulation
            print("\nRunning SPICE AC simulation...")
            try:
                freq, vout = run_ac_simulation(netlist)
                if freq is not None and vout is not None:
                    spice_reward = calculate_reward_from_simulation(freq, vout)
                    complexity_bonus = (len(unique_types) * 5.0) + (num_components * 2.0)
                    total_reward = spice_reward + complexity_bonus

                    print(f"  ✅ SPICE simulation successful!")
                    print(f"\n  SPICE reward: {spice_reward:.4f}")
                    print(f"  Complexity bonus: {complexity_bonus:.4f}")
                    print(f"  TOTAL REWARD: {total_reward:.4f}")

                    return total_reward
                else:
                    print(f"  ❌ SPICE simulation failed")
                    fallback_reward = max(0.01, heuristic_reward * 0.1)
                    print(f"  Fallback reward: {fallback_reward:.4f}")
                    return fallback_reward
            except Exception as e:
                print(f"  ❌ SPICE error: {e}")
                fallback_reward = max(0.01, heuristic_reward * 0.1)
                print(f"  Fallback reward: {fallback_reward:.4f}")
                return fallback_reward
        else:
            print("  ❌ Failed to generate netlist")
            return 0.0
    else:
        print(f"\n⚠️  Circuit does not qualify for SPICE simulation")
        if num_components < 3:
            print(f"  Reason: Only {num_components} components (need ≥3)")
        if not board.is_complete_and_valid():
            print(f"  Reason: Circuit not complete/valid")
        print(f"\n  Heuristic-only reward: {heuristic_reward:.4f}")
        return heuristic_reward


def main():
    print("\n" + "="*70)
    print("CMOS INVERTER REWARD TEST")
    print("="*70)

    # Build the inverter
    inverter = build_cmos_inverter()

    # Analyze and get reward
    final_reward = analyze_circuit(inverter)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Circuit: CMOS Inverter")
    print(f"Components: 2 (PMOS + NMOS)")
    print(f"Final Reward: {final_reward:.4f}")
    print("="*70)

    return inverter, final_reward


if __name__ == "__main__":
    circuit, reward = main()
