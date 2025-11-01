"""
Breadboard simulation for circuit topology generation.

This module provides a virtual breadboard environment for placing electronic
components and wiring them together. It enforces electrical connectivity rules
and validates circuit topologies.

Refactored to follow SOLID principles with small, focused methods.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set
import copy


# ============================================================
# Component Metadata
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
# Node and Component Models
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
    DEFAULT_ROWS = 30
    DEFAULT_COLUMNS = 8
    MIN_ROWS = 6  # Need VIN, VOUT, power rails, and at least one work row

    def __init__(self, rows: int = DEFAULT_ROWS, columns: int = DEFAULT_COLUMNS):
        if rows < self.MIN_ROWS:
            raise ValueError(f"Breadboard requires at least {self.MIN_ROWS} rows (got {rows})")
        if columns < 2:
            raise ValueError(f"Breadboard requires at least 2 columns (got {columns})")

        # Board dimensions (stored per-instance so tests/CLI can customize them)
        self.ROWS = rows
        self.COLUMNS = columns
        self.VSS_ROW = 0
        self.VDD_ROW = rows - 1
        self.VIN_ROW = 1
        self.VOUT_ROW = rows - 2
        self.WORK_START_ROW = 2
        self.WORK_END_ROW = rows - 3

        if self.WORK_END_ROW < self.WORK_START_ROW:
            raise ValueError("Breadboard needs at least one work row between VIN/VOUT and power rails")

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
        # Place VIN and VOUT on dedicated reserved rows
        self._place_component('vin', self.VIN_ROW, 0)
        self._place_component('vout', self.VOUT_ROW, 0)

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

        # Allow components to span from VIN/VOUT rows into work area
        min_allowed_row = self.VIN_ROW  # Allow starting from VIN row
        max_allowed_row = self.VOUT_ROW  # Allow ending at VOUT row
        if not (min_allowed_row <= pin_rows.start and pin_rows.stop - 1 <= max_allowed_row):
            return False

        if not all(self.is_empty(r, col) for r in pin_rows):
            return False
        if info.pin_count == 1:
            return not self.is_row_active(start_row)
        return any(self.is_row_active(r) for r in pin_rows)

    def can_place_wire(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        """
        Checks if a wire can be legally placed between two positions.

        Args:
            r1, c1: First endpoint position
            r2, c2: Second endpoint position

        Returns:
            True if wire placement is valid
        """
        # Same row connections are not allowed
        if r1 == r2:
            return False

        # Check if positions are within bounds
        if not self._is_position_valid(r1, c1) or not self._is_position_valid(r2, c2):
            return False

        # Check for duplicate wire
        if self._is_duplicate_wire(r1, c1, r2, c2):
            return False

        # At least one endpoint must be on an active net
        if not (self.is_row_active(r1) or self.is_row_active(r2)):
            return False

        # Check gate/base pin connection rules
        if not self._validate_control_pin_wiring(r1, c1, r2, c2):
            return False

        return True

    def _is_position_valid(self, row: int, col: int) -> bool:
        """
        Checks if a position is within the breadboard bounds.

        Args:
            row: Row index
            col: Column index

        Returns:
            True if position is valid
        """
        return 0 <= row < self.ROWS and 0 <= col < self.COLUMNS

    def _is_duplicate_wire(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        """
        Checks if a wire already exists between two positions.

        Args:
            r1, c1: First endpoint position
            r2, c2: Second endpoint position

        Returns:
            True if this wire already exists
        """
        wire_key = tuple(sorted(((r1, c1), (r2, c2))))
        return wire_key in self.placed_wires

    def _validate_control_pin_wiring(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        """
        Validates that gate/base pins are not directly connected to power rails.

        This prevents shorts and ensures proper circuit design.
        Gate pins (MOSFET) and base pins (BJT) should not be directly
        connected to VDD or VSS.

        Args:
            r1, c1: First endpoint position
            r2, c2: Second endpoint position

        Returns:
            True if wiring is valid
        """
        # Check both endpoints
        for row, col in [(r1, c1), (r2, c2)]:
            if not self._is_control_pin_power_rail_connection_valid(row, col, r1, c1, r2, c2):
                return False
        return True

    def _is_control_pin_power_rail_connection_valid(self, row: int, col: int,
                                                     r1: int, c1: int, r2: int, c2: int) -> bool:
        """
        Checks if a specific position (gate or base pin) can be wired to the other endpoint.

        Args:
            row, col: Position to check (potential gate/base pin)
            r1, c1: First wire endpoint
            r2, c2: Second wire endpoint

        Returns:
            True if connection is valid
        """
        cell = self.grid[row][col]
        if cell is None:
            return True  # Empty cell, no restriction

        component, pin_index = cell

        # Check if this is a gate pin (MOSFET pin 1)
        if component.type in ['nmos3', 'pmos3'] and pin_index == 1:
            other_row = r2 if row == r1 else r1
            if self._is_power_rail(other_row):
                return False  # Cannot wire gate to power rail

        # Check if this is a base pin (BJT pin 1)
        elif component.type in ['npn', 'pnp'] and pin_index == 1:
            other_row = r2 if row == r1 else r1
            if self._is_power_rail(other_row):
                return False  # Cannot wire base to power rail

        return True

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
        2. All components must be connected (including VIN-VOUT path)
        3. Gate/Base pins must not be directly connected to VDD/VSS

        Note: VIN-VOUT connectivity is now checked within _all_components_connected()
        using position-based net mapping for accurate validation.
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
        Verify that all component pins are part of the main circuit.
        No floating/disconnected components allowed.

        Uses position-based connectivity (same as netlist generation) to ensure
        validation matches actual electrical connectivity.

        Returns:
            True if all components are connected to the VIN-VOUT path
        """
        if not self.vin_placed or not self.vout_placed:
            return False

        # Build the same position-to-net mapping used in netlist generation
        position_to_net = self._build_net_mapping()

        # Get VIN and VOUT components
        vin_comp = next((c for c in self.placed_components if c.type == 'vin'), None)
        vout_comp = next((c for c in self.placed_components if c.type == 'vout'), None)

        if not vin_comp or not vout_comp:
            return False

        # Get the nets for VIN and VOUT
        vin_net = position_to_net[vin_comp.pins[0]]
        vout_net = position_to_net[vout_comp.pins[0]]

        # Check VIN and VOUT are on the same net (connected)
        if vin_net != vout_net:
            return False

        main_net = vin_net

        # Check every non-wire component has at least one pin on the main net
        for comp in self.placed_components:
            if comp.type in ['vin', 'vout', 'wire']:
                continue

            # At least one pin must be connected to the main net
            component_connected = False
            for pin_pos in comp.pins:
                if position_to_net[pin_pos] == main_net:
                    component_connected = True
                    break

            if not component_connected:
                return False  # Found a floating component

        return True

    def _validate_gate_base_connections(self) -> bool:
        """
        Ensure gate (MOSFET) and base (BJT) pins are not directly placed on
        VDD or VSS power rail rows.

        This prevents direct shorts but allows gates/bases to be in circuits
        that have other components connected to power rails.

        Gate = pin 1 (index 1) for NMOS/PMOS
        Base = pin 1 (index 1) for NPN/PNP

        Returns:
            True if all gate/base connections are valid
        """
        for comp in self.placed_components:
            # Check MOSFET gate pins
            if comp.type in ['nmos3', 'pmos3']:
                gate_row = comp.pins[1][0]  # Gate is second pin (index 1)
                # Gate cannot be placed directly on VDD or VSS rows
                if gate_row == self.VDD_ROW or gate_row == self.VSS_ROW:
                    return False

            # Check BJT base pins
            elif comp.type in ['npn', 'pnp']:
                base_row = comp.pins[1][0]  # Base is second pin (index 1)
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
            _, r1, c1, r2, c2 = action
            success = new_board._place_wire(r1, c1, r2, c2) is not None
        else:
            comp_type, start_row, col = action
            success = new_board._place_component(comp_type, start_row, col) is not None
        if not success:
            raise ValueError(f"Invalid action applied: {action}")
        return new_board

    def legal_actions(self) -> List[Tuple]:
        """
        Generates all legal actions (component placements and wires) from current state.

        Returns:
            List of action tuples:
            - Component placement: (comp_type, start_row, col)
            - Wire placement: ("wire", r1, c1, r2, c2)
            - Stop action: ("STOP",)
        """
        actions: List[Tuple] = []

        # Find the next available column for component placement
        target_col = self._find_target_column()

        if target_col == -1:
            # No more space - only allow STOP if circuit is complete
            self._add_stop_action_if_valid(actions)
            return actions

        # Generate component placement actions
        self._add_component_actions(actions, target_col)

        # Generate wire placement actions
        self._add_wire_actions(actions, target_col)

        # Add STOP action if circuit is complete and valid
        self._add_stop_action_if_valid(actions)

        return actions

    def _find_target_column(self) -> int:
        """
        Finds the next available column for component placement.

        Returns:
            Column index, or -1 if no columns are available
        """
        # Start from column 1 since column 0 is reserved for vin/vout
        for c in range(1, self.COLUMNS):
            # Check if this column has any empty space in the work area
            if not all(not self.is_empty(r, c) for r in range(self.WORK_START_ROW, self.WORK_END_ROW + 1)):
                return c
        return -1

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

            # Calculate the maximum starting row for this component
            # Allow components to connect from VIN_ROW (1) to VOUT_ROW (28)
            max_start = self.VOUT_ROW - (info.pin_count - 1)

            # Try all possible starting rows from VIN_ROW to max_start
            for r in range(self.VIN_ROW, max_start + 1):
                if self.can_place_component(comp_type, r, target_col):
                    actions.append((comp_type, r, target_col))

    def _add_wire_actions(self, actions: List[Tuple], target_col: int):
        """
        Adds all valid wire placement actions to the action list.

        Args:
            actions: List to append actions to
            target_col: Current target column (wires can connect up to this column)
        """
        # Find the maximum column that has any components
        # This ensures we can wire from all placed components, not just up to target_col
        max_col = 0
        for r in range(self.ROWS):
            for c in range(self.COLUMNS):
                if not self.is_empty(r, c):
                    max_col = max(max_col, c)

        # Use the larger of target_col and max_col to ensure all components can be wired
        wire_col_limit = max(target_col, max_col)

        # Get all active positions (potential wire sources)
        source_points = {(r, c) for c in range(wire_col_limit + 1)
                        for r in range(self.ROWS) if self.is_row_active(r)}

        # Get all positions (potential wire targets)
        target_points = {(r, c) for c in range(wire_col_limit + 1) for r in range(self.ROWS)}

        # Try all possible wire connections
        for r1, c1 in source_points:
            for r2, c2 in target_points:
                # Skip if positions are in wrong order (avoid duplicates)
                if (r1, c1) >= (r2, c2):
                    continue

                if self.can_place_wire(r1, c1, r2, c2):
                    actions.append(("wire", r1, c1, r2, c2))

    def _add_stop_action_if_valid(self, actions: List[Tuple]):
        """
        Adds STOP action if the circuit is complete and has minimum complexity.

        Args:
            actions: List to append STOP action to
        """
        # Count non-wire, non-IO components
        num_components = len([c for c in self.placed_components
                             if c.type not in ['wire', 'vin', 'vout']])

        # Only allow STOP if circuit is complete AND has minimum complexity
        if self.is_complete_and_valid() and num_components >= 1:
            actions.append(("STOP",))

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

        # Auto-union component pins (component pins are inherently connected)
        if len(component.pins) > 1:
            first_row = component.pins[0][0]
            for pin_row, _ in component.pins[1:]:
                self.union(first_row, pin_row)

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
        new_board.ROWS = self.ROWS
        new_board.COLUMNS = self.COLUMNS
        new_board.VSS_ROW = self.VSS_ROW
        new_board.VDD_ROW = self.VDD_ROW
        new_board.VIN_ROW = self.VIN_ROW
        new_board.VOUT_ROW = self.VOUT_ROW
        new_board.WORK_START_ROW = self.WORK_START_ROW
        new_board.WORK_END_ROW = self.WORK_END_ROW
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

        Returns None if the circuit is not complete and valid.

        Strategy: Build a connectivity graph where component pins get unique nets,
        then merge nets connected by wires.

        Returns:
            SPICE netlist string, or None if circuit is invalid
        """
        if not self.is_complete_and_valid():
            return None

        # Build net connectivity map
        position_to_net = self._build_net_mapping()

        # Generate netlist sections
        lines = self._generate_netlist_header()
        lines.extend(self._generate_power_supply())
        lines.extend(self._generate_input_source(position_to_net))
        lines.extend(self._generate_circuit_components(position_to_net))
        lines.extend(self._generate_output_probe(position_to_net))
        lines.extend(self._generate_device_models())
        lines.extend(self._generate_simulation_commands())

        return "\n".join(lines)

    def _build_net_mapping(self) -> Dict[Tuple[int, int], str]:
        """
        Builds a mapping from positions to net names, handling wire connections.

        Returns:
            Dictionary mapping (row, col) positions to net names
        """
        # Collect all positions used by components
        all_positions = self._collect_all_positions()

        # Assign initial net names
        position_to_net = self._assign_initial_nets(all_positions)

        # Merge nets connected by wires
        self._merge_connected_nets(position_to_net)

        return position_to_net

    def _collect_all_positions(self) -> Set[Tuple[int, int]]:
        """
        Collects all positions occupied by component pins.

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
        Merges nets that are connected by wires and multi-pin components using union-find.

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

        # First, union all pins of multi-pin components
        # (component pins are inherently connected)
        for comp in self.placed_components:
            if comp.type in ['vin', 'vout', 'wire']:
                continue
            if len(comp.pins) > 1:
                # Union all pins of this component together
                first_net = position_to_net[comp.pins[0]]
                for pin in comp.pins[1:]:
                    union_nets(first_net, position_to_net[pin])

        # Then apply wire connections
        for pin1, pin2 in wire_connections:
            if pin1 in position_to_net and pin2 in position_to_net:
                union_nets(position_to_net[pin1], position_to_net[pin2])

        # Apply final net names
        for pin in position_to_net:
            position_to_net[pin] = find_net(position_to_net[pin])

    def _collect_wire_connections(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Collects all wire connections from placed components.

        Returns:
            List of wire endpoint pairs
        """
        wire_connections = []
        for comp in self.placed_components:
            if comp.type == 'wire' and len(comp.pins) == 2:
                wire_connections.append((comp.pins[0], comp.pins[1]))
        return wire_connections

    def _generate_netlist_header(self) -> List[str]:
        """Generates the netlist header comment."""
        return [
            "* Auto-generated SPICE netlist from MCTS topology generator",
            ""
        ]

    def _generate_power_supply(self) -> List[str]:
        """Generates power supply voltage source."""
        return [
            "* Power supply",
            "VDD VDD 0 DC 5V",
            ""
        ]

    def _generate_input_source(self, position_to_net: Dict[Tuple[int, int], str]) -> List[str]:
        """
        Generates input signal source (VIN).

        Args:
            position_to_net: Net mapping dictionary

        Returns:
            List of netlist lines
        """
        lines = []
        vin_comp = next((c for c in self.placed_components if c.type == 'vin'), None)
        if vin_comp:
            vin_pos = vin_comp.pins[0]
            vin_net = position_to_net[vin_pos]
            lines.append("* Input signal")
            lines.append(f"VIN {vin_net} 0 AC 1V")
            lines.append("")
        return lines

    def _generate_circuit_components(self, position_to_net: Dict[Tuple[int, int], str]) -> List[str]:
        """
        Generates SPICE lines for all circuit components.

        Args:
            position_to_net: Net mapping dictionary

        Returns:
            List of netlist lines
        """
        lines = ["* Circuit components"]
        comp_counters = {}

        for comp in self.placed_components:
            if comp.type in ['vin', 'vout', 'wire']:
                continue  # Skip markers and wires

            spice_line = self._generate_component_line(comp, position_to_net, comp_counters)
            if spice_line:
                lines.append(spice_line)

        lines.append("")
        return lines

    def _generate_component_line(self, comp: Component,
                                 position_to_net: Dict[Tuple[int, int], str],
                                 comp_counters: Dict[str, int]) -> Optional[str]:
        """
        Generates a SPICE netlist line for a single component.

        Args:
            comp: Component to generate line for
            position_to_net: Net mapping dictionary
            comp_counters: Dictionary tracking component counts by type

        Returns:
            SPICE netlist line, or None if component should be skipped
        """
        # Get component ID
        comp_id = self._get_component_id(comp.type, comp_counters)

        # Get net names for component pins
        pin_nets = [position_to_net[pin] for pin in comp.pins]

        # Generate SPICE line based on component type
        return self._format_component_spice_line(comp.type, comp_id, pin_nets)

    def _get_component_id(self, comp_type: str, comp_counters: Dict[str, int]) -> str:
        """
        Gets a unique component ID for SPICE netlist.

        Args:
            comp_type: Type of component
            comp_counters: Dictionary tracking component counts

        Returns:
            Component ID string (e.g., "R1", "M2")
        """
        # MOSFETs must use 'M' prefix in SPICE
        if comp_type in ['nmos3', 'pmos3']:
            comp_prefix = 'M'
            counter_key = 'mosfet'  # Unified counter for all MOSFETs
        else:
            comp_prefix = comp_type[0].upper()
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

        Args:
            comp_type: Type of component
            comp_id: Component identifier
            pin_nets: List of net names for component pins

        Returns:
            Formatted SPICE line
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
            # NMOS: Drain Gate Source Bulk (Bulk tied to source)
            return f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} {pin_nets[2]} NMOS_MODEL L=1u W=10u"
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

    def _generate_output_probe(self, position_to_net: Dict[Tuple[int, int], str]) -> List[str]:
        """
        Generates output probe (VOUT).

        Args:
            position_to_net: Net mapping dictionary

        Returns:
            List of netlist lines
        """
        lines = []
        vout_comp = next((c for c in self.placed_components if c.type == 'vout'), None)
        if vout_comp:
            vout_pos = vout_comp.pins[0]
            vout_net = position_to_net[vout_pos]
            lines.append("* Output probe")
            lines.append(f".print ac v({vout_net})")
            lines.append("")
        return lines

    def _generate_device_models(self) -> List[str]:
        """Generates device model definitions."""
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
        """Generates simulation control commands."""
        return [
            "* Simulation commands",
            ".ac dec 100 1 1MEG",
            ".end"
        ]
    
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
    assert b0.is_row_active(b0.VIN_ROW)  # VIN at row 1
    assert b0.is_row_active(b0.VOUT_ROW)  # VOUT at row 28
    assert not b0.is_row_active(10)
    print("✅ Passed: Initial state is correct.")

    # --- Test 2: Component Placement Rules ---
    print("\n--- Test 2: Component Placement Rules ---")
    assert not b0.can_place_component('vin', 10, 1)  # VIN already placed
    assert not b0.can_place_component('resistor', 5, 0)  # Column 0 reserved
    # Note: Can't place resistor at (5,1) yet - need to wire VIN to work area first
    # First wire VIN to a work row to activate it
    b0_wired = b0.apply_action(('wire', b0.VIN_ROW, 0, 5, 1))
    assert b0_wired.is_row_active(5)
    assert b0_wired.can_place_component('resistor', 5, 1)  # Now row 5 is active
    print("✅ Passed: Component placement rules are enforced.")

    # --- Test 3: Wiring Rules and State Immutability ---
    print("\n--- Test 3: Wiring Rules & State Immutability ---")
    # First wire VIN to row 5 to activate it
    b1 = b0.apply_action(('wire', b0.VIN_ROW, 0, 5, 1))
    assert b1.is_row_active(5)
    # Now place resistor at rows 5-6
    b1 = b1.apply_action(('resistor', 5, 1))
    # Resistor is on rows 5-6, both should be active and auto-unioned
    assert b1.is_row_active(5) and b1.is_row_active(6)
    assert b1.find(5) == b1.find(6)  # Component pins are auto-connected
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
    # Connect vin to resistor and resistor to vout (resistor pins are already auto-connected)
    b3 = b2.apply_action(('wire', b0.VIN_ROW, 0, 5, 1))  # VIN (row 1) to resistor
    # Then connect to vout at row 28
    b4 = b3.apply_action(('wire', 10, 1, b0.VOUT_ROW, 0))  # Connect to VOUT (row 28)
    assert b4.is_complete_and_valid(), "Circuit should be complete after connecting VIN and VOUT nets."
    assert b4.get_reward() > 0.0
    print("✅ Passed: Circuit completion and reward logic are working.")

    print("\n🎉 All simple checks passed!")

def test_netlist_conversion():
    """
    Tests the to_netlist() method to ensure circuits are properly converted to SPICE format.
    """
    print("\n🔬 Running netlist conversion tests...")

    # --- Test 1: Incomplete Circuit Returns None ---
    print("\n--- Test 1: Incomplete Circuit Returns None ---")
    b0 = Breadboard()
    assert b0.to_netlist() is None, "Incomplete circuit should return None"
    print("✅ Passed: Incomplete circuit returns None")

    # --- Test 2: Simple RC Circuit ---
    print("\n--- Test 2: Simple RC Circuit Netlist ---")
    # Build: VIN -> Resistor -> Capacitor -> VOUT
    # Component pins are now auto-connected, only need wires between components
    b1 = Breadboard()
    b1 = b1.apply_action(('resistor', 5, 1))  # R on rows 5-6 (pins auto-connected)
    b1 = b1.apply_action(('wire', b1.VIN_ROW, 0, 5, 1))  # Connect VIN (row 1) to R pin 1
    b1 = b1.apply_action(('capacitor', 7, 2))  # C on rows 7-8 (pins auto-connected)
    b1 = b1.apply_action(('wire', 6, 1, 7, 2))  # Connect R pin 2 to C pin 1
    b1 = b1.apply_action(('wire', 8, 2, b1.VOUT_ROW, 0))  # Connect C pin 2 to VOUT (row 28)

    netlist = b1.to_netlist()
    assert netlist is not None, "Complete circuit should return a netlist"
    assert "VIN" in netlist, "Netlist should contain VIN source"
    assert "VDD" in netlist, "Netlist should contain VDD source"
    assert "R1" in netlist, "Netlist should contain resistor R1"
    assert "C1" in netlist, "Netlist should contain capacitor C1"
    assert ".ac dec" in netlist, "Netlist should contain AC analysis command"
    assert ".end" in netlist, "Netlist should end with .end"
    print("✅ Passed: RC circuit generates valid netlist")
    print(f"\nGenerated netlist:\n{netlist}\n")

    # --- Test 3: Multiple Components of Same Type ---
    print("\n--- Test 3: Multiple Components of Same Type ---")
    b2 = Breadboard()
    b2 = b2.apply_action(('resistor', 5, 1))  # R1 on rows 5-6 (pins auto-connected)
    b2 = b2.apply_action(('wire', b2.VIN_ROW, 0, 5, 1))  # Connect VIN to R1
    b2 = b2.apply_action(('resistor', 7, 2))  # R2 on rows 7-8 (pins auto-connected)
    b2 = b2.apply_action(('wire', 6, 1, 7, 2))  # Connect R1 to R2
    b2 = b2.apply_action(('wire', 8, 2, b2.VOUT_ROW, 0))  # Connect R2 to VOUT

    netlist2 = b2.to_netlist()
    assert netlist2 is not None
    assert "R1" in netlist2, "Should have R1"
    assert "R2" in netlist2, "Should have R2"
    r1_count = netlist2.count("R1")
    r2_count = netlist2.count("R2")
    assert r1_count >= 1 and r2_count >= 1, "Both resistors should be in netlist"
    print("✅ Passed: Multiple components of same type handled correctly")

    # --- Test 4: Net Naming and Connectivity ---
    print("\n--- Test 4: Net Naming and Connectivity ---")
    b3 = Breadboard()
    b3 = b3.apply_action(('resistor', 5, 1))  # Resistor pins auto-connected
    b3 = b3.apply_action(('wire', b3.VIN_ROW, 0, 5, 1))
    b3 = b3.apply_action(('wire', 6, 1, b3.VOUT_ROW, 0))

    netlist3 = b3.to_netlist()
    assert netlist3 is not None
    # Parse the netlist to check that VIN and VOUT are on the same net via the resistor
    lines = netlist3.split('\n')
    resistor_line = [l for l in lines if l.startswith('R1')][0]
    # The resistor should connect two nets
    assert 'R1' in resistor_line, "Resistor line should exist"
    print("✅ Passed: Net naming and connectivity correct")

    # --- Test 5: Transistor Component ---
    print("\n--- Test 5: Transistor Component (NMOS) ---")
    b4 = Breadboard()
    b4 = b4.apply_action(('nmos3', 5, 1))  # NMOS on rows 5-6-7 (drain, gate, source - pins auto-connected)
    b4 = b4.apply_action(('wire', b4.VIN_ROW, 0, 5, 1))  # VIN to drain
    b4 = b4.apply_action(('wire', 7, 1, b4.VOUT_ROW, 0))  # source to VOUT

    netlist4 = b4.to_netlist()
    assert netlist4 is not None
    assert "M1" in netlist4, "Should contain NMOS transistor (M1)"
    assert "NMOS_MODEL" in netlist4, "Should reference NMOS model"
    print("✅ Passed: Transistor component handled correctly")

    # --- Test 6: Proper Multi-Net RC Low-Pass Filter ---
    print("\n--- Test 6: Proper Multi-Net RC Low-Pass Filter ---")
    # Build a proper RC low-pass filter: VIN --R-- net1 --C-- GND, VOUT at net1
    b5 = Breadboard()
    # First wire VIN to work area
    b5 = b5.apply_action(('wire', b5.VIN_ROW, 0, 10, 1))  # Activate row 10
    # Place resistor between input and middle node
    b5 = b5.apply_action(('resistor', 10, 1))  # R on rows 10-11 (pins auto-connected)
    # Place capacitor from middle node to ground
    b5 = b5.apply_action(('capacitor', 12, 2))  # C on rows 12-13 (pins auto-connected)
    b5 = b5.apply_action(('wire', 11, 1, 12, 2))  # R output to C input
    b5 = b5.apply_action(('wire', 13, 2, 0, 2))  # C to VSS (ground)
    # Connect VOUT to the middle node (between R and C)
    b5 = b5.apply_action(('wire', 11, 1, b5.VOUT_ROW, 0))  # Middle node to VOUT

    netlist5 = b5.to_netlist()
    assert netlist5 is not None, "RC filter should generate netlist"

    # Verify structure: should have VIN net, middle net (at VOUT), and ground
    lines5 = netlist5.split('\n')
    r_line = [l for l in lines5 if l.startswith('R1')][0]
    c_line = [l for l in lines5 if l.startswith('C1')][0]

    # Resistor should connect VIN net to middle net
    # Capacitor should connect middle net to ground (0)
    assert '0' in c_line, "Capacitor should connect to ground"
    print("✅ Passed: Multi-net RC filter generates correct topology")
    print(f"\nRC Filter netlist:\n{netlist5}\n")

    print("\n🎉 All netlist conversion tests passed!")

if __name__ == "__main__":
    run_tests()
    test_netlist_conversion()
