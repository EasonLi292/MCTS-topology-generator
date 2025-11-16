#!/usr/bin/env python3
"""
Sanity check that the legal action space contains a straightforward build path
in the row-only model.
"""

import sys
from pathlib import Path

core_dir = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(core_dir))

from topology_game_board import Breadboard


def test_simple_valid_circuit_path():
    board = Breadboard(rows=15)

    actions_sequence = [
        (("wire", board.VIN_ROW, board.WORK_START_ROW + 1), "Activate a work row"),
        (("resistor", board.WORK_START_ROW + 1), "Place resistor R1"),
        (("wire", board.WORK_START_ROW + 2, board.VDD_ROW), "Tie R1 bottom to VDD"),
        (("wire", board.WORK_START_ROW + 1, board.VOUT_ROW), "Probe midpoint with VOUT"),
    ]

    for idx, (action, description) in enumerate(actions_sequence, start=1):
        legal_actions = board.legal_actions()
        assert action in legal_actions, f"Illegal at step {idx}: {description}"
        board = board.apply_action(action)
