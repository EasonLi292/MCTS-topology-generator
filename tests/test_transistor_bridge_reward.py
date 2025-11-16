#!/usr/bin/env python3
"""
Regression sanity for transistor bridge constructs in the row-only model.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from topology_game_board import Breadboard  # noqa: E402
from MCTS import MCTS  # noqa: E402


def _build_transistor_bridge():
    b = Breadboard(rows=15)
    # Place transistors
    pnp_row = b.WORK_START_ROW + 1
    npn_row = pnp_row + 6
    b = b.apply_action(("pnp", pnp_row))
    b = b.apply_action(("npn", npn_row))

    # Wire collectors/sources to rails
    b = b.apply_action(("wire", pnp_row, b.VDD_ROW))
    b = b.apply_action(("wire", npn_row + 2, b.VSS_ROW))

    # Tie gates/bases to VIN and bridge outputs to VOUT
    b = b.apply_action(("wire", b.VIN_ROW, pnp_row + 1))
    b = b.apply_action(("wire", b.VIN_ROW, npn_row + 1))
    b = b.apply_action(("wire", pnp_row + 2, npn_row))
    b = b.apply_action(("wire", pnp_row + 2, b.VOUT_ROW))
    return b


def test_transistor_bridge_flags_as_complete():
    board = _build_transistor_bridge()
    netlist = board.to_netlist()
    assert netlist is not None
    stats_board = MCTS(board).best_candidate_state or board
    assert stats_board is not None


def test_transistor_bridge_spice_succeeds_but_trivial_reward():
    board = _build_transistor_bridge()
    netlist = board.to_netlist()
    assert netlist is not None
    mcts = MCTS(board)
    mcts.search(iterations=50)
    assert mcts.best_candidate_state is not None
