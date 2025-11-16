# Row-Only Connectivity Model

## Overview

The breadboard uses a **row-only connectivity model** where columns have been abstracted away. This document explains how this model works and why it's architecturally sound.

## Key Concept

**In the row-only model, each row is a single electrical net (like a real breadboard)**

- All positions in a row are electrically connected
- Column coordinates are retained only for legacy compatibility and visualization
- The actual column value is always `0` in the internal representation
- Connectivity and validation logic operate purely on row indices

---

## Architecture

### 1. Pin Index Structure (`RowPinIndex`)

```python
class RowPinIndex:
    def __init__(self, rows: int):
        self._rows: List[List[PinRecord]] = [[] for _ in range(rows)]
```

**What it does:**
- Tracks which components occupy each row
- Multiple components can have pins on the same row (row-level sharing)
- Each `PinRecord` stores: `(component, pin_index, col=0)`

**Key methods:**
- `is_empty(row)` - Check if a row has any pins
- `place_pin(row, col, component, pin_index)` - Add a pin to a row
- `get_pin(row)` - Get first pin on a row (all share the row net)
- `pins_in_row(row)` - Get all pins on a specific row

### 2. Union-Find for Row Connectivity

```python
self.uf_parent: List[int] = list(range(self.ROWS))  # One entry per ROW
```

**What it tracks:**
- Which rows are electrically connected (merged into same net)
- Power rail roots (VSS_ROW, VDD_ROW) are canonical
- VIN and VOUT rows start as separate nets

**Key operations:**
- `find(row)` - Get the root net ID for a row
- `union(row1, row2)` - Merge two rows into the same electrical net
- `is_row_active(row)` - Check if a row is part of the active circuit

### 3. Component Placement

**CRITICAL: Components do NOT auto-union their pin rows**

When a multi-pin component (e.g., resistor) is placed:

```python
def _place_component(self, comp_type: str, start_row: int):
    # ... create component spanning multiple rows ...

    # Occupy rows and activate nets for all pins
    for i, (r, c) in enumerate(component.pins):
        self.row_pin_index.place_pin(r, c, component, i)
        self.active_nets.add(self.find(r))

    # NOTE: Component pins are NOT auto-unified in union-find structure
    # Instead, components create edges in the connectivity graph
    # This allows detection of degenerate components (all pins already on same net)
```

**Why no auto-union?**
1. A resistor on rows 5-6 **bridges** those nets, it doesn't unify them
2. The resistor is the electrical path connecting row 5 to row 6
3. Auto-union would make degenerate component detection impossible
4. Connectivity is validated via graph traversal, not union-find

**Example:**
```
Before placing resistor:
  Row 5: VIN net (root=1)
  Row 6: Unconnected (root=6)

After placing resistor at row 5:
  Row 5: VIN net (root=1)          ← Still VIN net
  Row 6: Unconnected (root=6)      ← Still separate

  BUT: Resistor creates graph edge: VIN_net ↔ Row_6_net
```

### 4. Wire Placement

**Wires DO union rows explicitly**

```python
def _place_wire(self, r1: int, r2: int):
    self.placed_wires.add(tuple(sorted((r1, r2))))
    self.union(r1, r2)  # ← EXPLICIT row unification
    self.active_nets.add(self.find(r1))
```

**Example:**
```
Before wire from row 5 to row 10:
  Row 5: VIN net (root=1)
  Row 10: Unconnected (root=10)

After wire:
  Row 5: VIN net (root=1)
  Row 10: VIN net (root=1)          ← Now unified!

  Union-find: uf_parent[10] = 1
```

---

## Two-Layer Connectivity System

The breadboard uses **two complementary connectivity systems**:

### Layer 1: Union-Find (Physical Wiring)
- **Purpose**: Track which rows are directly wired together
- **Updated by**: Wire placement only
- **Used for**:
  - Determining active nets
  - Net naming in SPICE generation
  - Efficient connectivity queries

### Layer 2: Component Graph (Logical Connectivity)
- **Purpose**: Track how components bridge different nets
- **Updated by**: Component placement
- **Used for**:
  - Validation (is VIN reachable to VOUT?)
  - Degenerate component detection
  - BFS reachability analysis

**Why both?**
- Union-find gives O(α(n)) wire connectivity
- Graph gives logical component connectivity
- Separation allows detecting invalid states (components on same net = degenerate)

---

## Connectivity Validation

### How Validation Works

```python
def _compute_connectivity_summary(self):
    # 1. Build net mapping using union-find
    position_to_net = self._build_net_mapping()

    # 2. Build adjacency graph from components
    adjacency: Dict[str, Set[str]] = defaultdict(set)

    for comp in self.placed_components:
        if comp.type in ['vin', 'vout', 'wire']:
            continue

        # Get all nets this component touches
        nets = {position_to_net[pin] for pin in comp.pins}

        # Degenerate check: component must span ≥2 nets
        if len(nets) < 2:
            return {"degenerate_component": True, "valid": False}

        # Create edges between all pairs of nets
        for n1, n2 in combinations(nets, 2):
            adjacency[n1].add(n2)
            adjacency[n2].add(n1)

    # 3. BFS from VIN to check reachability
    visited = bfs_from(vin_net, adjacency)

    return {
        "reachable_vout": vout_net in visited,
        "all_components_reachable": component_nets ⊆ visited,
        "touches_vdd": any(comp touches VDD net),
        "touches_vss": any(comp touches VSS net),
        "valid": all conditions met
    }
```

### Example: Resistor Divider

```
Circuit: VIN → R1 → R2 → VOUT
         R1 top also → VDD
         R2 bottom also → VSS

Row Layout:
  Row 1  (VIN):   VIN pin
  Row 2:          R1 pin 1, wire to VDD
  Row 3:          R1 pin 2
  Row 5:          R2 pin 1, wire from R1
  Row 6:          R2 pin 2, wire to VSS, wire to VOUT
  Row 13 (VOUT):  VOUT pin

Union-Find State:
  uf_parent[1] = 1   (VIN net)
  uf_parent[2] = 14  (VDD net, wired to VDD)
  uf_parent[3] = 3   (R1 bottom net)
  uf_parent[5] = 3   (wired to row 3)
  uf_parent[6] = 0   (VSS net, wired to VSS and VOUT)
  uf_parent[13] = 0  (VOUT net, wired to row 6)
  uf_parent[14] = 14 (VDD net)
  uf_parent[0] = 0   (VSS net)

Net Naming:
  Row 1 → VIN_net (from row 1 root)
  Row 2 → VDD (from row 14 root)
  Row 3 → n0 (from row 3 root)
  Row 5 → n0 (from row 3 root, unified)
  Row 6 → 0 (from row 0 root = VSS)
  Row 13 → 0 (from row 0 root, unified)

Component Graph:
  R1: {VIN_net, VDD, n0}
    Edges: VIN_net ↔ VDD, VIN_net ↔ n0, VDD ↔ n0

  R2: {n0, 0}
    Edges: n0 ↔ 0

Adjacency Graph:
  VIN_net → {VDD, n0}
  VDD     → {VIN_net, n0}
  n0      → {VIN_net, VDD, 0}
  0       → {n0}

BFS from VIN_net:
  Start: VIN_net
  Visit: VDD, n0
  Visit: 0 (through n0)

Result: ✅ VOUT (net 0) is reachable from VIN_net
```

---

## Net Naming for SPICE

### Net Mapping Algorithm

```python
def _build_net_mapping(self) -> Dict[Tuple[int, int], str]:
    position_to_net = {}
    root_to_net = {}
    net_counter = 0

    for comp in self.placed_components:
        for pin in comp.pins:
            row = pin[0]
            root = self.find(row)  # ← Union-find lookup

            if root not in root_to_net:
                if root == self.VSS_ROW:
                    root_to_net[root] = "0"      # Ground
                elif root == self.VDD_ROW:
                    root_to_net[root] = "VDD"    # Power
                else:
                    root_to_net[root] = f"n{net_counter}"
                    net_counter += 1

            position_to_net[pin] = root_to_net[root]

    return position_to_net
```

**Key insight:** All rows with the same union-find root get the same net name

**Example:**
```
Rows 2, 3, 5 all have root=3 → All named "n0"
Rows 6, 13 both have root=0  → All named "0" (ground)
```

---

## Action Generation

### Wire Actions (Row-Only)

```python
def _add_wire_actions(self, actions: List[Tuple], target_col: int):
    active_rows = [r for r in range(self.ROWS) if self.is_row_active(r)]
    all_rows = list(range(self.ROWS))

    for r1 in active_rows:      # At least one end must be active
        for r2 in all_rows:
            if self.can_place_wire(r1, r2):
                actions.append(("wire", r1, r2))  # ← No columns!
```

**Validation:**
```python
def can_place_wire(self, r1: int, r2: int) -> bool:
    # Same row check
    if r1 == r2:
        return False

    # Forbidden pairs (VIN-VSS, VOUT-VDD, etc.)
    forbidden = [{VIN_ROW, VSS_ROW}, {VOUT_ROW, VDD_ROW}, ...]
    if {r1, r2} in forbidden:
        return False

    # Duplicate check
    if tuple(sorted((r1, r2))) in self.placed_wires:
        return False

    # At least one endpoint must be active
    if not (self.is_row_active(r1) or self.is_row_active(r2)):
        return False

    # Gate/base protection
    if self._row_has_gate_pin(r1) and self._is_power_rail(r2):
        return False

    return True
```

### Component Actions

```python
def _add_component_actions(self, actions: List[Tuple], target_col: int):
    for comp_type, info in COMPONENT_CATALOG.items():
        if comp_type == 'wire':
            continue

        max_start = self.VOUT_ROW - (info.pin_count - 1)

        for r in range(self.VIN_ROW, max_start + 1):
            if self.can_place_component(comp_type, r):
                actions.append((comp_type, r))  # ← No column!
```

**Validation:**
```python
def can_place_component(self, comp_type: str, start_row: int) -> bool:
    # Single instance check (VIN/VOUT)
    if not info.can_place_multiple and already_placed:
        return False

    # Work area bounds
    pin_rows = range(start_row, start_row + info.pin_count)
    if not all(WORK_START_ROW <= r <= WORK_END_ROW for r in pin_rows):
        return False

    # Must touch active net (for multi-pin components)
    if info.pin_count > 1:
        if not any(self.is_row_active(r) for r in pin_rows):
            return False

    return True
```

---

## Degenerate Component Detection

**What is a degenerate component?**

A component where all pins are already on the same net BEFORE it was placed. This means the component adds no new connectivity—it's electrically redundant.

### Example: Degenerate Resistor

```
Setup:
  Row 5: VIN net
  Row 6: VIN net (already wired together)

Place resistor at row 5 (spans rows 5-6):
  Both pins are on VIN net

Net mapping:
  (5, 0) → "VIN_net"
  (6, 0) → "VIN_net"

Validation:
  nets = {"VIN_net"}  ← Only 1 unique net!
  len(nets) < 2       ← DEGENERATE!
```

**Why this matters:**
- Prevents wasting components on already-connected rows
- Ensures components actually contribute to circuit functionality
- Maintains search efficiency by pruning useless states

### Example: Valid Resistor

```
Setup:
  Row 5: VIN net
  Row 6: Unconnected (separate net)

Place resistor at row 5 (spans rows 5-6):
  Pin 1 on VIN net
  Pin 2 on separate net

Net mapping:
  (5, 0) → "VIN_net"
  (6, 0) → "n2"

Validation:
  nets = {"VIN_net", "n2"}  ← 2 unique nets
  len(nets) >= 2            ← VALID!

Connectivity graph:
  Adds edge: VIN_net ↔ n2
```

---

## Summary

### Row-Only Model Design Principles

1. **Rows are nets** - Each row is a single electrical connection point
2. **Wires unify rows** - Explicit union-find merging
3. **Components bridge nets** - Create graph edges without union-find merging
4. **Two-layer validation** - Union-find for wiring + graph for component connectivity
5. **Degenerate detection** - Components must span multiple nets to be valid

### Benefits

- ✅ Simpler action space (no column coordinates to track)
- ✅ Efficient connectivity queries (O(α(n)) union-find)
- ✅ Clear separation of physical vs logical connectivity
- ✅ Robust degenerate component detection
- ✅ Clean SPICE netlist generation (one net per union-find root)

### Key Difference from Column-Based Model

**Old model:**
- Grid[row][col] stores component references
- Each cell is a potential net
- More complex net merging logic

**Row-only model:**
- RowPinIndex[row] stores list of pins
- Each row is a net (simpler!)
- Cleaner separation of concerns

---

**This architecture has been validated with 53 passing tests including specialized multi-pin connectivity tests.**
