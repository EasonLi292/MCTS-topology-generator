"""Validation helpers for analyzing circuit topologies before simulation."""

from typing import List

# Use an absolute import to avoid issues with relative paths when the
# ``utils`` module is imported without package context.
from core.topology_game_board import Breadboard, Component

def validate_placement(breadboard: Breadboard, component: Component) -> bool:
    """Fast pre-simulation checks (e.g., no floating gates)."""
    # Check Kirchhoff's laws, shorts, etc.
    ...

def has_floating_nodes(breadboard: Breadboard) -> bool: ...