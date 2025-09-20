import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set

# ============================================================
# NOTE: Keep your original ComponentInfo, COMPONENT_CATALOG,
# and Component dataclasses. They are not shown here for brevity.
# ============================================================
# (Your original ComponentInfo, Component, and COMPONENT_CATALOG code goes here)


# ============================================================
# Simplified Breadboard Class
# ============================================================

class Breadboard:
    """
    A simplified breadboard environment for circuit design.

    This class manages the state of the breadboard, including component placement
    and connectivity. It provides methods to get legal actions, apply them,
    and calculate a reward for the resulting state, making it suitable for MCTS.
    """
    # --- Constants ---
    ROWS = 30
    COLUMNS = 8
    VSS_ROW = 0
    VDD_ROW = 29
    WORK_START_ROW = 1
    WORK_END_ROW = 28

    def __init__(self):
        # Grid stores (Component, pin_index) for physically placed components.
        # Wires do not occupy the grid.
        self.grid: List[List[Optional[Tuple['Component', int]]]] = [
            [None for _ in range(self.COLUMNS)] for _ in range(self.ROWS)
        ]
        self.placed_components: List[Component] = []
        self.component_counter = 0

        # --- State Tracking ---
        self.vin_placed = False
        self.vout_placed = False
        
        # --- Connectivity (Union-Find) ---
        self.uf_parent: List[int] = list(range(self.ROWS))
        # A net is "active" if it's connected to a component or power rail.
        self.active_nets: Set[int] = {self.find(self.VSS_ROW), self.find(self.VDD_ROW)}

        # Track placed wires to prevent duplicates.
        self.placed_wires: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()

    ## ------------------------------------------------------------
    ## Connectivity and Rule Checking
    ## ------------------------------------------------------------

    def find(self, row: int) -> int:
        """Finds the root of the net for a given row with path compression."""
        if self.uf_parent[row] != row:
            self.uf_parent[row] = self.find(self.uf_parent[row])
        return self.uf_parent[row]

    def union(self, row1: int, row2: int):
        """Merges the nets of two rows."""
        root1 = self.find(row1)
        root2 = self.find(row2)
        if root1 != root2:
            # If one net is active and the other isn't, merge into the active one.
            if root1 in self.active_nets and root2 not in self.active_nets:
                self.uf_parent[root2] = root1
            else:
                self.uf_parent[root1] = root2
                if root1 in self.active_nets:
                    self.active_nets.add(root2) # Ensure the new root is marked active

    def is_empty(self, row: int, col: int) -> bool:
        """Checks if a grid position is physically unoccupied."""
        return 0 <= row < self.ROWS and 0 <= col < self.COLUMNS and self.grid[row][col] is None

    def is_row_active(self, row: int) -> bool:
        """Checks if a row is part of an active net."""
        return self.find(row) in self.active_nets

    def can_place_component(self, comp_type: str, start_row: int, col: int) -> bool:
        """Checks if a non-wire component can be placed at a given location."""
        info = COMPONENT_CATALOG.get(comp_type)
        if not info or comp_type == 'wire': return False

        # Rule: Prevent placing unique components (vin, vout) more than once.
        if not info.can_place_multiple and getattr(self, f"{comp_type}_placed", False):
            return False

        # Rule: Check if all pins fit on the board and in empty spots.
        pin_rows = range(start_row, start_row + info.pin_count)
        if not (self.WORK_START_ROW <= pin_rows.start and pin_rows.stop - 1 <= self.WORK_END_ROW):
            return False
        if not all(self.is_empty(r, col) for r in pin_rows):
            return False

        # Rule: Single-pin components must start a new net (be placed on an INACTIVE row).
        if info.pin_count == 1:
            return not self.is_row_active(start_row)
        
        # Rule: Multi-pin components must connect to at least one ACTIVE row.
        return any(self.is_row_active(r) for r in pin_rows)

    def can_place_wire(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        """Checks if a wire can be placed between two points."""
        if r1 == r2: return False # No wires within the same row.
        
        # Rule: No duplicate wires.
        wire_key = tuple(sorted(((r1, c1), (r2, c2))))
        if wire_key in self.placed_wires: return False
            
        # Rule: Prevents creating isolated, floating wires. At least one end must be active.
        return self.is_row_active(r1) or self.is_row_active(r2)

    def is_complete_and_valid(self) -> bool:
        """Checks if the circuit is complete: VIN and VOUT are placed and connected."""
        if not (self.vin_placed and self.vout_placed): return False
        
        vin_row = next((c.pins[0][0] for c in self.placed_components if c.type == 'vin'), -1)
        vout_row = next((c.pins[0][0] for c in self.placed_components if c.type == 'vout'), -1)
        
        return vin_row != -1 and self.find(vin_row) == self.find(vout_row)

    ## ------------------------------------------------------------
    ## Action Generation and Application
    ## ------------------------------------------------------------

    def apply_action(self, action: Tuple) -> "Breadboard":
        """
        Applies an action by returning a new board state.
        This non-mutating approach is safer for search algorithms.
        """
        new_board = self.clone()
        action_type = action[0]

        if action_type == "STOP":
            return new_board

        success = False
        if action_type == "wire":
            _, r1, c1, r2, c2 = action
            success = new_board._place_wire(r1, c1, r2, c2) is not None
        else:
            comp_type, start_row, col = action
            success = new_board._place_component(comp_type, start_row, col) is not None
        
        if not success:
            raise ValueError(f"Invalid action applied: {action}")
        return new_board

    def legal_actions(self) -> List[Tuple]:
        """Generates all valid actions from the current state."""
        actions: List[Tuple] = []

        # Strategy: Build left-to-right. Find the first column that isn't full.
        target_col = next((c for c in range(self.COLUMNS) if not all(
            not self.is_empty(r, c) for r in range(self.WORK_START_ROW, self.WORK_END_ROW + 1)
        )), -1)

        if target_col == -1: # Board is full
            if self.is_complete_and_valid(): actions.append(("STOP",))
            return actions

        # 1. Component Placement Actions
        for comp_type, info in COMPONENT_CATALOG.items():
            if comp_type == 'wire': continue
            max_start = self.WORK_END_ROW - (info.pin_count - 1)
            for r in range(self.WORK_START_ROW, max_start + 1):
                if self.can_place_component(comp_type, r, target_col):
                    actions.append((comp_type, r, target_col))

        # 2. Wire Placement Actions
        # Sources are any active points (component pins or rails).
        source_points = {(r, c) for c in range(target_col + 1) for r in range(self.ROWS) if self.is_row_active(r)}
        # Targets can be any point in the buildable area.
        target_points = {(r, c) for c in range(target_col + 1) for r in range(self.ROWS)}
        
        for r1, c1 in source_points:
            for r2, c2 in target_points:
                if (r1, c1) >= (r2, c2): continue # Avoid duplicates and self-loops
                if self.can_place_wire(r1, c1, r2, c2):
                    actions.append(("wire", r1, c1, r2, c2))

        # 3. STOP Action
        if self.is_complete_and_valid():
            actions.append(("STOP",))
            
        return actions

    def get_reward(self) -> float:
        """Calculates a reward for the current board state. Essential for MCTS."""
        if not self.is_complete_and_valid():
            return 0.0

        # Reward based on component count and variety, penalize wire length.
        comp_count = sum(1 for c in self.placed_components if c.type not in ['wire', 'vin', 'vout'])
        wire_count = sum(1 for c in self.placed_components if c.type == 'wire')
        unique_types = len({c.type for c in self.placed_components if c.type not in ['wire', 'vin', 'vout']})
        
        return (comp_count * 10.0) + (unique_types * 5.0) - (wire_count * 1.0)

    ## ------------------------------------------------------------
    ## Private Helpers & Dunder Methods
    ## ------------------------------------------------------------
    
    def _place_component(self, comp_type: str, start_row: int, col: int) -> Optional[Component]:
        """(Internal) Mutates the board state by placing a component."""
        info = COMPONENT_CATALOG[comp_type]
        self.component_counter += 1
        component = Component(
            type=comp_type,
            pins=[(r, col) for r in range(start_row, start_row + info.pin_count)],
            id=self.component_counter
        )
        self.placed_components.append(component)

        for i, (r, c) in enumerate(component.pins):
            self.grid[r][c] = (component, i)
            self.active_nets.add(self.find(r))
        
        if comp_type in ['vin', 'vout']: setattr(self, f"{comp_type}_placed", True)
        return component

    def _place_wire(self, r1: int, c1: int, r2: int, c2: int) -> Optional[Component]:
        """(Internal) Mutates the board state by placing a wire."""
        self.placed_wires.add(tuple(sorted(((r1, c1), (r2, c2)))))
        self.union(r1, r2)
        
        self.component_counter += 1
        component = Component(type="wire", pins=[(r1, c1), (r2, c2)], id=self.component_counter)
        self.placed_components.append(component)
        
        self.active_nets.add(self.find(r1)) # Mark the newly merged net as active
        return component

    def clone(self) -> "Breadboard":
        """Creates a deep copy of the breadboard state for exploration."""
        new_board = self.__class__()
        new_board.grid = copy.deepcopy(self.grid)
        new_board.placed_components = copy.deepcopy(self.placed_components)
        new_board.placed_wires = self.placed_wires.copy()
        new_board.component_counter = self.component_counter
        new_board.vin_placed = self.vin_placed
        new_board.vout_placed = self.vout_placed
        new_board.uf_parent = self.uf_parent[:]
        new_board.active_nets = self.active_nets.copy()
        return new_board
        
    def __hash__(self) -> int:
        """Hashes the board state based on a canonical representation of components."""
        component_tuple = tuple(sorted(
            (c.type, tuple(sorted(c.pins))) for c in self.placed_components
        ))
        return hash(component_tuple)

    def __eq__(self, other: object) -> bool:
        """Checks for logical equality between two board states."""
        return isinstance(other, Breadboard) and hash(self) == hash(other)