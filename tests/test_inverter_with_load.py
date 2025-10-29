#!/usr/bin/env python3
"""
Test: Build a CMOS inverter with load resistor and evaluate its reward

Circuit topology:
VDD (row 29)
 |
 |-- PMOS source (pin 2)
     PMOS gate (pin 1) <-- VIN
     PMOS drain (pin 0)
      |
      |-- Output node (with resistor to ground)
      |   |
      |   Resistor
      |   |
      |   VSS
      |
     NMOS drain (pin 0)
     NMOS gate (pin 1) <-- VIN
     NMOS source (pin 2)
      |
     VSS (row 0, ground)

This is a CMOS inverter with a pull-down resistor load for better output characteristics.
"""

import sys
import os
# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard
from spice_simulator import run_ac_simulation, calculate_reward_from_simulation

def build_cmos_inverter_with_load():
    """Build a CMOS inverter with load resistor."""
    print("="*70)
    print("BUILDING CMOS INVERTER WITH LOAD RESISTOR")
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
    print(f"  PMOS placed: drain=row 10, gate=row 11, source=row 12")

    # Step 2: Place NMOS transistor (drain=15, gate=16, source=17)
    print("\n[Step 2] Placing NMOS at rows 15-16-17...")
    b = b.apply_action(('wire', b.VSS_ROW, 0, 17, 2))  # Activate row 17 from VSS
    b = b.apply_action(('nmos3', 15, 2))
    print(f"  NMOS placed: drain=row 15, gate=row 16, source=row 17")

    # Step 3: Connect both drains together (output node)
    print("\n[Step 3] Connecting PMOS drain (row 10) to NMOS drain (row 15)...")
    b = b.apply_action(('wire', 10, 1, 15, 2))

    # Step 4: Connect both gates to VIN
    print("\n[Step 4] Connecting gates to VIN...")
    b = b.apply_action(('wire', b.VIN_ROW, 0, 11, 1))  # PMOS gate to VIN
    b = b.apply_action(('wire', b.VIN_ROW, 0, 16, 2))  # NMOS gate to VIN

    # Step 5: Add load resistor on output (rows 20-21)
    print("\n[Step 5] Adding load resistor (rows 20-21)...")
    b = b.apply_action(('resistor', 20, 3))
    b = b.apply_action(('wire', 10, 1, 20, 3))  # Connect output node to resistor
    b = b.apply_action(('wire', 21, 3, b.VSS_ROW, 3))  # Resistor to ground

    # Step 6: Connect output node to VOUT
    print("\n[Step 6] Connecting output node to VOUT...")
    b = b.apply_action(('wire', 10, 1, b.VOUT_ROW, 0))

    print("\n✅ CMOS Inverter with load resistor built successfully!")
    return b


def analyze_circuit(board):
    """Analyze the circuit and compute rewards."""
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
    print(f"  Component types: {unique_types}")
    print(f"  Wires: {num_wires}")

    # Check connectivity
    vin_row = board.VIN_ROW
    vout_row = board.VOUT_ROW

    print(f"\nConnectivity:")
    print(f"  VIN-VOUT connected: {board.find(vin_row) == board.find(vout_row)}")
    print(f"  All components connected: {board._all_components_connected()}")
    print(f"  Gate/base validation: {board._validate_gate_base_connections()}")
    print(f"  Circuit complete: {board.is_complete_and_valid()}")

    # Calculate heuristic reward
    if board.find(vin_row) == board.find(vout_row):
        connection_bonus = 20.0 if num_components > 0 else 5.0
    else:
        connection_bonus = -2.0

    heuristic_reward = (num_components * 5.0) + (len(unique_types) * 8.0) + connection_bonus

    print(f"\n📊 Heuristic Reward Breakdown:")
    print(f"  Component reward: {num_components} × 5.0 = {num_components * 5.0}")
    print(f"  Diversity reward: {len(unique_types)} × 8.0 = {len(unique_types) * 8.0}")
    print(f"  Connection bonus: {connection_bonus}")
    print(f"  ─────────────────────────────────")
    print(f"  TOTAL HEURISTIC: {heuristic_reward}")

    # Check if circuit qualifies for SPICE simulation
    if board.is_complete_and_valid() and num_components >= 3:
        print(f"\n✅ Circuit qualifies for SPICE simulation!")

        # Generate netlist
        netlist = board.to_netlist()
        if netlist:
            print("\n📄 Generated SPICE Netlist:")
            print("-" * 70)
            print(netlist)
            print("-" * 70)

            # Save netlist
            with open('inverter_with_load.sp', 'w') as f:
                f.write(netlist)
            print("\n💾 Netlist saved to: inverter_with_load.sp")

            # Try to run SPICE simulation
            print("\n🔧 Running SPICE AC simulation...")
            try:
                freq, vout = run_ac_simulation(netlist)
                if freq is not None and vout is not None:
                    spice_reward = calculate_reward_from_simulation(freq, vout)
                    complexity_bonus = (len(unique_types) * 5.0) + (num_components * 2.0)
                    total_reward = spice_reward + complexity_bonus

                    print(f"  ✅ SPICE simulation successful!")
                    print(f"\n  📊 SPICE Reward Breakdown:")
                    print(f"    Base SPICE reward: {spice_reward:.4f}")
                    print(f"    Complexity bonus: {complexity_bonus:.4f}")
                    print(f"    ─────────────────────────────────")
                    print(f"    TOTAL REWARD: {total_reward:.4f}")

                    return total_reward, netlist
                else:
                    print(f"  ❌ SPICE simulation returned None")
                    fallback_reward = max(0.01, heuristic_reward * 0.1)
                    print(f"  Fallback reward: {fallback_reward:.4f}")
                    return fallback_reward, netlist
            except Exception as e:
                print(f"  ❌ SPICE error: {e}")
                fallback_reward = max(0.01, heuristic_reward * 0.1)
                print(f"  Fallback reward: {fallback_reward:.4f}")
                return fallback_reward, netlist
        else:
            print("  ❌ Failed to generate netlist")
            return 0.0, None
    else:
        print(f"\n⚠️  Circuit does not qualify for SPICE simulation")
        if num_components < 3:
            print(f"  Reason: Only {num_components} components (need ≥3)")
        if not board.is_complete_and_valid():
            print(f"  Reason: Circuit not complete/valid")
        print(f"\n  Heuristic-only reward: {heuristic_reward:.4f}")
        return heuristic_reward, None


def main():
    print("\n" + "="*70)
    print("CMOS INVERTER WITH LOAD - REWARD TEST")
    print("="*70)

    # Build the inverter
    inverter = build_cmos_inverter_with_load()

    # Analyze and get reward
    final_reward, netlist = analyze_circuit(inverter)

    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"Circuit Type: CMOS Inverter with Load Resistor")
    print(f"Total Components: 3 (PMOS + NMOS + Resistor)")
    print(f"Total Wires: {len([c for c in inverter.placed_components if c.type == 'wire'])}")
    print(f"Final Reward: {final_reward:.4f}")
    print("="*70)

    if netlist:
        print("\n💡 This circuit demonstrates:")
        print("  • Complementary MOSFET pair (CMOS)")
        print("  • Both gates driven by same input (inverter action)")
        print("  • Load resistor for output pull-down")
        print("  • All validation rules satisfied ✓")

    return inverter, final_reward


if __name__ == "__main__":
    circuit, reward = main()
