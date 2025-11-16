"""
Breadboard augmentation utilities for reducing MCTS search space.

The breadboard has vertical translation symmetry: circuits with identical topology
but different vertical positions are electrically equivalent. This module provides
functions to:
1. Normalize circuits to canonical form
2. Generate all symmetric variants
3. Enable reward sharing across equivalent states

This module follows SOLID principles:
- Single Responsibility: Each function has one clear purpose
- Open/Closed: Functions can be extended without modification
- Liskov Substitution: All functions work with Breadboard interface
- Interface Segregation: Functions have minimal, focused interfaces
- Dependency Inversion: Functions depend on abstractions (Breadboard), not implementations
"""

from typing import List, Dict, Set, Tuple, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.topology_game_board import Breadboard, Component, RowPinIndex


def get_min_max_rows(board: Breadboard) -> Tuple[int, int]:
    """
    Find the minimum and maximum row indices used by components (excluding fixed VIN/VOUT).

    Returns:
        (min_row, max_row): Range of rows occupied by the circuit
    """
    if not board.placed_components:
        return (board.WORK_START_ROW, board.WORK_END_ROW)

    min_row = board.ROWS
    max_row = 0

    for comp in board.placed_components:
        # Skip VIN and VOUT components as they are fixed
        if comp.type in ['vin', 'vout']:
            continue

        for row, col in comp.pins:
            # For wires, skip endpoints that are at VIN/VOUT positions
            if comp.type == 'wire':
                if row == board.VIN_ROW or row == board.VOUT_ROW:
                    continue

            # Only consider rows in the work area
            if board.WORK_START_ROW <= row <= board.WORK_END_ROW:
                min_row = min(min_row, row)
                max_row = max(max_row, row)

    # If no components in work area, return work area bounds
    if min_row == board.ROWS or max_row == 0:
        return (board.WORK_START_ROW, board.WORK_END_ROW)

    return (min_row, max_row)


def translate_vertically(board: Breadboard, row_offset: int) -> Optional[Breadboard]:
    """
    Create a new board with all components shifted vertically by row_offset.

    Args:
        board: Source breadboard
        row_offset: Number of rows to shift (positive = down, negative = up)

    Returns:
        New translated board, or None if translation would go out of bounds
    """
    # Create a fresh board without pre-placed VIN/VOUT
    new_board = Breadboard.__new__(Breadboard)
    new_board.ROWS = board.ROWS
    new_board.COLUMNS = 1
    new_board.VSS_ROW = board.VSS_ROW
    new_board.VDD_ROW = board.VDD_ROW
    new_board.VIN_ROW = board.VIN_ROW
    new_board.VOUT_ROW = board.VOUT_ROW
    new_board.WORK_START_ROW = board.WORK_START_ROW
    new_board.WORK_END_ROW = board.WORK_END_ROW
    new_board.row_pin_index = RowPinIndex(board.ROWS)
    new_board.placed_components = []
    new_board.component_counter = 0
    new_board.vin_placed = False
    new_board.vout_placed = False
    new_board.uf_parent = list(range(board.ROWS))
    new_board.active_nets = {new_board.find(board.VSS_ROW), new_board.find(board.VDD_ROW)}
    new_board.placed_wires = set()

    # Translate and place each component
    # Process VIN/VOUT first to ensure they're placed before wires
    for comp in board.placed_components:
        if comp.type in ['vin', 'vout']:
            new_board._place_component(comp.type, comp.pins[0][0])
            if comp.type == 'vin':
                new_board.vin_placed = True
            elif comp.type == 'vout':
                new_board.vout_placed = True

    # Then process non-wire components
    for comp in board.placed_components:
        if comp.type not in ['vin', 'vout', 'wire']:
            new_pins = [(r + row_offset, 0) for r, _ in comp.pins]

            if any(not (0 <= r < board.ROWS) for r, _ in new_pins):
                return None  # Translation out of bounds

            new_board._place_component(comp.type, new_pins[0][0])

    # Finally process wires
    for comp in board.placed_components:
        if comp.type == 'wire':
            new_pins = []
            for r, _ in comp.pins:
                if r in [board.VIN_ROW, board.VOUT_ROW, board.VSS_ROW, board.VDD_ROW]:
                    new_pins.append((r, 0))
                else:
                    new_pins.append((r + row_offset, 0))

            if any(not (0 <= r < board.ROWS) for r, _ in new_pins):
                return None  # Translation out of bounds

            new_board._place_wire(new_pins[0][0], new_pins[1][0])

    return new_board


def get_canonical_form(board: Breadboard) -> Breadboard:
    """
    Normalize a breadboard to its canonical form by shifting to the topmost valid position.

    The canonical form is the vertically-shifted variant where the circuit
    occupies the smallest row indices while keeping VIN/VOUT in the work area.

    Args:
        board: Input breadboard

    Returns:
        Canonicalized board (shifted to topmost position)
    """
    # Find current circuit bounds
    min_row, max_row = get_min_max_rows(board)

    # Calculate maximum upward shift while keeping circuit in bounds
    # Need to ensure VIN (at min_row potentially) stays >= WORK_START_ROW
    max_upward_shift = min_row - board.WORK_START_ROW

    if max_upward_shift <= 0:
        # Already at topmost position
        return board.clone()

    # Try to shift up by max_upward_shift
    canonical = translate_vertically(board, -max_upward_shift)

    if canonical is None:
        # Couldn't shift (edge case), return clone
        return board.clone()

    return canonical


def canonical_hash(board: Breadboard) -> int:
    """
    Compute hash of the canonical form for consistent state identification.

    This allows MCTS to recognize equivalent circuits regardless of vertical position.

    Args:
        board: Input breadboard

    Returns:
        Hash value of canonical form
    """
    canonical = get_canonical_form(board)
    return hash(canonical)


def generate_translations(board: Breadboard) -> List[Breadboard]:
    """
    Generate all valid vertical translations of the given board.

    This creates all electrically equivalent circuits by shifting the entire
    circuit up and down while staying within valid bounds.

    Args:
        board: Input breadboard

    Returns:
        List of all valid translated boards (including original position)
    """
    translations = []
    min_row, max_row = get_min_max_rows(board)

    # Calculate valid translation range
    # Maximum upward shift: move min_row to WORK_START_ROW
    max_up = min_row - board.WORK_START_ROW
    # Maximum downward shift: move max_row to WORK_END_ROW
    max_down = board.WORK_END_ROW - max_row

    # Generate all translations in valid range
    for offset in range(-max_up, max_down + 1):
        translated = translate_vertically(board, offset)
        if translated is not None:
            translations.append(translated)

    return translations


def augment_board_set(boards_with_rewards: Dict[Breadboard, float]) -> Dict[Breadboard, float]:
    """
    Augment a set of boards with their symmetric variants, propagating rewards.

    This function takes boards with known rewards and generates all vertical
    translations, assigning the same reward to all symmetric variants.
    Deduplicates by canonical form.

    Args:
        boards_with_rewards: Dict mapping boards to their rewards

    Returns:
        Expanded dict with all symmetric variants (deduplicated)
    """
    augmented = {}
    canonical_to_reward = {}

    for board, reward in boards_with_rewards.items():
        # Get canonical form for deduplication
        canon_hash = canonical_hash(board)

        # If we've seen this canonical form, keep the better reward
        if canon_hash in canonical_to_reward:
            canonical_to_reward[canon_hash] = max(canonical_to_reward[canon_hash], reward)
        else:
            canonical_to_reward[canon_hash] = reward

        # Generate all translations
        translations = generate_translations(board)
        for trans_board in translations:
            trans_canon_hash = canonical_hash(trans_board)
            # Use the reward from canonical form
            reward_to_use = canonical_to_reward.get(trans_canon_hash, reward)

            # Add if not already present or if this has better reward
            existing_reward = augmented.get(trans_board, float('-inf'))
            if reward_to_use > existing_reward:
                augmented[trans_board] = reward_to_use

    return augmented


def count_unique_topologies(boards: List[Breadboard]) -> int:
    """
    Count the number of unique circuit topologies in a list of boards.

    Uses canonical form to identify boards that are just vertical translations
    of the same circuit.

    Args:
        boards: List of breadboards

    Returns:
        Number of unique topologies (ignoring vertical position)
    """
    canonical_hashes = set()
    for board in boards:
        canonical_hashes.add(canonical_hash(board))
    return len(canonical_hashes)


def deduplicate_boards(boards: List[Breadboard]) -> List[Breadboard]:
    """
    Remove duplicate boards based on canonical form.

    Returns one representative from each equivalence class of vertically
    translated circuits (specifically, the canonical form).

    Args:
        boards: List of breadboards (may contain duplicates)

    Returns:
        List of unique canonical boards
    """
    seen_canonical = set()
    unique_boards = []

    for board in boards:
        canon = get_canonical_form(board)
        canon_hash = hash(canon)

        if canon_hash not in seen_canonical:
            seen_canonical.add(canon_hash)
            unique_boards.append(canon)

    return unique_boards
