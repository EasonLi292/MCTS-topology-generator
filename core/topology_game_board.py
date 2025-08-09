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
    priority: int = 1
    pin_names: List[str] = field(default_factory=list)
    can_place_multiple: bool = True  # Can this component be placed multiple times?

COMPONENT_CATALOG: Dict[str, ComponentInfo] = {
    'resistor': ComponentInfo(2, True, priority=3, pin_names=['p1', 'p2']),
    'capacitor': ComponentInfo(2, True, priority=2, pin_names=['p1', 'p2']),
    'inductor': ComponentInfo(2, True, priority=1, pin_names=['p1', 'p2']),
    'diode': ComponentInfo(2, True, priority=2, pin_names=['anode', 'cathode']),
    'nmos3': ComponentInfo(3, True, priority=3, pin_names=['drain', 'gate', 'source']),
    'pmos3': ComponentInfo(3, True, priority=3, pin_names=['drain', 'gate', 'source']),
    'npn': ComponentInfo(3, True, priority=2, pin_names=['collector', 'base', 'emitter']),
    'pnp': ComponentInfo(3, True, priority=2, pin_names=['collector', 'base', 'emitter']),
    'vin': ComponentInfo(1, True, priority=5, pin_names=['signal'], can_place_multiple=False),
    'vout': ComponentInfo(1, True, priority=5, pin_names=['signal'], can_place_multiple=False),
    'wire': ComponentInfo(2, False, priority=4, pin_names=['p1', 'p2']),
}

# ============================================================
# Node Model
# ============================================================

class NodeType(Enum):
    NORMAL = auto()
    VDD = auto()  # Power rail - always at row 29
    VSS = auto()  # Ground rail - always at row 0

@dataclass
class Node:
    row_index: int
    node_type: NodeType = NodeType.NORMAL
    connected_pins: List[Tuple["Component", int]] = field(default_factory=list)

# ============================================================
# Component Placement
# ============================================================

@dataclass
class Component:
    type: str
    pins: List[Tuple[int, int]]  # [(row, col)]
    id: int = 0

# ============================================================
# Breadboard Class
# ============================================================

class Breadboard:
    ROWS = 30
    COLUMNS = 8
    VSS_ROW = 0   # Ground at top
    VDD_ROW = 29  # Power at bottom
    WORK_START_ROW = 1  # Working area starts at row 1
    WORK_END_ROW = 28   # Working area ends at row 28

    def __init__(self):
        self.grid: List[List[Optional[Tuple[Component, int]]]] = [
            [None for _ in range(self.COLUMNS)] for _ in range(self.ROWS)
        ]
        
        # Initialize nodes
        self.nodes: List[Node] = []
        for r in range(self.ROWS):
            if r == self.VSS_ROW:
                self.nodes.append(Node(row_index=r, node_type=NodeType.VSS))
            elif r == self.VDD_ROW:
                self.nodes.append(Node(row_index=r, node_type=NodeType.VDD))
            else:
                self.nodes.append(Node(row_index=r, node_type=NodeType.NORMAL))
        
        self.placed_components: List[Component] = []
        self.component_counter = 0
        self.uf_parent: List[int] = list(range(self.ROWS))
        
        # Track special components
        self.vin_placed = False
        self.vout_placed = False
        
        # Track placed wires to avoid duplicates
        self.placed_wires: Set[Tuple[int, int, int, int]] = set()

    def find(self, row: int) -> int:
        """Union-find with path compression"""
        if self.uf_parent[row] != row:
            self.uf_parent[row] = self.find(self.uf_parent[row])
        return self.uf_parent[row]

    def union(self, row1: int, row2: int):
        """Union-find union operation"""
        root1 = self.find(row1)
        root2 = self.find(row2)
        if root1 != root2:
            self.uf_parent[root2] = root1

    def is_empty(self, row: int, col: int) -> bool:
        """Check if a grid position is empty"""
        return 0 <= row < self.ROWS and 0 <= col < self.COLUMNS and self.grid[row][col] is None

    def get_node(self, row: int) -> Node:
        """Get the node for a given row"""
        return self.nodes[row]

    def row_in_active_net(self, row: int) -> bool:
        """Check if row is in a net that has components or is a power rail"""
        root = self.find(row)
        
        # Check if any row with this root has pins or is a power rail
        for r in range(self.ROWS):
            if self.find(r) == root:
                node = self.get_node(r)
                # Power rails are always active
                if node.node_type in [NodeType.VSS, NodeType.VDD]:
                    return True
                # Rows with components are active
                if len(node.connected_pins) > 0:
                    return True
        return False

    def is_row_floating(self, row: int) -> bool:
        """Check if a row has no connections (floating)"""
        return not self.row_in_active_net(row)

    def is_row_connected(self, row: int) -> bool:
        """Check if a row has any connections (via union-find or direct pins)"""
        return self.row_in_active_net(row)

    def get_current_placement_column(self) -> Optional[int]:
        """Get the current column for component placement"""
        for col in range(self.COLUMNS):
            if any(self.is_empty(r, col) for r in range(self.WORK_START_ROW, self.WORK_END_ROW + 1)):
                return col
        return None

    def can_place_component_at(self, component_type: str, start_row: int, column: int) -> bool:
        """Check if component can be placed at position"""
        if component_type == 'wire':
            return False
        
        info = COMPONENT_CATALOG.get(component_type)
        if not info:
            return False
            
        # Check if we can place multiple of this component
        if not info.can_place_multiple:
            if component_type == 'vin' and self.vin_placed:
                return False
            if component_type == 'vout' and self.vout_placed:
                return False
        
        # For single-pin components (vin/vout)
        if info.pin_count == 1:
            if not (self.WORK_START_ROW <= start_row <= self.WORK_END_ROW):
                return False
            if not self.is_empty(start_row, column):
                return False
            
            # CRITICAL FIX: Vin/Vout must be placed on a floating row.
            if not self.is_row_floating(start_row):
                return False

            return True
        
        # For multi-pin vertical components
        if info.vertical_only:
            end_row = start_row + info.pin_count - 1
            if not (self.WORK_START_ROW <= start_row and end_row <= self.WORK_END_ROW):
                return False
            
            # Check if all positions are empty
            for r in range(start_row, end_row + 1):
                if not self.is_empty(r, column):
                    return False
            
            # At least one pin must connect to a non-floating row
            has_connection = False
            for r in range(start_row, end_row + 1):
                if self.is_row_connected(r):
                    has_connection = True
                    break
            
            return has_connection
        
        return False

    def place_component(self, component_type: str, start_row: int, column: int) -> Optional[Component]:
        """Place a component on the breadboard"""
        if not self.can_place_component_at(component_type, start_row, column):
            return None

        info = COMPONENT_CATALOG[component_type]
        
        if info.pin_count == 1:
            pin_positions = [(start_row, column)]
        else:
            pin_positions = [(r, column) for r in range(start_row, start_row + info.pin_count)]

        self.component_counter += 1
        component = Component(type=component_type, pins=pin_positions, id=self.component_counter)
        self.placed_components.append(component)

        # Update grid and node connections
        for idx, (r, c) in enumerate(pin_positions):
            self.grid[r][c] = (component, idx)
            self.get_node(r).connected_pins.append((component, idx))

        # Track special components
        if component_type == 'vin':
            self.vin_placed = True
        elif component_type == 'vout':
            self.vout_placed = True

        return component

    def can_place_wire(self, row1: int, col1: int, row2: int, col2: int) -> bool:
        """Check if wire can be placed between two positions"""
        if row1 == row2:
            return False  # No wires within the same row
        
        # Both positions must be valid
        if not (0 <= row1 < self.ROWS and 0 <= col1 < self.COLUMNS):
            return False
        if not (0 <= row2 < self.ROWS and 0 <= col2 < self.COLUMNS):
            return False
        
        # Check for duplicate wire (normalize order)
        wire_key = tuple(sorted([(row1, col1), (row2, col2)]))
        if wire_key in self.placed_wires:
            return False
        
        # Check if positions are available for wiring
        pos1_available = (self.is_empty(row1, col1) or 
                         row1 == self.VSS_ROW or row1 == self.VDD_ROW)
        pos2_available = (self.is_empty(row2, col2) or 
                         row2 == self.VSS_ROW or row2 == self.VDD_ROW)
        
        if not (pos1_available and pos2_available):
            return False
        
        # At least one end must be connected to something (not floating)
        # Using fixed connectivity check
        row1_connected = (row1 == self.VSS_ROW or row1 == self.VDD_ROW or 
                         self.is_row_connected(row1))
        row2_connected = (row2 == self.VSS_ROW or row2 == self.VDD_ROW or 
                         self.is_row_connected(row2))
        
        return row1_connected or row2_connected

    def place_wire(self, row1: int, col1: int, row2: int, col2: int) -> Optional[Component]:
        """Place a wire connecting two positions"""
        if not self.can_place_wire(row1, col1, row2, col2):
            return None

        # Track this wire to prevent duplicates
        wire_key = tuple(sorted([(row1, col1), (row2, col2)]))
        self.placed_wires.add(wire_key)

        # Union the two rows in the connectivity graph
        self.union(row1, row2)
        
        pin_positions = [(row1, col1), (row2, col2)]
        self.component_counter += 1
        component = Component(type="wire", pins=pin_positions, id=self.component_counter)
        self.placed_components.append(component)

        # Update grid and connections (but not for power rails)
        for idx, (r, c) in enumerate(pin_positions):
            if r != self.VSS_ROW and r != self.VDD_ROW:  # Don't occupy power rail grid
                self.grid[r][c] = (component, idx)
            self.get_node(r).connected_pins.append((component, idx))

        return component

    def get_component_placement_actions(self, target_column: int) -> List[Tuple]:
        """Generate component placement actions"""
        actions = []
        
        for component_type, info in COMPONENT_CATALOG.items():
            if component_type == 'wire':
                continue
                
            # Check if we can still place this component type
            if not info.can_place_multiple:
                if component_type == 'vin' and self.vin_placed:
                    continue
                if component_type == 'vout' and self.vout_placed:
                    continue
            
            # For single-pin components (vin/vout)
            if info.pin_count == 1:
                for row in range(self.WORK_START_ROW, self.WORK_END_ROW + 1):
                    if self.can_place_component_at(component_type, row, target_column):
                        actions.append((component_type, row, target_column))
            else:
                # Multi-pin components
                max_start_row = self.WORK_END_ROW - info.pin_count + 1
                for row in range(self.WORK_START_ROW, max_start_row + 1):
                    if self.can_place_component_at(component_type, row, target_column):
                        actions.append((component_type, row, target_column))
        
        return actions

    def get_wire_actions(self, target_column: int) -> List[Tuple]:
        """Generate wire placement actions - enhanced with same-column connections"""
        actions = []
        
        # Get all existing component positions (left of target column)
        component_positions = []
        for col in range(target_column):  # Only look left of current column
            for row in range(self.ROWS):
                if not self.is_empty(row, col):
                    component_positions.append((row, col))
        
        # Also include power rail positions in target column for connections
        component_positions.append((self.VSS_ROW, target_column))
        component_positions.append((self.VDD_ROW, target_column))
        
        # Get empty positions in target column
        empty_positions = []
        for row in range(self.WORK_START_ROW, self.WORK_END_ROW + 1):
            if self.is_empty(row, target_column):
                empty_positions.append((row, target_column))
        
        # Wire from existing components to empty positions in target column
        for comp_row, comp_col in component_positions:
            for empty_row, empty_col in empty_positions:
                if self.can_place_wire(comp_row, comp_col, empty_row, empty_col):
                    actions.append(("wire", comp_row, comp_col, empty_row, empty_col))
        
        # Add same-column wiring within target column
        # Connect occupied positions to empty positions within the same column
        occupied_in_target = []
        for row in range(self.WORK_START_ROW, self.WORK_END_ROW + 1):
            if not self.is_empty(row, target_column):
                occupied_in_target.append((row, target_column))
        
        # Wire between occupied and empty positions in same column
        for occ_row, occ_col in occupied_in_target:
            for empty_row, empty_col in empty_positions:
                if self.can_place_wire(occ_row, occ_col, empty_row, empty_col):
                    actions.append(("wire", occ_row, occ_col, empty_row, empty_col))
        
        return actions

    def legal_actions(self) -> List[Tuple]:
        """Generate all legal actions"""
        actions: List[Tuple] = []

        # Get current placement column
        current_col = self.get_current_placement_column()
        if current_col is None:
            if self.is_complete_and_valid():
                actions.append(("STOP",))
            return actions

        # Component placement actions (no priority sorting - let MCTS decide)
        component_actions = self.get_component_placement_actions(current_col)
        actions.extend(component_actions)

        # Wire placement actions
        wire_actions = self.get_wire_actions(current_col)
        actions.extend(wire_actions)

        # STOP action if circuit is complete
        if self.is_complete_and_valid():
            actions.append(("STOP",))

        return actions

    def is_complete_and_valid(self) -> bool:
        """Check if circuit is complete and valid"""
        # Must have both VIN and VOUT placed
        if not (self.vin_placed and self.vout_placed):
            return False
        
        # Find VIN and VOUT components
        vin_component = None
        vout_component = None
        for comp in self.placed_components:
            if comp.type == 'vin':
                vin_component = comp
            elif comp.type == 'vout':
                vout_component = comp
        
        if not (vin_component and vout_component):
            return False
        
        # Check if VIN and VOUT are connected (in same net using union-find)
        vin_row = vin_component.pins[0][0]
        vout_row = vout_component.pins[0][0]
        
        return self.find(vin_row) == self.find(vout_row)

    def get_circuit_complexity(self) -> int:
        """Return circuit complexity score"""
        regular_components = len([c for c in self.placed_components 
                                if c.type not in ['wire', 'vin', 'vout']])
        wire_count = len([c for c in self.placed_components if c.type == 'wire'])
        unique_types = len(set(c.type for c in self.placed_components 
                             if c.type not in ['wire', 'vin', 'vout']))
        
        return regular_components * 10 + wire_count * 2 + unique_types * 5

    def apply_action(self, action: Tuple) -> bool:
        """Apply an action to the breadboard"""
        if not action:
            return False
            
        if action[0] == "STOP":
            return self.is_complete_and_valid()
        elif action[0] == "wire":
            if len(action) != 5:
                return False
            _, row1, col1, row2, col2 = action
            return self.place_wire(row1, col1, row2, col2) is not None
        else:
            if len(action) != 3:
                return False
            component_type, row, col = action
            return self.place_component(component_type, row, col) is not None

    def clone(self) -> "Breadboard":
        """Create a deep copy of the breadboard"""
        new_board = Breadboard()
        new_board.grid = copy.deepcopy(self.grid)
        new_board.nodes = copy.deepcopy(self.nodes)
        new_board.placed_components = copy.deepcopy(self.placed_components)
        new_board.component_counter = self.component_counter
        new_board.uf_parent = self.uf_parent[:]
        new_board.vin_placed = self.vin_placed
        new_board.vout_placed = self.vout_placed
        new_board.placed_wires = self.placed_wires.copy()
        return new_board

    def get_netlist(self) -> Dict[int, List[Tuple[str, str]]]:
        """Generate netlist with component and pin details"""
        netlist = {}
        for node in self.nodes:
            if node.connected_pins or node.node_type != NodeType.NORMAL:
                net_id = self.find(node.row_index)
                if net_id not in netlist:
                    netlist[net_id] = []
                    # Add net type based on what's in this net
                    net_root_node = self.get_node(net_id)
                    if net_root_node.node_type == NodeType.VSS:
                        netlist[net_id].append(("VSS", ""))
                    elif net_root_node.node_type == NodeType.VDD:
                        netlist[net_id].append(("VDD", ""))
                
                for comp, pin_idx in node.connected_pins:
                    info = COMPONENT_CATALOG.get(comp.type)
                    pin_name = (info.pin_names[pin_idx] if info and pin_idx < len(info.pin_names) 
                              else f"pin{pin_idx}")
                    netlist[net_id].append((f"{comp.type}_{comp.id}", pin_name))
        
        return netlist

    def __hash__(self) -> int:
        """Hash for state comparison"""
        sorted_components = tuple(sorted(
            (comp.type, tuple(sorted(comp.pins))) for comp in self.placed_components
        ))
        return hash((sorted_components, self.vin_placed, self.vout_placed))

    def __eq__(self, other: object) -> bool:
        """Equality based on component placement"""
        return isinstance(other, Breadboard) and hash(self) == hash(other)

    def __str__(self) -> str:
        """String representation"""
        result = f"Breadboard {self.ROWS}x{self.COLUMNS} - Complexity: {self.get_circuit_complexity()}\n"
        result += f"VSS: row {self.VSS_ROW}, VDD: row {self.VDD_ROW}\n"
        result += f"VIN placed: {self.vin_placed}, VOUT placed: {self.vout_placed}\n"
        result += f"Components: {len(self.placed_components)}\n"
        
        # Component breakdown
        comp_types = {}
        for comp in self.placed_components:
            comp_types[comp.type] = comp_types.get(comp.type, 0) + 1
        result += f"Types: {comp_types}\n"
        
        # Circuit completion status
        result += f"Circuit complete: {self.is_complete_and_valid()}\n"
        
        return result


# ============================================================
# Test Function
# ============================================================

def test_connectivity_fixes():
    """Test the connectivity fixes"""
    print("Testing Connectivity Fixes...")
    
    b = Breadboard()
    print(f"Board: {b.ROWS}x{b.COLUMNS}")
    print(f"VSS: row {b.VSS_ROW}, VDD: row {b.VDD_ROW}")
    print(f"Working area: rows {b.WORK_START_ROW}-{b.WORK_END_ROW}")
    
    # Test 1: Place VIN on row 5
    print("\n=== Test 1: Place VIN ===")
    success = b.place_component('vin', 5, 0)
    print(f"VIN placed on (5,0): {success is not None}")
    print(f"Row 5 connected: {b.is_row_connected(5)}")
    print(f"Row 5 floating: {b.is_row_floating(5)}")
    
    # Test 2: Place wire from row 5 to row 10
    print("\n=== Test 2: Place wire (5,0) -> (10,0) ===")
    success = b.place_wire(5, 0, 10, 0)
    print(f"Wire placed: {success is not None}")
    print(f"Row 5 find: {b.find(5)}, Row 10 find: {b.find(10)}")
    print(f"Row 10 connected: {b.is_row_connected(10)}")  # Should be True now
    print(f"Row 10 floating: {b.is_row_floating(10)}")   # Should be False now
    
    # Test 3: Try to place resistor connecting to row 10 (should work now)
    print("\n=== Test 3: Place resistor on rows 10-11 ===")
    actions = b.legal_actions()
    resistor_actions = [a for a in actions if a[0] == 'resistor' and a[1] == 10]
    print(f"Resistor actions at row 10: {len(resistor_actions)}")
    if resistor_actions:
        success = b.apply_action(resistor_actions[0])
        print(f"Resistor placed: {success}")
        print(f"Row 11 connected: {b.is_row_connected(11)}")
    
    # Test 4: Test duplicate wire prevention
    print("\n=== Test 4: Try duplicate wire ===")
    duplicate_success = b.place_wire(5, 0, 10, 0)
    print(f"Duplicate wire placed: {duplicate_success is not None}")  # Should be False
    
    # Test 5: Power rail connection
    print("\n=== Test 5: Connect to power rail ===")
    power_wire = b.place_wire(11, 0, b.VDD_ROW, 0)
    print(f"Power wire placed: {power_wire is not None}")
    print(f"Row 11 find: {b.find(11)}, VDD find: {b.find(b.VDD_ROW)}")
    
    print(f"\nFinal state:")
    print(b)
    print(f"Netlist: {b.get_netlist()}")


def test_new_breadboard():
    """Test the new breadboard design"""
    print("Testing New Breadboard Design...")
    
    b = Breadboard()
    print(f"Board: {b.ROWS}x{b.COLUMNS}")
    print(f"VSS: row {b.VSS_ROW}, VDD: row {b.VDD_ROW}")
    print(f"Working area: rows {b.WORK_START_ROW}-{b.WORK_END_ROW}")
    
    initial_actions = b.legal_actions() 
    print(f"Initial legal actions: {len(initial_actions)}")
    
    # Show action breakdown
    action_types = {}
    for action in initial_actions:
        action_types[action[0]] = action_types.get(action[0], 0) + 1
    print(f"Action types: {action_types}")
    
    # Test circuit construction
    print("\nBuilding a simple circuit...")
    
    # 1. Place VIN first (must connect to floating row)
    vin_actions = [a for a in initial_actions if a[0] == 'vin']
    if vin_actions:
        print(f"1. Placing VIN: {vin_actions[0]}")
        b.apply_action(vin_actions[0])
        print(f"   VIN placed: {b.vin_placed}")
    
    # 2. Place a resistor connecting to VIN
    actions = b.legal_actions()
    resistor_actions = [a for a in actions if a[0] == 'resistor']
    if resistor_actions:
        print(f"2. Placing resistor: {resistor_actions[0]}")
        b.apply_action(resistor_actions[0])
    
    # 3. Place VOUT on a connected row (should work with relaxed rules)
    actions = b.legal_actions()
    vout_actions = [a for a in actions if a[0] == 'vout']
    if vout_actions:
        print(f"3. Placing VOUT: {vout_actions[0]}")
        b.apply_action(vout_actions[0])
        print(f"   VOUT placed: {b.vout_placed}")
    
    # 4. Connect with power rails
    actions = b.legal_actions()
    wire_actions = [a for a in actions if a[0] == 'wire']
    print(f"4. Available wire actions: {len(wire_actions)}")
    if wire_actions:
        # Find a power rail connection
        power_wires = [a for a in wire_actions if 
                      a[1] in [b.VSS_ROW, b.VDD_ROW] or a[3] in [b.VSS_ROW, b.VDD_ROW]]
        if power_wires:
            print(f"   Power wire action: {power_wires[0]}")
            b.apply_action(power_wires[0])
    
    print(f"\nFinal state:")
    print(b)
    print(f"Circuit complete: {b.is_complete_and_valid()}")
    print(f"Netlist: {b.get_netlist()}")


if __name__ == "__main__":
    test_connectivity_fixes()
    print("\n" + "="*50 + "\n")
    test_new_breadboard()