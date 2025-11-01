#!/usr/bin/env python3
"""End-to-end check for generated SPICE netlists."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard  # noqa: E402
from spice_simulator import run_ac_simulation  # noqa: E402


def choose_row(board: Breadboard, offset: int, height: int = 1) -> int:
    """Clamp requested component row into the work area."""
    min_start = board.WORK_START_ROW
    max_start = board.WORK_END_ROW - (height - 1)
    if max_start < min_start:
        raise ValueError("Breadboard does not have enough work rows for component placement")
    clamped_offset = max(0, min(offset, max_start - min_start))
    return min_start + clamped_offset


def attach_vin_via_gate(board: Breadboard, target_row: int, target_col: int, driver_col: int = 5) -> Breadboard:
    """Drive a target node from VIN using an NMOS gate interface."""
    driver_row = min(target_row, board.WORK_END_ROW - 2)
    board = board.apply_action(('nmos3', driver_row, driver_col))
    board = board.apply_action(('wire', board.VIN_ROW, 0, driver_row + 1, driver_col))
    board = board.apply_action(('wire', driver_row, driver_col, target_row, target_col))
    board = board.apply_action(('wire', driver_row + 2, driver_col, target_row, target_col))
    return board


def build_valid_rc_filter() -> Breadboard:
    """Construct a known-good RC filter used in partial-circuit demos."""
    board = Breadboard()

    resistor_row = choose_row(board, 3, height=2)
    capacitor_row = choose_row(board, 6, height=2)

    board = board.apply_action(('resistor', resistor_row, 1))
    board = attach_vin_via_gate(board, resistor_row, 1, driver_col=5)

    board = board.apply_action(('capacitor', capacitor_row, 1))
    board = board.apply_action(('wire', resistor_row + 1, 1, capacitor_row, 1))

    # Supply resistor to VDD in column 2
    supply_res_row = capacitor_row
    board = board.apply_action(('resistor', supply_res_row, 2))
    board = board.apply_action(('wire', supply_res_row, 2, capacitor_row, 1))
    board = board.apply_action(('wire', supply_res_row + 1, 2, board.VDD_ROW, 0))

    # Load resistor to ground in column 3
    ground_res_row = capacitor_row
    board = board.apply_action(('resistor', ground_res_row, 3))
    board = board.apply_action(('wire', ground_res_row, 3, capacitor_row + 1, 1))
    board = board.apply_action(('wire', ground_res_row + 1, 3, board.VSS_ROW, 0))

    # Winning wire to VOUT
    board = board.apply_action(('wire', capacitor_row + 1, 1, board.VOUT_ROW, 0))

    return board


def test_generated_netlist_runs_spice():
    print("\n=== Netlist Generation Sanity Check ===")

    board = build_valid_rc_filter()
    assert board.is_complete_and_valid(), "Circuit should be valid before exporting netlist"

    position_to_net = board._build_net_mapping()  # noqa: SLF001 - intentional test hook
    vout_comp = next(c for c in board.placed_components if c.type == 'vout')
    vout_net = position_to_net[vout_comp.pins[0]]

    netlist = board.to_netlist()
    assert netlist, "Expected a SPICE netlist string"

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
