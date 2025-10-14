from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set
import copy

# ============================================================
# Component Metadata (Unchanged)
# ============================================================
@dataclass(frozen=True)
class ComponentInfo:
    pin_count: int
    vertical_only: bool
    pin_names: List[str] = field(default_factory=list)
    can_place_multiple: bool = True

COMPONENT_CATALOG: Dict[str, ComponentInfo] = {
    'resistor': ComponentInfo(2, True, pin_names=['p1', 'p2']),
    'capacitor': ComponentInfo(2, True, pin_names=['p1', 'p2']),
    'inductor': ComponentInfo(2, True, pin_names=['p1', 'p2']),
    'diode': ComponentInfo(2, True, pin_names=['anode', 'cathode']),
    'nmos3': ComponentInfo(3, True, pin_names=['drain', 'gate', 'source']),
    'pmos3': ComponentInfo(3, True, pin_names=['drain', 'gate', 'source']),
    'npn': ComponentInfo(3, True, pin_names=['collector', 'base', 'emitter']),
    'pnp': ComponentInfo(3, True, pin_names=['collector', 'base', 'emitter']),
    'vin': ComponentInfo(1, True, pin_names=['signal'], can_place_multiple=False),
    'vout': ComponentInfo(1, True, pin_names=['signal'], can_place_multiple=False),
    'wire': ComponentInfo(2, False, pin_names=['p1', 'p2']),
}

# ============================================================
# Node and Component Models (Unchanged)
# ============================================================
class NodeType(Enum):
    NORMAL = auto()
    VDD = auto()
    VSS = auto()

@dataclass
class Component:
    type: str
    pins: List[Tuple[int, int]]
    id: int = 0

# ============================================================
# Breadboard Class
# ============================================================
class Breadboard:
    ROWS = 30
    COLUMNS = 8
    VSS_ROW = 0
    VDD_ROW = 29
    WORK_START_ROW = 1
    WORK_END_ROW = 28

    def __init__(self):
        self.grid: List[List[Optional[Tuple['Component', int]]]] = [
            [None for _ in range(self.COLUMNS)] for _ in range(self.ROWS)
        ]
        self.placed_components: List[Component] = []
        self.component_counter = 0
        self.vin_placed = False
        self.vout_placed = False
        self.uf_parent: List[int] = list(range(self.ROWS))
        self.active_nets: Set[int] = {self.find(self.VSS_ROW), self.find(self.VDD_ROW)}
        self.placed_wires: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
        self._place_component('vin', 5, 0)
        self._place_component('vout', 20, 0)

    def find(self, row: int) -> int:
        if self.uf_parent[row] != row:
            self.uf_parent[row] = self.find(self.uf_parent[row])
        return self.uf_parent[row]

    def union(self, row1: int, row2: int):
        root1 = self.find(row1)
        root2 = self.find(row2)
        if root1 != root2:
            # Merge roots and maintain active_nets consistency
            if root1 in self.active_nets and root2 in self.active_nets:
                # Both active: merge root2 into root1, remove stale root2
                self.uf_parent[root2] = root1
                self.active_nets.discard(root2)
            elif root1 in self.active_nets:
                # Only root1 active: make root1 the parent
                self.uf_parent[root2] = root1
            elif root2 in self.active_nets:
                # Only root2 active: make root2 the parent
                self.uf_parent[root1] = root2
            else:
                # Neither active: arbitrary choice
                self.uf_parent[root2] = root1

    def is_empty(self, row: int, col: int) -> bool:
        return 0 <= row < self.ROWS and 0 <= col < self.COLUMNS and self.grid[row][col] is None

    def is_row_active(self, row: int) -> bool:
        return self.find(row) in self.active_nets

    def can_place_component(self, comp_type: str, start_row: int, col: int) -> bool:
        info = COMPONENT_CATALOG.get(comp_type)
        if not info or comp_type == 'wire': return False
        if not info.can_place_multiple and getattr(self, f"{comp_type}_placed", False):
            return False
        pin_rows = range(start_row, start_row + info.pin_count)
        if not (self.WORK_START_ROW <= pin_rows.start and pin_rows.stop - 1 <= self.WORK_END_ROW):
            return False
        if not all(self.is_empty(r, col) for r in pin_rows):
            return False
        if info.pin_count == 1:
            return not self.is_row_active(start_row)
        return any(self.is_row_active(r) for r in pin_rows)

    def can_place_wire(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        if r1 == r2: return False
        # Check bounds
        if not (0 <= r1 < self.ROWS and 0 <= c1 < self.COLUMNS):
            return False
        if not (0 <= r2 < self.ROWS and 0 <= c2 < self.COLUMNS):
            return False
        # Check for duplicate wire
        wire_key = tuple(sorted(((r1, c1), (r2, c2))))
        if wire_key in self.placed_wires: return False
        # At least one endpoint must be on an active net
        return self.is_row_active(r1) or self.is_row_active(r2)

    def is_complete_and_valid(self) -> bool:
        if not (self.vin_placed and self.vout_placed): return False
        vin_row = next((c.pins[0][0] for c in self.placed_components if c.type == 'vin'), -1)
        vout_row = next((c.pins[0][0] for c in self.placed_components if c.type == 'vout'), -1)
        return vin_row != -1 and self.find(vin_row) == self.find(vout_row)

    def apply_action(self, action: Tuple) -> "Breadboard":
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
        actions: List[Tuple] = []
        target_col = next((c for c in range(self.COLUMNS) if not all(
            not self.is_empty(r, c) for r in range(self.WORK_START_ROW, self.WORK_END_ROW + 1)
        )), -1)
        if target_col == -1:
            if self.is_complete_and_valid(): actions.append(("STOP",))
            return actions
        for comp_type, info in COMPONENT_CATALOG.items():
            if comp_type == 'wire': continue
            max_start = self.WORK_END_ROW - (info.pin_count - 1)
            for r in range(self.WORK_START_ROW, max_start + 1):
                if self.can_place_component(comp_type, r, target_col):
                    actions.append((comp_type, r, target_col))
        source_points = {(r, c) for c in range(target_col + 1) for r in range(self.ROWS) if self.is_row_active(r)}
        target_points = {(r, c) for c in range(target_col + 1) for r in range(self.ROWS)}
        for r1, c1 in source_points:
            for r2, c2 in target_points:
                if (r1, c1) >= (r2, c2): continue
                if self.can_place_wire(r1, c1, r2, c2):
                    actions.append(("wire", r1, c1, r2, c2))
        if self.is_complete_and_valid():
            actions.append(("STOP",))
        return actions

    def get_reward(self) -> float:
        if not self.is_complete_and_valid():
            return 0.0
        comp_count = sum(1 for c in self.placed_components if c.type not in ['wire', 'vin', 'vout'])
        wire_count = sum(1 for c in self.placed_components if c.type == 'wire')
        unique_types = len({c.type for c in self.placed_components if c.type not in ['wire', 'vin', 'vout']})
        return (comp_count * 10.0) + (unique_types * 5.0) - (wire_count * 1.0)
    
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

        # Occupy grid and activate nets for all pins
        for i, (r, c) in enumerate(component.pins):
            self.grid[r][c] = (component, i)
            self.active_nets.add(self.find(r))

        if comp_type in ['vin', 'vout']: setattr(self, f"{comp_type}_placed", True)
        return component

    def _place_wire(self, r1: int, c1: int, r2: int, c2: int) -> Optional[Component]:
        self.placed_wires.add(tuple(sorted(((r1, c1), (r2, c2)))))
        self.union(r1, r2)
        self.component_counter += 1
        component = Component(type="wire", pins=[(r1, c1), (r2, c2)], id=self.component_counter)
        self.placed_components.append(component)
        self.active_nets.add(self.find(r1))
        return component

    def clone(self) -> "Breadboard":
        new_board = self.__class__.__new__(self.__class__)
        new_board.grid = copy.deepcopy(self.grid)
        new_board.placed_components = copy.deepcopy(self.placed_components)
        new_board.component_counter = self.component_counter
        new_board.vin_placed = self.vin_placed
        new_board.vout_placed = self.vout_placed
        new_board.uf_parent = self.uf_parent[:]
        new_board.active_nets = self.active_nets.copy()
        new_board.placed_wires = self.placed_wires.copy()
        return new_board
        
    def __hash__(self) -> int:
        component_tuple = tuple(sorted(
            (c.type, tuple(sorted(c.pins))) for c in self.placed_components
        ))
        return hash(component_tuple)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Breadboard) and hash(self) == hash(other)
    
# ============================================================
# Checks and Tests (Unchanged)
# ============================================================
def run_tests():
    """
    Runs a series of checks to validate the Breadboard logic.
    """
    print("🔬 Running tests for Breadboard environment...")
    
    # --- Test 1: Initial State ---
    print("\n--- Test 1: Initial State ---")
    b0 = Breadboard()
    assert b0.vin_placed and b0.vout_placed
    assert len(b0.placed_components) == 2
    assert b0.is_row_active(5)
    assert b0.is_row_active(20)
    assert not b0.is_row_active(10)
    print("✅ Passed: Initial state is correct.")

    # --- Test 2: Component Placement Rules ---
    print("\n--- Test 2: Component Placement Rules ---")
    assert not b0.can_place_component('vin', 10, 1)
    assert not b0.can_place_component('resistor', 5, 0)
    assert b0.can_place_component('resistor', 5, 1)
    assert not b0.can_place_component('resistor', 10, 1)
    print("✅ Passed: Component placement rules are enforced.")

    # --- Test 3: Wiring Rules and State Immutability ---
    print("\n--- Test 3: Wiring Rules & State Immutability ---")
    b1 = b0.apply_action(('resistor', 5, 1))
    # Resistor is on rows 5-6, both should be active (but not auto-unioned)
    assert b1.is_row_active(5) and b1.is_row_active(6)
    assert len(b0.placed_components) == 2  # Original board unchanged
    assert not b0.is_row_active(6)  # Original board unchanged
    b2 = b1.apply_action(('wire', 6, 1, 10, 1))
    assert b2.find(6) == b2.find(10)  # Wire unions rows 6 and 10
    assert b2.is_row_active(10)
    print("✅ Passed: Wiring rules and state immutability are correct.")

    # --- Test 4: Circuit Completion and Reward ---
    print("\n--- Test 4: Circuit Completion and Reward ---")
    assert not b2.is_complete_and_valid()
    assert b2.get_reward() == 0.0
    # Now need to wire the resistor pins together (5 and 6) to create a connection
    b3 = b2.apply_action(('wire', 5, 0, 6, 1))
    # Then connect to vout at row 20
    b4 = b3.apply_action(('wire', 10, 1, 20, 0))
    assert b4.is_complete_and_valid(), "Circuit should be complete after connecting VIN and VOUT nets."
    assert b4.get_reward() > 0.0
    print("✅ Passed: Circuit completion and reward logic are working.")

    print("\n🎉 All simple checks passed!")

if __name__ == "__main__":
    run_tests()