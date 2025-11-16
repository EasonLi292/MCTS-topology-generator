#!/usr/bin/env python3
"""
Validation rule smoke tests adapted to row-only model.
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard


def choose_row(board: Breadboard, offset: int, height: int = 1) -> int:
    min_start = board.WORK_START_ROW
    max_start = board.WORK_END_ROW - (height - 1)
    if max_start < min_start:
        raise ValueError("Breadboard does not have enough work rows for component placement")
    clamped_offset = max(0, min(offset, max_start - min_start))
    return min_start + clamped_offset


def attach_vin_via_gate(board: Breadboard, target_row: int) -> Breadboard:
    driver_row = min(target_row, board.WORK_END_ROW - 2)
    board = board.apply_action(('nmos3', driver_row))
    board = board.apply_action(('wire', board.VIN_ROW, driver_row + 1))
    board = board.apply_action(('wire', driver_row, target_row))
    board = board.apply_action(('wire', driver_row + 2, target_row))
    return board


def test_floating_component_detection():
    b = Breadboard()
    resistor_row = choose_row(b, 3, height=2)
    floating_cap_row = choose_row(b, 7, height=2)
    b = b.apply_action(('resistor', resistor_row))
    b = attach_vin_via_gate(b, resistor_row)
    b = b.apply_action(('capacitor', floating_cap_row))
    b = b.apply_action(('wire', resistor_row + 1, b.VOUT_ROW))
    assert not b.is_complete_and_valid()


def test_gate_vdd_connection_prevention():
    b = Breadboard()
    nmos_row = choose_row(b, 3, height=3)
    b = b.apply_action(('nmos3', nmos_row))
    gate_row = nmos_row + 1
    can_wire_gate_to_vdd = b.can_place_wire(gate_row, b.VDD_ROW)
    assert not can_wire_gate_to_vdd


def test_gate_vss_connection_prevention():
    b = Breadboard()
    pmos_row = choose_row(b, 3, height=3)
    b = b.apply_action(('pmos3', pmos_row))
    gate_row = pmos_row + 1
    can_wire_gate_to_vss = b.can_place_wire(gate_row, b.VSS_ROW)
    assert not can_wire_gate_to_vss


def test_base_vdd_connection_prevention():
    b = Breadboard()
    npn_row = choose_row(b, 3, height=3)
    b = b.apply_action(('npn', npn_row))
    base_row = npn_row + 1
    can_wire_base_to_vdd = b.can_place_wire(base_row, b.VDD_ROW)
    assert not can_wire_base_to_vdd


def test_base_vss_connection_prevention():
    b = Breadboard()
    pnp_row = choose_row(b, 3, height=3)
    b = b.apply_action(('pnp', pnp_row))
    base_row = pnp_row + 1
    can_wire_base_to_vss = b.can_place_wire(base_row, b.VSS_ROW)
    assert not can_wire_base_to_vss


def test_valid_circuit_with_all_connected():
    b = Breadboard()
    r1 = choose_row(b, 3, height=2)
    r2 = choose_row(b, 6, height=2)
    b = b.apply_action(('resistor', r1))
    b = b.apply_action(('resistor', r2))
    b = b.apply_action(('wire', b.VIN_ROW, r1))
    b = b.apply_action(('wire', r1 + 1, r2))
    b = b.apply_action(('wire', r2 + 1, b.VDD_ROW))
    b = b.apply_action(('wire', r2, b.VSS_ROW))
    b = b.apply_action(('wire', r2, b.VOUT_ROW))
    assert len(b.placed_components) >= 5


def test_transistor_circuit_with_valid_connections():
    b = Breadboard()
    nmos_row = choose_row(b, 3, height=3)
    b = b.apply_action(('nmos3', nmos_row))
    gate_row = nmos_row + 1
    source_row = nmos_row + 2
    b = b.apply_action(('wire', b.VIN_ROW, gate_row))
    b = b.apply_action(('wire', nmos_row, b.VOUT_ROW))
    b = b.apply_action(('wire', source_row, b.VSS_ROW))
    b = b.apply_action(('wire', gate_row, b.VDD_ROW))  # supply path
    assert len(b.placed_components) >= 4


def test_partial_circuit_not_valid():
    b = Breadboard()
    resistor_row = choose_row(b, 3, height=2)
    b = b.apply_action(('resistor', resistor_row))
    b = attach_vin_via_gate(b, resistor_row)
    assert not b.is_complete_and_valid()


def test_vin_short_to_power_rail_prevents_netlist():
    b = Breadboard()
    mid_row = choose_row(b, 2, height=1)
    b = b.apply_action(('wire', b.VIN_ROW, mid_row))
    b = b.apply_action(('wire', mid_row, b.VSS_ROW))
    summary = b.get_connectivity_summary()
    netlist = b.to_netlist()
    assert summary.get("vin_on_power_rail")
    assert netlist is None
