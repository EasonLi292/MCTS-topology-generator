from typing import List
from ..core.topology_game_board import Breadboard, Component

def validate_placement(breadboard: Breadboard, component: Component) -> bool:
    """Fast pre-simulation checks (e.g., no floating gates)."""
    # Check Kirchhoff's laws, shorts, etc.
    ...

def has_floating_nodes(breadboard: Breadboard) -> bool: ...