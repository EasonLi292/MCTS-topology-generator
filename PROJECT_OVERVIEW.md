# MCTS Circuit Topology Generator - Technical Overview

## Project Summary

This project implements a **Monte Carlo Tree Search (MCTS)** algorithm to automatically generate analog circuit topologies. The system explores the space of possible circuit configurations, placing components (resistors, capacitors, transistors, etc.) on a virtual breadboard and connecting them with wires, with the goal of finding valid circuits that connect an input signal to an output.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Key Components](#key-components)
3. [MCTS Algorithm Details](#mcts-algorithm-details)
4. [Breadboard State Representation](#breadboard-state-representation)
5. [Reward System](#reward-system)
6. [Pseudocode](#pseudocode)
7. [Challenges and Solutions](#challenges-and-solutions)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Main Entry Point                      │
│                     (main.py)                            │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              MCTS Search Engine                          │
│                  (MCTS.py)                               │
│  • Tree traversal (Selection)                            │
│  • Node expansion (Expansion)                            │
│  • State evaluation (Simulation)                         │
│  • Value backpropagation (Backpropagation)              │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           Breadboard State Manager                       │
│         (topology_game_board.py)                         │
│  • Circuit state representation                          │
│  • Legal action generation                               │
│  • Component placement rules                             │
│  • Connectivity tracking (Union-Find)                    │
│  • SPICE netlist generation                             │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           SPICE Simulator Interface                      │
│           (spice_simulator.py)                           │
│  • AC analysis simulation                                │
│  • Circuit performance evaluation                        │
│  • Reward calculation                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Breadboard Grid Structure

The virtual breadboard is a **30×8 grid** with the following layout:

```
Row  0: VSS (Ground)           [Reserved - always available]
Row  1: VIN (Input Signal)     [Reserved - input node]
Rows 2-27: Component Work Area [Available for component placement]
Row 28: VOUT (Output Signal)   [Reserved - output node]
Row 29: VDD (Power Supply)     [Reserved - always available]
```

**Design Rationale:**
- Reserved rows ensure consistent power/ground/I/O availability
- Columns 0 contains VIN/VOUT markers
- Columns 1-7 are used for circuit components
- Column-by-column placement reduces search space by preventing symmetric duplicates

### 2. Available Components

The component catalog includes:

| Component Type | Pins | Description | SPICE Model |
|---------------|------|-------------|-------------|
| Resistor | 2 | Passive, 1kΩ | R |
| Capacitor | 2 | Passive, 1µF | C |
| Inductor | 2 | Passive, 1mH | L |
| Diode | 2 | Anode/Cathode | D (DMOD) |
| NMOS | 3 | Drain/Gate/Source | M (NMOS_MODEL) |
| PMOS | 3 | Drain/Gate/Source | M (PMOS_MODEL) |
| NPN Transistor | 3 | Collector/Base/Emitter | Q (NPN_MODEL) |
| PNP Transistor | 3 | Collector/Base/Emitter | Q (PNP_MODEL) |
| Wire | 2 | Connects two nodes | (connectivity only) |

### 3. State Representation

Each breadboard state maintains:

- **Grid occupancy**: 2D array tracking which components occupy which positions
- **Placed components**: List of all components with their pin positions
- **Union-Find structure**: Tracks which rows are electrically connected
- **Active nets**: Set of nets that have at least one component connected
- **Wire tracking**: Prevents duplicate wire placement

---

## MCTS Algorithm Details

### Four Phases of MCTS

```
        ┌──────────────┐
        │  Root Node   │
        │  (Initial    │
        │  Breadboard) │
        └──────┬───────┘
               │
         (1) SELECTION
               │
               ▼
        ┌──────────────┐
        │ Select child │
        │ using UCT    │──┐ Repeat until
        └──────┬───────┘  │ leaf node found
               │          │
               └──────────┘
               │
         (2) EXPANSION
               │
               ▼
        ┌──────────────┐
        │ Create new   │
        │ child node   │
        │ (new action) │
        └──────┬───────┘
               │
         (3) SIMULATION
               │
               ▼
        ┌──────────────┐
        │ Evaluate     │
        │ state with   │
        │ heuristic or │
        │ SPICE        │
        └──────┬───────┘
               │
      (4) BACKPROPAGATION
               │
               ▼
        ┌──────────────┐
        │ Update wins/ │
        │ visits back  │
        │ to root      │
        └──────────────┘
```

### Upper Confidence Bound for Trees (UCT)

The algorithm selects which child node to explore using the UCT formula:

```
UCT(node) = exploitation + exploration
          = (wins / visits) + c × sqrt(ln(parent_visits) / visits)
```

Where:
- `wins / visits`: Average reward from this node (exploitation)
- `c`: Exploration constant (default: 1.0)
- `sqrt(ln(parent_visits) / visits)`: Exploration bonus for less-visited nodes

**This balances:**
- **Exploitation**: Choosing nodes with high historical rewards
- **Exploration**: Trying less-visited nodes that might be better

---

## Breadboard State Representation

### Connectivity Model

The system uses **Union-Find (Disjoint Set Union)** to track electrical connectivity:

```
Breadboard rows are electrical nodes
    │
    ├─ Component pins on same row are implicitly connected
    │
    ├─ Component pins are auto-unioned (multi-pin components)
    │
    └─ Wires explicitly union two rows
```

**Example:**
```
Row 5: VIN ──┐
Row 6:       ├─ (Resistor pins auto-connected)
Row 7:       │
Row 8:       └─ (Wire connects row 6 to row 8)
Row 9: VOUT ─┘
```

After placement:
- `union(5, 6)`: Resistor pins connected
- `union(6, 8)`: Wire connects resistor to row 8
- `find(5) == find(9)`: Circuit is complete!

### Legal Action Generation

Actions are constrained to maintain search efficiency:

1. **Column-by-column placement**: Components must be placed in the leftmost empty column
2. **Connectivity requirement**: Components can only be placed if at least one pin connects to an active net
3. **No duplicate wires**: Same wire cannot be placed twice
4. **Boundary checks**: Components must fit within work area (rows 2-27)

**Legal Actions:**
```
actions = {
    component_placements: [
        (component_type, start_row, column)
        for each component type
        for each valid starting row
        if placement_is_valid()
    ],
    wire_placements: [
        (wire, row1, col1, row2, col2)
        for each active_row_position
        for each target_position
        if not duplicate and row1 ≠ row2
    ],
    stop_action: [
        (STOP,) if circuit_is_complete() and num_components ≥ 3
    ]
}
```

---

## Reward System

The reward system uses a **two-tier approach**: heuristic rewards for incomplete circuits, and SPICE simulation rewards for complete circuits.

### Heuristic Rewards (Incomplete Circuits)

```
heuristic_reward = component_reward
                 + diversity_reward
                 + connection_bonus

Where:
  component_reward = num_components × 5.0
  diversity_reward = num_unique_types × 8.0

  connection_bonus = {
    +20.0  if VIN-VOUT connected AND num_components > 0
    +5.0   if VIN-VOUT connected AND num_components = 0
    -2.0   if VIN-VOUT not connected
  }
```

**Design Rationale:**
- **Component diversity**: Encourages trying different component types
- **Connection bonus**: Strongly rewards connecting input to output
- **Penalty for empty circuits**: Prevents trivial direct VIN→VOUT connection
- **Positive bias**: All rewards kept positive to avoid "poisoning" the search tree

### SPICE Simulation Rewards (Complete Circuits)

For circuits with **3+ components** that connect VIN to VOUT:

```
spice_reward = base_spice_score + complexity_bonus

Where:
  base_spice_score = calculate_reward_from_simulation(freq, vout)
  complexity_bonus = (num_unique_types × 5.0) + (num_components × 2.0)
```

The SPICE simulator:
1. Generates a netlist from the breadboard state
2. Runs AC analysis (1 Hz to 1 MHz)
3. Evaluates output voltage characteristics
4. Returns a performance-based reward

---

## Pseudocode

### Main MCTS Search Loop

```python
function MCTS_SEARCH(initial_breadboard, iterations):
    root = MCTSNode(initial_breadboard)
    best_candidate_state = None
    best_candidate_reward = 0.0

    for i in range(iterations):
        node = root

        # PHASE 1: SELECTION
        # Traverse tree using UCT until we reach a leaf
        while node.has_children() and node.is_fully_expanded():
            node = SELECT_BEST_CHILD(node, exploration_constant=1.0)

        # PHASE 2: EXPANSION
        # Add a new child node with an untried action
        if node.has_untried_actions():
            action = node.pop_random_untried_action()
            new_state = node.state.apply_action(action)
            node = node.add_child(new_state, action)

        # PHASE 3: SIMULATION (Evaluation)
        # Evaluate the new state
        state = node.state

        # Calculate metrics
        num_components = count_non_wire_components(state)
        num_unique_types = count_unique_component_types(state)
        vin_row = get_vin_row(state)
        vout_row = get_vout_row(state)

        # Connection bonus
        if state.find(vin_row) == state.find(vout_row):
            if num_components > 0:
                connection_bonus = 20.0
            else:
                connection_bonus = 5.0
        else:
            connection_bonus = -2.0

        # Heuristic reward
        heuristic = (num_components * 5.0) +
                   (num_unique_types * 8.0) +
                   connection_bonus

        # SPICE evaluation for complete circuits
        if state.is_complete() and num_components >= 3:
            netlist = state.to_netlist()
            if netlist:
                try:
                    freq, vout = run_spice_simulation(netlist)
                    spice_reward = calculate_reward(freq, vout)
                    complexity_bonus = (num_unique_types * 5.0) +
                                      (num_components * 2.0)
                    reward = spice_reward + complexity_bonus
                except:
                    reward = max(0.01, heuristic * 0.1)
            else:
                reward = max(0.01, heuristic * 0.1)
        else:
            reward = max(0.0, heuristic)

        # Track best candidate
        if reward > best_candidate_reward:
            best_candidate_reward = reward
            best_candidate_state = state

        # PHASE 4: BACKPROPAGATION
        # Update all ancestor nodes
        while node is not None:
            node.visits += 1
            node.wins += reward
            node = node.parent

    return root, best_candidate_state
```

### UCT Selection

```python
function SELECT_BEST_CHILD(node, exploration_constant):
    best_score = -infinity
    best_child = None

    for child in node.children:
        if child.visits == 0:
            return child  # Prioritize unvisited children

        # UCT formula
        exploitation = child.wins / child.visits
        exploration = exploration_constant * sqrt(log(node.visits) / child.visits)
        uct_score = exploitation + exploration

        if uct_score > best_score:
            best_score = uct_score
            best_child = child

    return best_child
```

### Component Placement Validation

```python
function CAN_PLACE_COMPONENT(breadboard, component_type, start_row, column):
    info = COMPONENT_CATALOG[component_type]
    pin_rows = [start_row, start_row + 1, ..., start_row + info.pin_count - 1]

    # Check boundaries
    if not (WORK_START_ROW <= min(pin_rows) and max(pin_rows) <= WORK_END_ROW):
        return False

    # Check if cells are empty
    for row in pin_rows:
        if breadboard.grid[row][column] is not None:
            return False

    # Single-pin components: must connect to inactive net
    if info.pin_count == 1:
        return not breadboard.is_row_active(start_row)

    # Multi-pin components: at least one pin must connect to active net
    return any(breadboard.is_row_active(row) for row in pin_rows)
```

### Netlist Generation

```python
function TO_NETLIST(breadboard):
    if not breadboard.is_complete():
        return None

    # Initialize net mapping
    position_to_net = {}
    net_counter = 0

    # Assign initial nets to all component pins
    for component in breadboard.placed_components:
        for pin_row, pin_col in component.pins:
            if pin_row == VSS_ROW:
                position_to_net[(pin_row, pin_col)] = "0"  # Ground
            elif pin_row == VDD_ROW:
                position_to_net[(pin_row, pin_col)] = "VDD"
            else:
                position_to_net[(pin_row, pin_col)] = f"n{net_counter}"
                net_counter += 1

    # Merge nets connected by wires
    union_find = UnionFind()
    for wire in breadboard.get_wires():
        pin1, pin2 = wire.pins
        net1 = position_to_net[pin1]
        net2 = position_to_net[pin2]
        union_find.union(net1, net2)

    # Apply net merges
    for position in position_to_net:
        position_to_net[position] = union_find.find(position_to_net[position])

    # Generate SPICE netlist
    lines = []
    lines.append("* Auto-generated SPICE netlist")
    lines.append("VDD VDD 0 DC 5V")

    vin_net = position_to_net[breadboard.get_vin_position()]
    lines.append(f"VIN {vin_net} 0 AC 1V")

    for component in breadboard.placed_components:
        if component.type in ['resistor', 'capacitor', 'inductor', ...]:
            nets = [position_to_net[pin] for pin in component.pins]
            lines.append(generate_component_line(component.type, nets))

    vout_net = position_to_net[breadboard.get_vout_position()]
    lines.append(f".print ac v({vout_net})")
    lines.append(".ac dec 100 1 1MEG")
    lines.append(".end")

    return "\n".join(lines)
```

---

## Challenges and Solutions

### Challenge 1: Exponential Action Space

**Problem**: With 8 component types and ~30 possible placements per column, plus hundreds of possible wire connections, the action space grows exponentially.

**Solutions:**
1. **Column-by-column constraint**: Force leftmost-column placement
2. **Connectivity filtering**: Only allow placements that extend the active circuit
3. **Wire deduplication**: Track and prevent duplicate wires
4. **Progressive expansion**: MCTS naturally focuses on promising subtrees

### Challenge 2: Sparse Rewards

**Problem**: Most random circuits are invalid or perform poorly. Valid circuits are rare, making learning difficult.

**Solutions:**
1. **Intermediate heuristic rewards**: Guide exploration with component count and diversity metrics
2. **Connection bonus**: Strongly reward circuits that achieve VIN-VOUT connectivity
3. **Positive reward bias**: Avoid negative rewards that poison the search tree
4. **Progressive requirements**: Start with simple goals (connectivity) before complex ones (performance)

### Challenge 3: Trivial Solutions

**Problem**: Algorithm finds "shortcut" solutions (e.g., direct wire from VIN to VOUT).

**Solutions:**
1. **Minimum component requirement**: Enforce 3+ components for completion
2. **Differential connection bonus**: Reward circuits with components more than empty connections
3. **Complexity rewards**: Bonus for component diversity and count

### Challenge 4: Disconnected Components

**Problem**: Components placed but not electrically connected to the main circuit path.

**Current Status**: Partially addressed by connectivity requirements, but some edge cases remain. The breadboard allows components to be placed if they connect to *any* active net, not necessarily the VIN-VOUT path.

**Potential Solutions:**
1. Track connectivity to both VIN and VOUT separately
2. Require all components to be on the critical path
3. Add reward penalty for unused components

### Challenge 5: Search Depth vs. Quality

**Problem**: Finding circuits with 3+ components requires exploring deep trees, but MCTS tends to exploit early successes.

**Solutions:**
1. **Tunable exploration constant**: Increase to encourage more exploration
2. **Visit-based filtering**: Require minimum visits before selecting best solution
3. **Best candidate tracking**: Save highest-reward state even if not in final path

---

## Performance Characteristics

### Computational Complexity

- **State space size**: O(C^N × W^M) where C=components, N=columns, W=wires, M=connections
- **MCTS iteration**: O(depth × branching_factor) for tree traversal
- **SPICE evaluation**: O(1) per complete circuit (dominant cost)

### Typical Run Statistics (10,000 iterations)

```
Total iterations:        10,000
SPICE simulations:       ~0-50 (only for complete circuits)
Tree nodes created:      ~3,000-5,000
Average tree depth:      ~3-5 actions
Best circuit found:      2-3 components (current implementation)
Runtime:                 ~30-60 seconds
```

### Scaling Observations

- Most iterations perform only tree traversal (fast)
- SPICE simulations are bottleneck but rare (only ~0.5% of iterations)
- 200,000 iterations ≈ 3-5x slower than 10,000 (not linear due to tree reuse)

---

## Future Enhancements

1. **Neural Network Evaluation**: Replace SPICE with learned performance predictor for faster iteration
2. **Parallel MCTS**: Distribute tree search across multiple threads/processes
3. **Transfer Learning**: Use successful circuits from previous runs to warm-start search
4. **Multi-objective Optimization**: Optimize for multiple metrics (gain, bandwidth, power, etc.)
5. **Adaptive Rewards**: Dynamically adjust reward weights based on search progress
6. **Component Value Optimization**: Not just topology, but also component values (R, C, L)
7. **Constraint Satisfaction**: Add hard constraints (e.g., "must include amplifier stage")

---

## References

- Browne et al. (2012). "A Survey of Monte Carlo Tree Search Methods"
- Silver et al. (2016). "Mastering the game of Go with deep neural networks"
- Kocsis & Szepesvári (2006). "Bandit based Monte-Carlo Planning"

---

## Appendix: Code Structure

```
MCTS-topology-generator/
├── core/
│   ├── MCTS.py                    # MCTS algorithm implementation
│   ├── topology_game_board.py     # Breadboard state and rules
│   ├── spice_simulator.py         # SPICE interface and rewards
│   └── main.py                    # Entry point and CLI
├── utils/
│   └── augmentation.py            # Circuit symmetry utilities
├── generated_circuit.sp           # Latest generated SPICE netlist
├── best_candidate_circuit.sp      # Best circuit found in search
└── README.md                      # Project documentation
```

---

*Generated for MCTS Circuit Topology Generator Project*
*Author: Eason Li*
*Date: 2025*
