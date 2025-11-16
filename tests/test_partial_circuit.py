#!/usr/bin/env python3
"""
Smoke test that a partial circuit can be built with row-only actions.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard  # noqa: E402


def test_partial_circuit_build():
    board = Breadboard()

    resistor_row = board.WORK_START_ROW + 2
    capacitor_row = resistor_row + 3

    board = board.apply_action(("resistor", resistor_row))
    board = board.apply_action(("wire", board.VIN_ROW, resistor_row))
    board = board.apply_action(("capacitor", capacitor_row))
    board = board.apply_action(("wire", resistor_row + 1, capacitor_row))

    assert len([c for c in board.placed_components if c.type == "resistor"]) == 1
    assert len([c for c in board.placed_components if c.type == "capacitor"]) == 1
