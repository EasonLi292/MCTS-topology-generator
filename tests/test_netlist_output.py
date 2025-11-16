#!/usr/bin/env python3
"""End-to-end check for generated SPICE netlists (row-only model)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard  # noqa: E402
from spice_simulator import run_ac_simulation  # noqa: E402


def build_valid_rc_filter() -> Breadboard:
    board = Breadboard()

    r1 = board.WORK_START_ROW
    r2 = r1 + 3
    r3 = r2 + 3

    # R1: VIN to midpoint
    board = board.apply_action(("resistor", r1))
    board = board.apply_action(("wire", board.VIN_ROW, r1))

    # R2: midpoint to VSS
    board = board.apply_action(("resistor", r2))
    board = board.apply_action(("wire", r1 + 1, r2))
    board = board.apply_action(("wire", r2 + 1, board.VSS_ROW))

    # R3: midpoint to VDD
    board = board.apply_action(("resistor", r3))
    board = board.apply_action(("wire", r1 + 1, r3))
    board = board.apply_action(("wire", r3 + 1, board.VDD_ROW))

    # VOUT taps midpoint
    board = board.apply_action(("wire", r1 + 1, board.VOUT_ROW))

    return board


def test_generated_netlist_runs_spice():
    print("\n=== Netlist Generation Sanity Check ===")

    board = build_valid_rc_filter()
    netlist = board.to_netlist()
    assert netlist, "Expected a SPICE netlist string"

    position_to_net = board._build_net_mapping()  # noqa: SLF001
    vout_comp = next(c for c in board.placed_components if c.type == 'vout')
    vout_net = position_to_net[vout_comp.pins[0]]

    if f".print ac v({vout_net})" not in netlist:
        raise AssertionError(f"Netlist missing VOUT probe (.print ac v({vout_net}))")

    freq, vout = run_ac_simulation(netlist)
    if freq is None or vout is None:
        print("⚠️  SPICE not available; skipping simulation verification.")
        return

    assert freq.size > 0 and vout.size > 0, "SPICE simulation returned empty result set"
    print("✅ Netlist probes VOUT and runs through ngspice without fatal errors.")


if __name__ == "__main__":
    test_generated_netlist_runs_spice()
