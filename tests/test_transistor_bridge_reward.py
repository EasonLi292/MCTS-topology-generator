#!/usr/bin/env python3
"""
Regression tests for trivial transistor bridges that currently pass validation
but only earn the heuristic fallback reward because SPICE fails.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from topology_game_board import Breadboard  # noqa: E402
from MCTS import MCTS, CircuitStatistics  # noqa: E402
from spice_simulator import run_ac_simulation  # noqa: E402


BRIDGE_ACTIONS = [
    ("pnp", 2, 1),
    ("npn", 10, 1),
    ("wire", 0, 0, 12, 1),
    ("wire", 4, 1, 14, 0),
    ("wire", 1, 0, 3, 1),
    ("wire", 0, 0, 2, 1),
    ("wire", 10, 1, 13, 0),
]


def _build_transistor_bridge():
    board = Breadboard(rows=15)
    for action in BRIDGE_ACTIONS:
        board = board.apply_action(action)
    return board


def test_transistor_bridge_flags_as_complete():
    """The bridge circuit passes validation and generates correct netlist with Q prefix."""
    board = _build_transistor_bridge()
    summary = board.get_connectivity_summary()

    assert board.is_complete_and_valid()
    assert summary["touches_vdd"] and summary["touches_vss"]
    assert summary["reachable_vout"] and summary["all_components_reachable"]
    assert summary["vin_on_power_rail"] is False

    netlist = board.to_netlist()
    assert netlist is not None
    # Check for correct Q prefix (not P prefix)
    assert "Q1 0 n0 VDD" in netlist, "PNP should use Q1, not P1"
    assert "Q2 n4 n5 0" in netlist, "NPN should use Q2, not N1"
    assert ".print ac v(n4)" in netlist


def test_transistor_bridge_spice_succeeds_but_trivial_reward():
    """
    After fixing BJT prefix (Q instead of P/N), SPICE simulation succeeds.
    However, the circuit is electrically broken (floating NPN base), so output
    is all zeros and reward is trivial (10.0 points).
    """
    board = _build_transistor_bridge()

    netlist = board.to_netlist()
    freq, vout = run_ac_simulation(netlist)

    # SPICE should now succeed (Q prefix fix)
    assert freq is not None, "SPICE simulation should succeed"
    assert vout is not None, "SPICE simulation should return voltage data"
    assert len(freq) == 601, "Should have 601 frequency points"

    # But output should be all zeros (floating base issue)
    import numpy as np
    assert np.all(np.abs(vout) < 1e-6), "Output should be zero (broken circuit)"

    mcts = MCTS(board)
    stats = CircuitStatistics()
    reward = mcts._evaluate_circuit(board, stats)

    # Reward floor for completed circuits sits slightly above incomplete cap
    expected_reward = 45.0 + 2  # baseline + component count
    assert reward == expected_reward, f"Expected completion floor reward {expected_reward}, got {reward}"
    assert stats.spice_success_count == 1, "SPICE should succeed"
    assert stats.spice_fail_count == 0, "SPICE should not fail"
