"""
Breadboard simulation for circuit topology generation.

This module provides a virtual breadboard environment for placing electronic
components and wiring them together. It enforces electrical connectivity rules
and validates circuit topologies.

ROW-BASED CONNECTIVITY MODEL:
- Each row functions as a single electrical net (like a real breadboard)
- All columns in a row are electrically connected
- Union-find structure maintains one entry per row (not per cell)
- Components must be placed on active rows (rows connected to VIN/VOUT/power)
- Wires extend the active network by connecting entire rows

Refactored to follow SOLID principles with small, focused methods.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set
import copy


# ============================================================
# Component Metadata
# ============================================================
@dataclass(frozen=True)
class ComponentInfo:
    """
    Metadata for electronic components in the circuit topology generator.

    This dataclass defines the characteristics and placement rules for each
    component type that can be placed on the virtual breadboard.

    Attributes:
        pin_count (int): Number of pins the component has (e.g., 2 for resistor, 3 for transistor).
            **ACTIVELY USED** - Determines component size and placement validation.

        vertical_only (bool):
            All components are placed vertically in the current implementation.
            Wire placement uses separate logic in can_place_wire().
            Consider removing or implementing if horizontal placement is needed.

        pin_names (List[str]): 
            Symbolic names for each pin (e.g., ['drain', 'gate', 'source'] for MOSFETs).
            Could be used for enhanced netlist generation or validation.
            Consider removing if not needed, or document intended use case.

        can_place_multiple (bool): 
            If False, prevents placing more than one instance of this component type.
            Used for VIN and VOUT to ensure only one of each exists on the board.
            Default: True (most components can have multiple instances).

    Usage Notes:
        - Only pin_count and can_place_multiple are currently used in validation logic
        - vertical_only and pin_names are defined but never referenced in placement/netlist code
        - Future enhancements could leverage pin_names for polarity checking (diodes)
          or improved SPICE netlist labeling
    """
    pin_count: int
    vertical_only: bool  # RESERVED: Not currently enforced
    pin_names: List[str] = field(default_factory=list)  # RESERVED: Not currently used
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
# Node and Component Models
# ============================================================
class NodeType(Enum):
    NORMAL = auto()
    VDD = auto()
    VSS = auto()

@dataclass
class Component:
    type: str
    pins: List[int]  # List of row indices where component pins are placed
    id: int = 0


@dataclass
class PinRecord:
    component: Component
    pin_index: int


class RowPinIndex:
    """
    Tracks which pins exist on each row in the row-based connectivity model.

    Each row is a single electrical net, and this index tracks which component
    pins occupy each row.
    """

    def __init__(self, rows: int):
        self._rows: List[List[PinRecord]] = [[] for _ in range(rows)]

    def clone(self) -> "RowPinIndex":
        new_index = RowPinIndex(len(self._rows))
        new_index._rows = copy.deepcopy(self._rows)
        return new_index

    def is_empty(self, row: int) -> bool:
        return 0 <= row < len(self._rows) and len(self._rows[row]) == 0

    def place_pin(self, row: int, component: Component, pin_index: int):
        self._rows[row].append(PinRecord(component, pin_index))

    def get_pin(self, row: int) -> Optional[PinRecord]:
        if 0 <= row < len(self._rows) and self._rows[row]:
            # Return the first pin (all share the row net)
            return self._rows[row][0]
        return None

    def pins_in_row(self, row: int) -> List[PinRecord]:
        if 0 <= row < len(self._rows):
            return list(self._rows[row])
        return []

    def rows_view(self) -> Dict[int, List[Dict[str, object]]]:
        """
        Returns a lightweight mapping of rows to pin summaries.

        Used for debugging/introspection without exposing mutable structures.
        """
        view: Dict[int, List[Dict[str, object]]] = {}
        for row_idx, pins in enumerate(self._rows):
            if not pins:
                continue
            view[row_idx] = [
                {
                    "component": pin.component.type,
                    "component_id": pin.component.id,
                    "pin_index": pin.pin_index,
                }
                for pin in pins
            ]
        return view

# ============================================================
# Breadboard Class
# ============================================================
class Breadboard:
    DEFAULT_ROWS = 15
    MIN_ROWS = 6  # Need VIN, VOUT, power rails, and at least one work row
    MIN_ACTIVE_COMPONENTS = 2  # Non-wire components required for a valid circuit

    def __init__(self, rows: int = DEFAULT_ROWS):
        if rows < self.MIN_ROWS:
            raise ValueError(f"Breadboard requires at least {self.MIN_ROWS} rows (got {rows})")

        self.ROWS = rows
        self.COLUMNS = 1  # retained for legacy callers; no column semantics
        self.VSS_ROW = 0
        self.VDD_ROW = rows - 1
        self.VIN_ROW = 1
        self.VOUT_ROW = rows - 2
        self.WORK_START_ROW = 2
        self.WORK_END_ROW = rows - 3

        if self.WORK_END_ROW < self.WORK_START_ROW:
            raise ValueError("Breadboard needs at least one work row between VIN/VOUT and power rails")

        # Row-centric pin index (no columns in node model)
        self.row_pin_index = RowPinIndex(self.ROWS)
        self.placed_components: List[Component] = []
        self.component_counter = 0
        self.vin_placed = False
        self.vout_placed = False
        # ROW-BASED CONNECTIVITY MODEL (like a real breadboard):
        # - Each row is a single electrical net (all columns electrically connected)
        # - uf_parent has one entry per row (not per cell)
        # - Wiring between rows unions entire rows, not just specific cells
        # - When VIN is at (1, 0), all of row 1 is the VIN net
        self.uf_parent: List[int] = list(range(self.ROWS))
        # Initialize active nets with all special rows (power rails and I/O)
        self.active_nets: Set[int] = {
            self.find(self.VSS_ROW),
            self.find(self.VDD_ROW),
            self.find(self.VIN_ROW),
            self.find(self.VOUT_ROW)
        }
        self.placed_wires: Set[Tuple[int, int]] = set()
        # Place VIN and VOUT on dedicated reserved rows
        self._place_component('vin', self.VIN_ROW)
        self._place_component('vout', self.VOUT_ROW)

    def find(self, row: int) -> int:
        """Find the root net ID for a given row (union-find with path compression).

        Args:
            row: Row index (0 to ROWS-1)

        Returns:
            Root row ID representing the electrical net this row belongs to
        """
        if self.uf_parent[row] != row:
            self.uf_parent[row] = self.find(self.uf_parent[row])
        return self.uf_parent[row]

    def union(self, row1: int, row2: int):
        """Unite two rows into the same electrical net.

        This merges entire rows - all columns in row1 and row2 become part
        of the same electrical net. This is the core operation that implements
        row-based connectivity.

        Args:
            row1: First row to unite
            row2: Second row to unite
        """
        root1 = self.find(row1)
        root2 = self.find(row2)
        if root1 != root2:
            # Keep power rails as canonical roots when involved
            if root1 in {self.VDD_ROW, self.VSS_ROW}:
                self.uf_parent[root2] = root1
            elif root2 in {self.VDD_ROW, self.VSS_ROW}:
                self.uf_parent[root1] = root2
            elif root1 in self.active_nets and root2 in self.active_nets:
                self.uf_parent[root2] = root1
                self.active_nets.discard(root2)
            elif root1 in self.active_nets:
                self.uf_parent[root2] = root1
            elif root2 in self.active_nets:
                self.uf_parent[root1] = root2
            else:
                self.uf_parent[root2] = root1

    def is_empty(self, row: int) -> bool:
        return self.row_pin_index.is_empty(row)

    def is_row_active(self, row: int) -> bool:
        return self.find(row) in self.active_nets

    def get_pin_at(self, row: int) -> Optional["PinRecord"]:
        """Returns the pin record at a specific row, if any."""
        return self.row_pin_index.get_pin(row)

    def pins_in_row(self, row: int) -> List[PinRecord]:
        """Returns all pins that occupy a given row."""
        return self.row_pin_index.pins_in_row(row)

    def row_pin_summary(self) -> Dict[int, List[Dict[str, object]]]:
        """
        Lightweight view of pins per row.
        Helpful for debugging or for row-centric reasoning without columns.
        """
        return self.row_pin_index.rows_view()

    def can_place_component(self, comp_type: str, start_row: int) -> bool:
        info = COMPONENT_CATALOG.get(comp_type)
        if not info or comp_type == 'wire': return False
        if not info.can_place_multiple and getattr(self, f"{comp_type}_placed", False):
            return False
        pin_rows = range(start_row, start_row + info.pin_count)

        # Prevent components from having pins ON VIN/VOUT rows
        # Components can only be placed in the work area (rows 2-12 for 15-row board)
        # This keeps VIN/VOUT rows reserved for signal I/O only
        # Since entire rows are unified electrically, placing a component on VIN/VOUT row
        # would make that component's pins part of the I/O net (usually undesirable)
        min_allowed_row = self.WORK_START_ROW  # Start after VIN row
        max_allowed_row = self.WORK_END_ROW    # End before VOUT row
        if not (min_allowed_row <= pin_rows.start and pin_rows.stop - 1 <= max_allowed_row):
            return False

        # Node model allows multiple pins per row; we only check bounds
        if info.pin_count == 1:
            return not self.is_row_active(start_row)

        # Component can only be placed if at least one pin touches an active net
        # This ensures circuits are built by extending from active nets with wires first
        pins_touch_active = any(self.is_row_active(r) for r in pin_rows)
        if not pins_touch_active:
            return False

        # Prevent degenerate components: all pins must not be on the same net
        # A component with all pins on the same net is electrically useless
        pin_nets = {self.find(r) for r in pin_rows}
        if len(pin_nets) < 2:
            return False  # All pins would be on same net - degenerate component

        # Prevent duplicate component topologies: don't place same component type
        # across the same set of nets (e.g., two resistors both connecting n0 to n1)
        # This creates redundant parallel components that don't add topological diversity
        net_signature = tuple(sorted(pin_nets))
        for existing_comp in self.placed_components:
            if existing_comp.type == comp_type and existing_comp.type not in ['vin', 'vout', 'wire']:
                existing_nets = tuple(sorted({self.find(r) for r in existing_comp.pins}))
                if existing_nets == net_signature:
                    return False  # Same component type already spans these exact nets

        return True

    def can_place_wire(self, r1: int, r2: int) -> bool:
        """
        Checks if a wire can be legally placed between two rows.

        Args:
            r1: First endpoint row
            r2: Second endpoint row

        Returns:
            True if wire placement is valid
        """
        # Same row connections are not allowed
        if r1 == r2:
            return False

        # ROW-BASED CONNECTIVITY MODEL:
        # When VIN is placed at (VIN_ROW, 0), the entire VIN_ROW becomes the VIN net.
        # Wires can connect to any column in a row since all columns are electrically unified.
        # The union-find structure (uf_parent) maintains one entry per row, not per cell.

        # Forbidden row pairs - only forbid DIRECT wires between special I/O/power rows
        forbidden_row_pairs = [
            {self.VIN_ROW, self.VSS_ROW},
            {self.VOUT_ROW, self.VDD_ROW},
            {self.VSS_ROW, self.VOUT_ROW},
            {self.VIN_ROW, self.VOUT_ROW},
        ]
        endpoint_rows = {r1, r2}
        for pair in forbidden_row_pairs:
            if endpoint_rows == pair:
                return False

        # Check if rows are within bounds
        if not self._is_position_valid(r1) or not self._is_position_valid(r2):
            return False

        # Check for duplicate wire
        if self._is_duplicate_wire(r1, r2):
            return False

        # At least one endpoint must be on an active net
        if not (self.is_row_active(r1) or self.is_row_active(r2)):
            return False

        # Check gate/base pin connection rules
        if not self._validate_control_pin_wiring(r1, r2):
            return False

        return True

    def _is_mos_gate_cell(self, row: int) -> bool:
        if not self._is_position_valid(row):
            return False
        pin = self.row_pin_index.get_pin(row)
        if pin is None:
            return False
        component = pin.component
        pin_index = pin.pin_index
        return component.type in ['nmos3', 'pmos3'] and pin_index == 1

    def _is_position_valid(self, row: int) -> bool:
        """
        Checks if a row is within the breadboard bounds.

        Args:
            row: Row index

        Returns:
            True if row is valid
        """
        return 0 <= row < self.ROWS

    def _is_duplicate_wire(self, r1: int, r2: int) -> bool:
        """
        Checks if a wire already exists between two rows.

        Args:
            r1: First endpoint row
            r2: Second endpoint row

        Returns:
            True if this wire already exists
        """
        wire_key = tuple(sorted((r1, r2)))
        return wire_key in self.placed_wires

    def _validate_control_pin_wiring(self, r1: int, r2: int) -> bool:
        """
        Validates that gate/base pins are not directly connected to power rails.

        This prevents shorts and ensures proper circuit design.
        Gate pins (MOSFET) and base pins (BJT) should not be directly
        connected to VDD or VSS.

        Args:
            r1: First endpoint row
            r2: Second endpoint row

        Returns:
            True if wiring is valid
        """
        if self._row_has_gate_pin(r1) and self._is_power_rail(r2):
            return False
        if self._row_has_gate_pin(r2) and self._is_power_rail(r1):
            return False
        if self._row_has_base_pin(r1) and self._is_power_rail(r2):
            return False
        if self._row_has_base_pin(r2) and self._is_power_rail(r1):
            return False
        return True

    def _row_has_gate_pin(self, row: int) -> bool:
        return any(
            pin.component.type in ['nmos3', 'pmos3'] and pin.pin_index == 1
            for pin in self.row_pin_index.pins_in_row(row)
        )

    def _row_has_base_pin(self, row: int) -> bool:
        return any(
            pin.component.type in ['npn', 'pnp'] and pin.pin_index == 1
            for pin in self.row_pin_index.pins_in_row(row)
        )

    def _is_power_rail(self, row: int) -> bool:
        """
        Checks if a row is a power rail (VDD or VSS).

        Args:
            row: Row index to check

        Returns:
            True if row is VDD or VSS
        """
        return row == self.VDD_ROW or row == self.VSS_ROW

    def is_complete_and_valid(self) -> bool:
        """
        Checks if the circuit is complete and valid for simulation.

        Requirements:
        1. VIN and VOUT must be placed
        2. All components must be connected in a VIN-VOUT path through components
        3. Circuit must have at least MIN_ACTIVE_COMPONENTS (2) non-wire components
        4. Circuit must touch both power rails (VDD and VSS)
        5. Gate/Base pins must not be directly placed on VDD/VSS rows

        Returns:
            True if circuit meets all validity requirements
        """
        if not (self.vin_placed and self.vout_placed):
            return False

        # Check for floating components (also validates VIN-VOUT connection)
        if not self._all_components_connected():
            return False

        # Check gate/base pins are not connected to power rails
        if not self._validate_gate_base_connections():
            return False

        return True

    def _all_components_connected(self) -> bool:
        """
        Verify that all components form a valid circuit path from VIN to VOUT.

        This checks:
        - VIN can reach VOUT through component connections
        - All components are reachable from VIN (no floating components)
        - Circuit has minimum number of active components
        - Circuit touches both power rails (VDD and VSS)

        Uses the connectivity summary computed from the actual net mapping
        to ensure validation matches electrical connectivity.

        Returns:
            True if circuit forms a valid VIN-VOUT path meeting all requirements
        """
        summary = self._compute_connectivity_summary()
        return summary.get("valid", False)

    def _validate_gate_base_connections(self) -> bool:
        """
        Ensure gate (MOSFET) and base (BJT) pins are not directly placed on
        VDD or VSS power rail rows.

        This prevents direct shorts but allows gates/bases to be connected to
        power rails indirectly through other circuit components.

        Pin configuration:
        - MOSFET (nmos3/pmos3): pins[0]=drain, pins[1]=gate, pins[2]=source
        - BJT (npn/pnp): pins[0]=collector, pins[1]=base, pins[2]=emitter

        Returns:
            True if all gate/base pins are valid (not on VDD_ROW or VSS_ROW)
        """
        for comp in self.placed_components:
            # Check MOSFET gate pins
            if comp.type in ['nmos3', 'pmos3']:
                gate_row = comp.pins[1]  # Gate is second pin (index 1)
                # Gate cannot be placed directly on VDD or VSS rows
                if gate_row == self.VDD_ROW or gate_row == self.VSS_ROW:
                    return False

            # Check BJT base pins
            elif comp.type in ['npn', 'pnp']:
                base_row = comp.pins[1]  # Base is second pin (index 1)
                # Base cannot be placed directly on VDD or VSS rows
                if base_row == self.VDD_ROW or base_row == self.VSS_ROW:
                    return False

        return True

    def apply_action(self, action: Tuple) -> "Breadboard":
        new_board = self.clone()
        action_type = action[0]
        if action_type == "STOP":
            return new_board
        success = False
        if action_type == "wire":
            _, r1, r2 = action
            success = new_board._place_wire(r1, r2) is not None
        else:
            comp_type, start_row = action
            success = new_board._place_component(comp_type, start_row) is not None
        if not success:
            raise ValueError(f"Invalid action applied: {action}")
        return new_board

    def legal_actions(self) -> List[Tuple]:
        """
        Generates all legal actions (component placements and wires) from current state
        in the node model (rows only, no columns).

        Returns:
            List of action tuples:
            - Component placement: (comp_type, start_row)
            - Wire placement: ("wire", r1, r2)
            - Stop action: ("STOP",)
        """
        actions: List[Tuple] = []
        self._add_component_actions(actions, target_col=0)
        self._add_wire_actions(actions, target_col=0)
        self._add_stop_action_if_valid(actions)
        return actions

    def _add_component_actions(self, actions: List[Tuple], target_col: int):
        """
        Adds all valid component placement actions to the action list.

        Args:
            actions: List to append actions to
            target_col: Column to place components in
        """
        for comp_type, info in COMPONENT_CATALOG.items():
            if comp_type == 'wire':
                continue  # Wires are handled separately

            max_start = self.VOUT_ROW - (info.pin_count - 1)

            for r in range(self.VIN_ROW, max_start + 1):
                if self.can_place_component(comp_type, r):
                    actions.append((comp_type, r))

    def _add_wire_actions(self, actions: List[Tuple], target_col: int):
        """
        Adds all valid wire placement actions to the action list.

        Args:
            actions: List to append actions to
            target_col: Current target column (wires can connect up to this column)
        """
        _ = target_col  # unused in node model
        active_rows = [r for r in range(self.ROWS) if self.is_row_active(r)]
        all_rows = list(range(self.ROWS))
        seen_wires = set()

        for r1 in active_rows:
            for r2 in all_rows:
                wire_key = tuple(sorted((r1, r2)))
                if wire_key in seen_wires:
                    continue
                if self.can_place_wire(r1, r2):
                    seen_wires.add(wire_key)
                    actions.append(("wire", r1, r2))

    def _add_stop_action_if_valid(self, actions: List[Tuple]):
        """
        Adds STOP action if the circuit meets all validity requirements.

        The STOP action is only available when:
        - Circuit is complete and valid (per is_complete_and_valid())
        - Has at least 1 non-wire component (for backwards compatibility)

        Note: is_complete_and_valid() already enforces MIN_ACTIVE_COMPONENTS (2),
        so the num_components >= 1 check here is redundant but kept for clarity.

        Args:
            actions: List to append STOP action to
        """
        # Count non-wire, non-IO components
        num_components = len([c for c in self.placed_components
                             if c.type not in ['wire', 'vin', 'vout']])

        # Only allow STOP if circuit is complete and valid
        if self.is_complete_and_valid() and num_components >= 1:
            actions.append(("STOP",))

    def get_reward(self) -> float:
        if not self.is_complete_and_valid():
            return 0.0
        comp_count = sum(1 for c in self.placed_components if c.type not in ['wire', 'vin', 'vout'])
        wire_count = sum(1 for c in self.placed_components if c.type == 'wire')
        unique_types = len({c.type for c in self.placed_components if c.type not in ['wire', 'vin', 'vout']})
        return (comp_count * 10.0) + (unique_types * 5.0) - (wire_count * 1.0)
    
    def _place_component(self, comp_type: str, start_row: int) -> Optional[Component]:
        """(Internal) Mutates the board state by placing a component.

        Places a component starting at start_row with pins occupying consecutive rows.
        Each pin activates its entire row in the active_nets set.

        Note: Component pins do NOT automatically unite rows in the union-find structure.
        Components create edges in the connectivity graph during validation/netlist generation.
        This allows detection of degenerate components (all pins already on same net).
        """
        info = COMPONENT_CATALOG[comp_type]
        self.component_counter += 1
        component = Component(
            type=comp_type,
            pins=list(range(start_row, start_row + info.pin_count)),
            id=self.component_counter
        )
        self.placed_components.append(component)

        # Occupy rows and activate nets for all pins
        for i, r in enumerate(component.pins):
            self.row_pin_index.place_pin(r, component, i)
            self.active_nets.add(self.find(r))

        # NOTE: Component pins are NOT auto-unified in union-find structure
        # Instead, components create edges in the connectivity graph (see _compute_connectivity_summary)
        # This allows detection of degenerate components (all pins already on same net)

        if comp_type in ['vin', 'vout']: setattr(self, f"{comp_type}_placed", True)
        return component

    def _place_wire(self, r1: int, r2: int) -> Optional[Component]:
        """(Internal) Mutates the board state by placing a wire between two rows.

        Unites the entire rows r1 and r2 into a single electrical net using union-find.
        This is consistent with the row-based connectivity model where each row
        is a single electrical net (like a real breadboard).

        Args:
            r1: First endpoint row
            r2: Second endpoint row

        Returns:
            The created wire component, or None if placement fails
        """
        self.placed_wires.add(tuple(sorted((r1, r2))))
        self.union(r1, r2)  # Unions entire rows
        self.component_counter += 1
        component = Component(type="wire", pins=[r1, r2], id=self.component_counter)
        self.placed_components.append(component)
        self.active_nets.add(self.find(r1))
        return component

    def clone(self) -> "Breadboard":
        new_board = self.__class__.__new__(self.__class__)
        new_board.ROWS = self.ROWS
        new_board.COLUMNS = self.COLUMNS
        new_board.VSS_ROW = self.VSS_ROW
        new_board.VDD_ROW = self.VDD_ROW
        new_board.VIN_ROW = self.VIN_ROW
        new_board.VOUT_ROW = self.VOUT_ROW
        new_board.WORK_START_ROW = self.WORK_START_ROW
        new_board.WORK_END_ROW = self.WORK_END_ROW
        new_board.row_pin_index = self.row_pin_index.clone()
        new_board.placed_components = copy.deepcopy(self.placed_components)
        new_board.component_counter = self.component_counter
        new_board.vin_placed = self.vin_placed
        new_board.vout_placed = self.vout_placed
        new_board.uf_parent = self.uf_parent[:]
        new_board.active_nets = self.active_nets.copy()
        new_board.placed_wires = self.placed_wires.copy()
        return new_board
        
    def __hash__(self) -> int:
        """
        Generate hash for board state based on placed components.

        Creates a canonical representation by sorting components, which enables
        deduplication of equivalent board states during MCTS search.
        Pin list order is preserved within each component to maintain polarity
        (e.g., diode anode vs cathode, transistor pin ordering).

        Returns:
            Hash of the board's component configuration
        """
        # Preserve pin order to maintain component polarity (e.g., diode orientation)
        component_tuple = tuple(sorted(
            (c.type, tuple(c.pins)) for c in self.placed_components
        ))
        return hash(component_tuple)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Breadboard) and hash(self) == hash(other)

    def to_netlist(self) -> Optional[str]:
        """
        Converts the breadboard circuit to a SPICE netlist format.

        Strategy:
        1. Build net mapping from component pin positions using union-find row roots
        2. Assign net names (0 for ground, VDD for power, n0-nN for other nets)
        3. Generate SPICE netlist sections in order:
           - Header comment
           - Device models (must come before component instances)
           - Power supply (VDD)
           - Input source (VIN)
           - Circuit components (resistors, capacitors, transistors, etc.)
           - Output probe (VOUT)
           - Simulation commands

        Returns:
            SPICE netlist string, or None if circuit is not complete and valid
        """
        if not self.is_complete_and_valid():
            return None

        # Build net connectivity map
        row_to_net = self._build_net_mapping()

        # Generate netlist sections
        lines = self._generate_netlist_header()
        lines.extend(self._generate_device_models())  # Models must be defined before components
        lines.extend(self._generate_power_supply())
        lines.extend(self._generate_input_source(row_to_net))
        lines.extend(self._generate_circuit_components(row_to_net))
        lines.extend(self._generate_output_probe(row_to_net))
        lines.extend(self._generate_simulation_commands())

        return "\n".join(lines)

    def _build_net_mapping(self) -> Dict[int, str]:
        """
        Builds a mapping from component pin rows to net names.

        Uses the union-find structure to determine which net each row belongs to.
        Rows with the same root get the same net name.

        Special nets:
        - VSS_ROW root -> "0" (ground)
        - VDD_ROW root -> "VDD" (power supply)
        - Other roots -> "n0", "n1", "n2", etc.

        Returns:
            Dictionary mapping row indices to net names (e.g., "0", "VDD", "n0")
        """
        row_to_net: Dict[int, str] = {}
        root_to_net: Dict[int, str] = {}
        net_counter = 0

        for comp in self.placed_components:
            for row in comp.pins:
                root = self.find(row)
                if root not in root_to_net:
                    if root == self.VSS_ROW:
                        root_to_net[root] = "0"
                    elif root == self.VDD_ROW:
                        root_to_net[root] = "VDD"
                    else:
                        root_to_net[root] = f"n{net_counter}"
                        net_counter += 1
                row_to_net[row] = root_to_net[root]

        return row_to_net

    def _collect_all_positions(self) -> Set[Tuple[int, int]]:
        """
        Collects all positions occupied by component pins.

        Note: This method is not used in the current implementation but is kept
        for potential future use or debugging purposes.

        Returns:
            Set of (row, col) positions
        """
        all_positions: Set[Tuple[int, int]] = set()
        for comp in self.placed_components:
            for pin in comp.pins:
                all_positions.add(pin)
        return all_positions

    def _assign_initial_nets(self, positions: Set[Tuple[int, int]]) -> Dict[Tuple[int, int], str]:
        """
        Assigns initial net names to all positions.

        Note: This method is not used in the current implementation but is kept
        for potential future use. The current implementation uses _build_net_mapping()
        which directly uses the union-find structure.

        Power rails get special names (0 for ground, VDD for power).
        Other positions get unique net names.

        Args:
            positions: Set of positions to assign nets to

        Returns:
            Dictionary mapping positions to net names
        """
        position_to_net: Dict[Tuple[int, int], str] = {}
        net_counter = 0

        for pos in sorted(positions):
            row, col = pos

            # Special handling for power rails
            if row == self.VSS_ROW:
                position_to_net[pos] = "0"  # Ground
            elif row == self.VDD_ROW:
                position_to_net[pos] = "VDD"
            else:
                # Each position gets a unique net initially
                position_to_net[pos] = f"n{net_counter}"
                net_counter += 1

        return position_to_net

    def _merge_connected_nets(self, position_to_net: Dict[Tuple[int, int], str]):
        """
        Merges nets that are connected by wires using union-find.

        Note: This method is not used in the current implementation but is kept
        for potential future use. The current implementation uses _build_net_mapping()
        which directly uses the board's existing union-find structure.

        Args:
            position_to_net: Dictionary to update with merged net names
        """
        # Collect wire connections
        wire_connections = self._collect_wire_connections()

        # Use union-find to merge nets
        net_parent: Dict[str, str] = {}

        def find_net(net: str) -> str:
            """Finds the root net name with path compression."""
            if net not in net_parent:
                net_parent[net] = net
                return net
            if net_parent[net] != net:
                net_parent[net] = find_net(net_parent[net])
            return net_parent[net]

        def union_nets(net1: str, net2: str):
            """Unions two nets, preferring special nets (0, VDD)."""
            root1, root2 = find_net(net1), find_net(net2)
            if root1 != root2:
                # Prefer keeping special nets (0, VDD)
                if root1 in ["0", "VDD"]:
                    net_parent[root2] = root1
                elif root2 in ["0", "VDD"]:
                    net_parent[root1] = root2
                else:
                    net_parent[root2] = root1

        # Apply wire connections
        for pin1, pin2 in wire_connections:
            if pin1 in position_to_net and pin2 in position_to_net:
                union_nets(position_to_net[pin1], position_to_net[pin2])

        # Apply final net names
        for pin in position_to_net:
            position_to_net[pin] = find_net(position_to_net[pin])

    def _collect_wire_connections(self) -> List[Tuple[int, int]]:
        """
        Collects all wire connections from placed components.

        Returns:
            List of wire endpoint row pairs
        """
        wire_connections = []
        for comp in self.placed_components:
            if comp.type == 'wire' and len(comp.pins) == 2:
                wire_connections.append((comp.pins[0], comp.pins[1]))
        return wire_connections

    def get_connectivity_summary(self) -> Dict[str, object]:
        """
        Returns a detailed summary of circuit connectivity and validity.

        The summary includes:
        - VIN/VOUT presence and net assignments
        - Component connectivity (which nets have components)
        - Reachability from VIN to VOUT through components
        - Power rail connections (VDD/VSS)
        - Validity checks (degenerate components, floating components, etc.)

        Returns:
            Dictionary with connectivity information and validation results
        """
        return self._compute_connectivity_summary()

    def _compute_connectivity_summary(self) -> Dict[str, object]:
        """
        Computes detailed connectivity summary by building a component connectivity graph.

        This method:
        1. Maps all component pins to their net names using union-find
        2. Builds an adjacency graph where components create edges between nets
        3. Performs BFS from VIN net to find all reachable nets
        4. Validates circuit requirements (connectivity, power rails, no degeneracies)

        Returns:
            Dictionary with validation results and connectivity information
        """
        summary: Dict[str, object] = {
            "vin_present": self.vin_placed,
            "vout_present": self.vout_placed,
            "vin_net": None,
            "vout_net": None,
            "component_nets": set(),
            "visited_nets": set(),
            "touches_vdd": False,
            "touches_vss": False,
            "rails_in_component": {"VDD": False, "0": False},
            "reachable_vout": False,
            "all_components_reachable": False,
            "has_active_components": False,
            "vin_vout_distinct": True,
            "degenerate_component": False,
            "vin_on_power_rail": False,
            "vout_on_power_rail": False,
            "component_count": 0,
            "valid": False,
        }

        if not (self.vin_placed and self.vout_placed):
            return summary

        row_to_net = self._build_net_mapping()

        vin_comp = next((c for c in self.placed_components if c.type == 'vin'), None)
        vout_comp = next((c for c in self.placed_components if c.type == 'vout'), None)

        if not vin_comp or not vout_comp:
            return summary

        vin_net = row_to_net[vin_comp.pins[0]]
        vout_net = row_to_net[vout_comp.pins[0]]
        summary["vin_net"] = vin_net
        summary["vout_net"] = vout_net

        if vin_net in {"0", "VDD"}:
            summary["vin_on_power_rail"] = True
            return summary

        if vout_net in {"0", "VDD"}:
            summary["vout_on_power_rail"] = True
            return summary

        if vin_net == vout_net:
            summary["vin_vout_distinct"] = False
            return summary

        adjacency: Dict[str, Set[str]] = defaultdict(set)
        component_nets: Set[str] = set()
        touches_vdd = False
        touches_vss = False
        has_active_components = False
        component_count = 0

        for comp in self.placed_components:
            if comp.type in ['vin', 'vout', 'wire']:
                continue

            has_active_components = True
            component_count += 1
            nets = {row_to_net[row] for row in comp.pins}

            if len(nets) < 2:
                summary["degenerate_component"] = True
                return summary

            if "VDD" in nets:
                touches_vdd = True
            if "0" in nets:
                touches_vss = True

            component_nets.update(nets)
            nets_list = list(nets)

            for i in range(len(nets_list)):
                for j in range(i + 1, len(nets_list)):
                    n1, n2 = nets_list[i], nets_list[j]
                    adjacency[n1].add(n2)
                    adjacency[n2].add(n1)

        summary["has_active_components"] = has_active_components
        summary["component_count"] = component_count

        if not has_active_components:
            return summary

        summary["touches_vdd"] = touches_vdd
        summary["touches_vss"] = touches_vss

        visited: Set[str] = set()
        queue: deque[str] = deque([vin_net])
        visited.add(vin_net)

        while queue:
            net = queue.popleft()
            for neighbor in adjacency.get(net, ()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        summary["visited_nets"] = visited
        summary["reachable_vout"] = vout_net in visited
        summary["all_components_reachable"] = component_nets.issubset(visited)
        summary["rails_in_component"]["VDD"] = "VDD" in visited
        summary["rails_in_component"]["0"] = "0" in visited

        # Valid if VIN can reach VOUT through components, every component is on that path,
        # circuit has at least MIN_ACTIVE_COMPONENTS active components, and it touches both rails.
        summary["valid"] = (
            component_count >= self.MIN_ACTIVE_COMPONENTS and
            summary["reachable_vout"] and
            summary["all_components_reachable"] and
            has_active_components and
            summary["touches_vdd"] and
            summary["touches_vss"]
        )

        summary["component_nets"] = component_nets
        return summary

    def _generate_netlist_header(self) -> List[str]:
        """
        Generates the SPICE netlist header comment.

        Returns:
            List containing header comment lines
        """
        return [
            "* Auto-generated SPICE netlist from MCTS topology generator",
            ""
        ]

    def _generate_power_supply(self) -> List[str]:
        """
        Generates power supply voltage source (VDD).

        Returns:
            List containing VDD voltage source definition (5V DC)
        """
        return [
            "* Power supply",
            "VDD VDD 0 DC 5V",
            ""
        ]

    def _generate_input_source(self, row_to_net: Dict[int, str]) -> List[str]:
        """
        Generates input signal source (VIN) for AC analysis.

        Creates an AC voltage source with 1V amplitude at the VIN net.

        Args:
            row_to_net: Net mapping dictionary from _build_net_mapping()

        Returns:
            List of SPICE netlist lines for input source
        """
        lines = []
        vin_comp = next((c for c in self.placed_components if c.type == 'vin'), None)
        if vin_comp:
            vin_row = vin_comp.pins[0]
            vin_net = row_to_net[vin_row]
            lines.append("* Input signal")
            lines.append(f"VIN {vin_net} 0 AC 1V")
            lines.append("")
        return lines

    def _generate_circuit_components(self, row_to_net: Dict[int, str]) -> List[str]:
        """
        Generates SPICE lines for all circuit components.

        Iterates through all placed components (excluding VIN, VOUT, and wires)
        and generates the appropriate SPICE component line for each.

        Args:
            row_to_net: Net mapping dictionary from _build_net_mapping()

        Returns:
            List of SPICE netlist lines for circuit components
        """
        lines = ["* Circuit components"]
        comp_counters = {}

        for comp in self.placed_components:
            if comp.type in ['vin', 'vout', 'wire']:
                continue  # Skip markers and wires

            spice_line = self._generate_component_line(comp, row_to_net, comp_counters)
            if spice_line:
                lines.append(spice_line)

        lines.append("")
        return lines

    def _generate_component_line(self, comp: Component,
                                 row_to_net: Dict[int, str],
                                 comp_counters: Dict[str, int]) -> Optional[str]:
        """
        Generates a SPICE netlist line for a single component.

        Gets the component ID (e.g., R1, C2, M3), maps pins to net names,
        and formats the appropriate SPICE line.

        Args:
            comp: Component to generate line for
            row_to_net: Net mapping dictionary from _build_net_mapping()
            comp_counters: Dictionary tracking component counts by type for ID generation

        Returns:
            SPICE netlist line string, or None if component should be skipped
        """
        # Get component ID
        comp_id = self._get_component_id(comp.type, comp_counters)

        # Get net names for component pins
        pin_nets = [row_to_net[row] for row in comp.pins]

        # Generate SPICE line based on component type
        return self._format_component_spice_line(comp.type, comp_id, pin_nets)

    def _get_component_id(self, comp_type: str, comp_counters: Dict[str, int]) -> str:
        """
        Gets a unique component ID for SPICE netlist.

        Uses SPICE naming conventions:
        - R for resistors
        - C for capacitors
        - L for inductors
        - D for diodes
        - M for MOSFETs (both NMOS and PMOS share counter)
        - Q for BJTs (both NPN and PNP share counter)

        Args:
            comp_type: Type of component (e.g., 'resistor', 'nmos3', 'npn')
            comp_counters: Dictionary tracking component counts for ID generation

        Returns:
            Component ID string (e.g., "R1", "M2", "Q1")
        """
        prefix_map = {
            'resistor': 'R',
            'capacitor': 'C',
            'inductor': 'L',
            'diode': 'D',
            'nmos3': 'M',
            'pmos3': 'M',
            'npn': 'Q',
            'pnp': 'Q',
            'vin': 'V',
            'vout': 'V',
        }

        if comp_type in ['nmos3', 'pmos3']:
            comp_prefix = 'M'
            counter_key = 'mosfet'  # Unified counter for all MOSFETs
        elif comp_type in ['npn', 'pnp']:
            comp_prefix = 'Q'
            counter_key = 'bjt'  # Unified counter for all BJTs
        else:
            comp_prefix = prefix_map.get(comp_type, comp_type[0].upper())
            counter_key = comp_type

        # Increment counter
        if counter_key not in comp_counters:
            comp_counters[counter_key] = 0
        comp_counters[counter_key] += 1

        return f"{comp_prefix}{comp_counters[counter_key]}"

    def _format_component_spice_line(self, comp_type: str, comp_id: str,
                                     pin_nets: List[str]) -> Optional[str]:
        """
        Formats a SPICE netlist line for a component.

        Generates the appropriate SPICE syntax for each component type with
        default parameter values:
        - Resistors: 1kΩ
        - Capacitors: 1µF
        - Inductors: 1mH
        - Diodes: DMOD model
        - MOSFETs: L=1µm, W=10µm with bulk connections (NMOS bulk to ground, PMOS bulk to VDD)
        - BJTs: NPN_MODEL or PNP_MODEL

        Args:
            comp_type: Type of component (e.g., 'resistor', 'nmos3', 'npn')
            comp_id: Component identifier (e.g., 'R1', 'M2', 'Q1')
            pin_nets: List of net names for component pins

        Returns:
            Formatted SPICE line, or None if component type is unknown
        """
        if comp_type == 'resistor':
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} 1k"
        elif comp_type == 'capacitor':
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} 1u"
        elif comp_type == 'inductor':
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} 1m"
        elif comp_type == 'diode':
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} DMOD"
        elif comp_type == 'nmos3':
            # NMOS: Drain Gate Source Bulk (Bulk tied to VSS/ground)
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} 0 NMOS_MODEL L=1u W=10u"
        elif comp_type == 'pmos3':
            # PMOS: Drain Gate Source Bulk (Bulk tied to VDD)
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} VDD PMOS_MODEL L=1u W=10u"
        elif comp_type == 'npn':
            # NPN: Collector Base Emitter
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} NPN_MODEL"
        elif comp_type == 'pnp':
            # PNP: Collector Base Emitter
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} PNP_MODEL"
        return None

    def _generate_output_probe(self, row_to_net: Dict[int, str]) -> List[str]:
        """
        Generates output probe (VOUT) for AC analysis.

        Creates a .print statement to output the AC voltage at the VOUT net.

        Args:
            row_to_net: Net mapping dictionary from _build_net_mapping()

        Returns:
            List of SPICE netlist lines for output probe
        """
        lines = []
        vout_comp = next((c for c in self.placed_components if c.type == 'vout'), None)
        if vout_comp:
            vout_row = vout_comp.pins[0]
            vout_net = row_to_net[vout_row]
            lines.append("* Output probe")
            lines.append(f".print ac v({vout_net})")
            lines.append("")
        return lines

    def _generate_device_models(self) -> List[str]:
        """
        Generates SPICE device model definitions.

        Defines models for:
        - DMOD: Simple diode model
        - NMOS_MODEL: NMOS transistor (VTO=0.7V, KP=20µA/V²)
        - PMOS_MODEL: PMOS transistor (VTO=-0.7V, KP=10µA/V²)
        - NPN_MODEL: NPN BJT (BF=100)
        - PNP_MODEL: PNP BJT (BF=100)

        Returns:
            List of SPICE .model statements
        """
        return [
            "* Device models",
            ".model DMOD D",
            ".model NMOS_MODEL NMOS (LEVEL=1 VTO=0.7 KP=20u)",
            ".model PMOS_MODEL PMOS (LEVEL=1 VTO=-0.7 KP=10u)",
            ".model NPN_MODEL NPN (BF=100)",
            ".model PNP_MODEL PNP (BF=100)",
            ""
        ]

    def _generate_simulation_commands(self) -> List[str]:
        """
        Generates SPICE simulation control commands.

        Sets up AC analysis with:
        - Decade sweep (100 points per decade)
        - Frequency range: 1 Hz to 1 MHz

        Returns:
            List of SPICE simulation command lines
        """
        return [
            "* Simulation commands",
            ".ac dec 100 1 1MEG",
            ".end"
        ]
    
# ============================================================

if __name__ == '__main__':
    print("Run the dedicated pytest suite for validation.")
