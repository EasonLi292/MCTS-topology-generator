#!/usr/bin/env python3
"""
Row-only model: smoke checks that we can build and extend partial circuits.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard  # noqa: E402


def build_near_complete_board() -> Breadboard:
    b = Breadboard(rows=15)
    mid = b.WORK_START_ROW + 3

    b = b.apply_action(("resistor", mid))
    b = b.apply_action(("wire", b.VIN_ROW, mid))

    g_row = mid + 2
    b = b.apply_action(("resistor", g_row))
    b = b.apply_action(("wire", g_row, mid + 1))
    b = b.apply_action(("wire", g_row + 1, b.VSS_ROW))

    s_row = g_row + 2
    b = b.apply_action(("resistor", s_row))
    b = b.apply_action(("wire", s_row, mid + 1))
    b = b.apply_action(("wire", s_row + 1, b.VDD_ROW))

    return b, mid


def test_one_wire_away():
    b, mid = build_near_complete_board()
    b = b.apply_action(("wire", mid + 1, b.VOUT_ROW))
    assert len(b.placed_components) >= 5


def test_two_steps_away():
    b, mid = build_near_complete_board()
    b = b.apply_action(("wire", mid + 1, b.VOUT_ROW))
    assert len(b.placed_components) >= 5


def test_components_placed_need_wiring():
    b = Breadboard(rows=15)
    r1 = b.WORK_START_ROW + 2
    r2 = r1 + 2

    b = b.apply_action(("resistor", r1))
    b = b.apply_action(("resistor", r2))

    b = b.apply_action(("wire", b.VIN_ROW, r1))
    b = b.apply_action(("wire", r1 + 1, r2))
    b = b.apply_action(("wire", r2 + 1, b.VDD_ROW))
    b = b.apply_action(("wire", r2, b.VSS_ROW))
    b = b.apply_action(("wire", r2, b.VOUT_ROW))

    assert len(b.placed_components) >= 4
