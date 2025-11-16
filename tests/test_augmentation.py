#!/usr/bin/env python3
"""
Row-only augmentation sanity checks.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.topology_game_board import Breadboard
from utils.augmentation import (
    get_min_max_rows,
    translate_vertically,
    get_canonical_form,
    canonical_hash,
    generate_translations,
    augment_board_set,
    count_unique_topologies,
    deduplicate_boards
)


def build_simple_board() -> Breadboard:
    b = Breadboard()
    r = b.WORK_START_ROW + 2
    b = b.apply_action(("resistor", r))
    b = b.apply_action(("wire", b.VIN_ROW, r))
    b = b.apply_action(("wire", r + 1, b.VOUT_ROW))
    return b


def test_basic_translation():
    b0 = build_simple_board()
    _, max_row = get_min_max_rows(b0)
    offset = min(2, b0.WORK_END_ROW - max_row)
    b1 = translate_vertically(b0, offset)
    assert b1 is not None
    assert len(b0.placed_components) == len(b1.placed_components)


def test_canonical_form():
    boards = []
    for off in [0, 2, 4]:
        b = Breadboard()
        r = b.WORK_START_ROW + 2 + off
        b = b.apply_action(("resistor", r))
        b = b.apply_action(("wire", b.VIN_ROW, r))
        b = b.apply_action(("wire", r + 1, b.VOUT_ROW))
        boards.append(b)

    hashes = [canonical_hash(b) for b in boards]
    assert len(hashes) == len(boards)
    for b in boards:
        get_canonical_form(b)


def test_generate_translations():
    b0 = build_simple_board()
    translations = generate_translations(b0)
    assert translations
    for t in translations:
        assert isinstance(t, Breadboard)


def test_augment_board_set():
    b1 = build_simple_board()
    b2 = build_simple_board().apply_action(("wire", b1.WORK_START_ROW, b1.WORK_START_ROW + 5))
    boards_with_rewards = {b1: 10.0, b2: 20.0}
    augmented = augment_board_set(boards_with_rewards)
    assert len(augmented) >= len(boards_with_rewards)


def test_count_and_dedup():
    b1 = build_simple_board()
    b2 = build_simple_board()
    boards = [b1, b2]
    uniq = count_unique_topologies(boards)
    deduped = deduplicate_boards(boards)
    assert uniq >= 1
    assert len(deduped) <= len(boards)
