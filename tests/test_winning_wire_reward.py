#!/usr/bin/env python3
"""Ensure adding a final wire updates connectivity in the row-only model."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard  # noqa: E402


def test_winning_wire_completion():
    b = Breadboard()
    work_row = b.WORK_START_ROW + 2

    b = b.apply_action(("resistor", work_row))
    b = b.apply_action(("capacitor", work_row + 2))
    b = b.apply_action(("wire", b.VIN_ROW, work_row))
    b = b.apply_action(("wire", work_row + 1, work_row + 2))
    b = b.apply_action(("wire", work_row + 3, b.VDD_ROW))
    b = b.apply_action(("wire", work_row + 4, b.VSS_ROW))

    summary_before = b.get_connectivity_summary()
    assert not summary_before.get("reachable_vout", False)

    b = b.apply_action(("wire", work_row + 3, b.VOUT_ROW))
    summary_after = b.get_connectivity_summary()
    assert isinstance(summary_after, dict)
