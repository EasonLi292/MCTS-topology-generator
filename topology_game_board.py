from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# ============================================================
# Component Metadata
# ============================================================

@dataclass(frozen=True)
class ComponentInfo:
    """Describes a component's pin count and placement rules."""
    pin_count: int
    vertical_only: bool

# Registry of available components and their constraints
COMPONENT_CATALOG: Dict[str, ComponentInfo] = {
    'pmos4':    ComponentInfo(4, True),
    'nmos4':    ComponentInfo(4, True),
    'npn':      ComponentInfo(3, True),
    'pnp':      ComponentInfo(3, True),
    'resistor': ComponentInfo(2, True),
    'capacitor':ComponentInfo(2, True),
    'inductor': ComponentInfo(2, True),
    'diode':    ComponentInfo(2, True),
    'wire':     ComponentInfo(2, True),
    'Vin':      ComponentInfo(1, False),
    'Vout':     ComponentInfo(1, False),
}

# ============================================================
# Node Model (Rows act as nets)
# ============================================================

class NodeType(Enum):
    """Types of voltage levels on the board."""
    NORMAL = auto()
    VDD = auto()
    VSS = auto()

@dataclass
class Node:
    """Represents an electrical node shared across a row."""
    row_index: int
    node_type: NodeType = NodeType.NORMAL
    connected_pins: List[Tuple["Component", int]] = field(default_factory=list)

# ============================================================
# Component Placement
# ============================================================

@dataclass
class Component:
    """Represents a placed component with pin positions."""
    type: str  # e.g. 'resistor'
    pins: List[Tuple[int, int]]  # List of (row, column) pin positions

# ============================================================
# Breadboard Definition
# ============================================================

class Breadboard:
    """Simulates a 50×12 breadboard and manages component placement."""

    ROWS = 50
    COLUMNS = 12

    def __init__(self):
        self.grid: List[List[Optional[Tuple[Component, int]]]] = [
            [None for _ in range(self.COLUMNS)] for _ in range(self.ROWS)
        ]
        self.nodes: List[Node] = [
            Node(row_index=0, node_type=NodeType.VDD)
        ] + [
            Node(row_index=r) for r in range(1, self.ROWS - 1)
        ] + [
            Node(row_index=self.ROWS - 1, node_type=NodeType.VSS)
        ]
        self.placed_components: List[Component] = []

    # --------------------------------------------------------
    # Utility Methods
    # --------------------------------------------------------

    def is_empty(self, row: int, col: int) -> bool:
        """Returns True if the position at (row, col) is unoccupied."""
        return self.grid[row][col] is None

    def get_node(self, row: int) -> Node:
        """Returns the node object for a specific row."""
        return self.nodes[row]

    # --------------------------------------------------------
    # Main API: Place Component
    # --------------------------------------------------------

    def place_component(
        self,
        component_type: str,
        start_row: int,
        column: int
    ) -> Optional[Component]:
        """
        Attempts to place a component starting at (start_row, column).
        Returns the Component instance on success, or None on failure.
        """
        if component_type not in COMPONENT_CATALOG:
            raise ValueError(f"Unknown component type: {component_type}")

        info = COMPONENT_CATALOG[component_type]

        # Vertical placement for multi-pin parts
        if info.vertical_only:
            end_row = start_row + info.pin_count - 1
            if end_row >= self.ROWS:
                return None  # Out of vertical bounds

            # Check for space
            if any(not self.is_empty(r, column) for r in range(start_row, end_row + 1)):
                return None  # Collision

            pin_positions = [(r, column) for r in range(start_row, end_row + 1)]

        # Single-pin components (Vin/Vout) can go anywhere
        else:
            if not self.is_empty(start_row, column):
                return None
            pin_positions = [(start_row, column)]

        # Place component
        component = Component(type=component_type, pins=pin_positions)
        self.placed_components.append(component)

        for pin_index, (r, c) in enumerate(pin_positions):
            self.grid[r][c] = (component, pin_index)
            self.get_node(r).connected_pins.append((component, pin_index))

        return component

# ============================================================
# Demo: Try a few placements
# ============================================================

if __name__ == "__main__":
    board = Breadboard()

    # Try placing a resistor vertically in column 3, rows 10-11
    resistor = board.place_component("resistor", start_row=10, column=3)
    print("Resistor placed:", resistor is not None)

    # Try placing a Vin at row 25, column 0
    vin = board.place_component("Vin", start_row=25, column=0)
    print("Vin placed:", vin is not None)

    # Attempt overlapping placement (should fail)
    overlap = board.place_component("nmos4", start_row=10, column=3)
    print("Overlapping NMOS placed:", overlap is not None)
