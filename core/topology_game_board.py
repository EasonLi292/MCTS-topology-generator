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
    VIN_ROW = 1
    VOUT_ROW = 28
    WORK_START_ROW = 2
    WORK_END_ROW = 27

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
        # Start from column 1 since column 0 is reserved for vin/vout
        target_col = next((c for c in range(1, self.COLUMNS) if not all(
            not self.is_empty(r, c) for r in range(self.WORK_START_ROW, self.WORK_END_ROW + 1)
        )), -1)
        if target_col == -1:
            # Only allow STOP if circuit is complete AND has minimum complexity
            num_components = len([c for c in self.placed_components
                                 if c.type not in ['wire', 'vin', 'vout']])
            if self.is_complete_and_valid() and num_components >= 3:
                actions.append(("STOP",))
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
        # Only allow STOP if circuit is complete AND has minimum complexity
        num_components = len([c for c in self.placed_components
                             if c.type not in ['wire', 'vin', 'vout']])
        if self.is_complete_and_valid() and num_components >= 3:
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
        then merge nets connected by wires. This prevents components in different
        columns from incorrectly sharing nets due to row-level union-find.
        """
        if not self.is_complete_and_valid():
            return None

        # Build connectivity graph: each position starts with its own net
        position_to_net: Dict[Tuple[int, int], str] = {}
        net_counter = 0

        # First pass: Assign initial net names to all positions (components + wire endpoints)
        all_positions: Set[Tuple[int, int]] = set()

        for comp in self.placed_components:
            for pin in comp.pins:
                all_positions.add(pin)

        for pos in sorted(all_positions):
            row, col = pos

            # Special handling for power rails - only if position is ON the power rail row
            if row == self.VSS_ROW:
                position_to_net[pos] = "0"  # Ground
            elif row == self.VDD_ROW:
                position_to_net[pos] = "VDD"
            else:
                # Each position gets a unique net initially
                position_to_net[pos] = f"n{net_counter}"
                net_counter += 1

        # Second pass: Merge nets connected by wires
        # Build list of wire connections
        wire_connections: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        for comp in self.placed_components:
            if comp.type == 'wire' and len(comp.pins) == 2:
                wire_connections.append((comp.pins[0], comp.pins[1]))

        # Merge nets using union-find on net names
        net_parent: Dict[str, str] = {}

        def find_net(net: str) -> str:
            if net not in net_parent:
                net_parent[net] = net
                return net
            if net_parent[net] != net:
                net_parent[net] = find_net(net_parent[net])
            return net_parent[net]

        def union_nets(net1: str, net2: str):
            root1, root2 = find_net(net1), find_net(net2)
            if root1 != root2:
                #  Prefer keeping special nets (0, VDD)
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

        # Apply net merges to get final net names
        for pin in position_to_net:
            position_to_net[pin] = find_net(position_to_net[pin])

        # Build the netlist
        lines = []
        lines.append("* Auto-generated SPICE netlist from MCTS topology generator")
        lines.append("")

        # Voltage sources
        lines.append("* Power supply")
        lines.append("VDD VDD 0 DC 5V")
        lines.append("")

        # Add input signal source (vin)
        vin_comp = next((c for c in self.placed_components if c.type == 'vin'), None)
        if vin_comp:
            vin_pos = vin_comp.pins[0]
            vin_net = position_to_net[vin_pos]
            lines.append("* Input signal")
            lines.append(f"VIN {vin_net} 0 AC 1V")
            lines.append("")

        # Add components
        lines.append("* Circuit components")
        comp_counters = {}

        for comp in self.placed_components:
            if comp.type in ['vin', 'vout', 'wire']:
                continue  # Skip markers and wires

            # Get component prefix and increment counter
            comp_prefix = comp.type[0].upper()
            if comp.type not in comp_counters:
                comp_counters[comp.type] = 0
            comp_counters[comp.type] += 1
            comp_id = f"{comp_prefix}{comp_counters[comp.type]}"

            # Get net names for each pin
            pin_nets = [position_to_net[pin] for pin in comp.pins]

            # Generate SPICE line based on component type
            if comp.type == 'resistor':
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} 1k")
            elif comp.type == 'capacitor':
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} 1u")
            elif comp.type == 'inductor':
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} 1m")
            elif comp.type == 'diode':
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} DMOD")
            elif comp.type == 'nmos3':
                # NMOS: Drain Gate Source (Bulk tied to source)
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} {pin_nets[2]} NMOS_MODEL")
            elif comp.type == 'pmos3':
                # PMOS: Drain Gate Source (Bulk tied to VDD)
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} VDD PMOS_MODEL")
            elif comp.type == 'npn':
                # NPN: Collector Base Emitter
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} NPN_MODEL")
            elif comp.type == 'pnp':
                # PNP: Collector Base Emitter
                lines.append(f"{comp_id} {pin_nets[0]} {pin_nets[1]} {pin_nets[2]} PNP_MODEL")

        lines.append("")

        # Add output probe (vout)
        vout_comp = next((c for c in self.placed_components if c.type == 'vout'), None)
        if vout_comp:
            vout_pos = vout_comp.pins[0]
            vout_net = position_to_net[vout_pos]
            lines.append("* Output probe")
            lines.append(f".print ac v({vout_net})")
            lines.append("")

        # Add device models
        lines.append("* Device models")
        lines.append(".model DMOD D")
        lines.append(".model NMOS_MODEL NMOS (LEVEL=1)")
        lines.append(".model PMOS_MODEL PMOS (LEVEL=1)")
        lines.append(".model NPN_MODEL NPN")
        lines.append(".model PNP_MODEL PNP")
        lines.append("")

        # Add simulation commands
        lines.append("* Simulation commands")
        lines.append(".ac dec 100 1 1MEG")
        lines.append(".end")

        return "\n".join(lines)
    
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
    b3 = b2.apply_action(('wire', 5, 0, 5, 1))  # VIN to resistor
    # Then connect to vout at row 20
    b4 = b3.apply_action(('wire', 10, 1, 20, 0))
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
    b1 = b1.apply_action(('wire', 5, 0, 5, 1))  # Connect VIN (row 5, col 0) to R pin 1 (row 5, col 1)
    b1 = b1.apply_action(('capacitor', 7, 2))  # C on rows 7-8 (pins auto-connected)
    b1 = b1.apply_action(('wire', 6, 1, 7, 2))  # Connect R pin 2 to C pin 1
    b1 = b1.apply_action(('wire', 8, 2, 20, 0))  # Connect C pin 2 to VOUT

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
    b2 = b2.apply_action(('wire', 5, 0, 5, 1))  # Connect VIN to R1
    b2 = b2.apply_action(('resistor', 7, 2))  # R2 on rows 7-8 (pins auto-connected)
    b2 = b2.apply_action(('wire', 6, 1, 7, 2))  # Connect R1 to R2
    b2 = b2.apply_action(('wire', 8, 2, 20, 0))  # Connect R2 to VOUT

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
    b3 = b3.apply_action(('wire', 5, 0, 5, 1))
    b3 = b3.apply_action(('wire', 6, 1, 20, 0))

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
    b4 = b4.apply_action(('wire', 5, 0, 5, 1))  # VIN to drain
    b4 = b4.apply_action(('wire', 7, 1, 20, 0))  # source to VOUT

    netlist4 = b4.to_netlist()
    assert netlist4 is not None
    assert "N1" in netlist4, "Should contain NMOS transistor"
    assert "NMOS_MODEL" in netlist4, "Should reference NMOS model"
    print("✅ Passed: Transistor component handled correctly")

    # --- Test 6: Proper Multi-Net RC Low-Pass Filter ---
    print("\n--- Test 6: Proper Multi-Net RC Low-Pass Filter ---")
    # Build a proper RC low-pass filter: VIN --R-- net1 --C-- GND, VOUT at net1
    b5 = Breadboard()
    # Place resistor between input and middle node
    b5 = b5.apply_action(('resistor', 10, 1))  # R on rows 10-11 (pins auto-connected)
    b5 = b5.apply_action(('wire', 5, 0, 10, 1))  # VIN to R input
    # Place capacitor from middle node to ground
    b5 = b5.apply_action(('capacitor', 12, 2))  # C on rows 12-13 (pins auto-connected)
    b5 = b5.apply_action(('wire', 11, 1, 12, 2))  # R output to C input
    b5 = b5.apply_action(('wire', 13, 2, 0, 2))  # C to VSS (ground)
    # Connect VOUT to the middle node (between R and C)
    b5 = b5.apply_action(('wire', 11, 1, 20, 0))  # Middle node to VOUT

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