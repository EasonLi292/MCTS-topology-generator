#!/usr/bin/env python3
"""Wire validation checks for the row-only model."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from topology_game_board import Breadboard


def test_same_row_wire_rejected():
    b = Breadboard()
    work_row = b.WORK_START_ROW
    assert not b.can_place_wire(work_row, work_row)


def test_forbidden_pairs():
    b = Breadboard()
    assert not b.can_place_wire(b.VIN_ROW, b.VSS_ROW)
    assert not b.can_place_wire(b.VOUT_ROW, b.VDD_ROW)


def test_duplicate_wire_detection():
    b = Breadboard()
    r1 = b.WORK_START_ROW
    r2 = r1 + 1
    b = b.apply_action(('wire', r1, r2))
    assert not b.can_place_wire(r1, r2)
    assert not b.can_place_wire(r2, r1)


def test_inactive_net_wire_blocked():
    b = Breadboard()
    r1 = b.WORK_START_ROW
    r2 = r1 + 1
    assert not b.is_row_active(r1)
    assert not b.is_row_active(r2)
    assert not b.can_place_wire(r1, r2)


def test_wire_requires_active_endpoint():
    b = Breadboard()
    r1 = b.WORK_START_ROW
    assert b.can_place_wire(b.VIN_ROW, r1)
