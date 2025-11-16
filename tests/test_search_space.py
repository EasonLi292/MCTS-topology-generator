#!/usr/bin/env python3
"""
Test to verify that a valid circuit can be constructed through legal actions
in the row-only node model.
"""

import sys
from pathlib import Path

# Add core directory to path
core_dir = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(core_dir))

from topology_game_board import Breadboard


def test_search_space_reachability():
    """Ensure a simple build path is present in the legal action space."""
    board = Breadboard(rows=15)

    actions_sequence = [
        (("wire", board.VIN_ROW, board.WORK_START_ROW), "Wire VIN to first work row"),
        (("resistor", board.WORK_START_ROW), "Place a resistor spanning two rows"),
        (("wire", board.WORK_START_ROW + 1, board.VOUT_ROW), "Wire resistor output to VOUT row"),
    ]

    for idx, (action, description) in enumerate(actions_sequence, start=1):
        legal_actions = board.legal_actions()
        assert action in legal_actions, f"Step {idx} illegal: {description}"
        board = board.apply_action(action)
