# MCTS Circuit Topology Generator - Project Overview

## Project Summary

This project implements a Monte Carlo Tree Search (MCTS) algorithm to automatically discover analog circuit topologies. The system explores possible circuit configurations by placing components (resistors, capacitors, inductors, transistors, diodes) on a virtual breadboard and connecting them with wires. Valid circuits are evaluated using SPICE simulation to find functional designs that connect an input signal to an output.

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
│  • Circuit validation rules                              │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           SPICE Simulator Interface                      │
│           (spice_simulator.py)                           │
│  • AC analysis simulation (ngspice)                      │
│  • Frequency response evaluation                         │
│  • Performance-based reward calculation                  │
└─────────────────────────────────────────────────────────┘
```

## Breadboard Grid Structure

The virtual breadboard uses **8 columns** and a configurable number of rows:

```
Row 0:              VSS (Ground)                  [Reserved - always available]
Row 1:              VIN (Input Signal)            [Reserved - input node]
Rows 2..(N-3):      Component Work Area           [Available for component placement]
Row (N-2):          VOUT (Output Signal)          [Reserved - output node]
Row (N-1):          VDD (Power Supply)            [Reserved - always available]
```

`N` is user-selectable (command-line default 15; historical layout uses 30). All documentation and tests derive row indices from these symbolic positions, so the search can adapt to smaller boards for faster convergence or larger ones for richer topologies.

**Design Features:**
- Reserved rows ensure consistent power/ground/I/O availability regardless of total height
- Column 0 contains VIN/VOUT markers
- Columns 1-7 used for circuit components
- Column-by-column placement reduces search space

## Available Components

| Component | Pins | Value | SPICE Model |
|-----------|------|-------|-------------|
| Resistor | 2 | 1kΩ | R |
| Capacitor | 2 | 1µF | C |
| Inductor | 2 | 1mH | L |
| Diode | 2 | - | D (DMOD) |
| NMOS | 3 | L=1µ, W=10µ | M (NMOS_MODEL) |
| PMOS | 3 | L=1µ, W=10µ | M (PMOS_MODEL) |
| NPN | 3 | β=100 | Q (NPN_MODEL) |
| PNP | 3 | β=100 | Q (PNP_MODEL) |
| Wire | 2 | - | (connectivity) |

## MCTS Algorithm

### Four Phases

1. **Selection**: Navigate tree using UCT formula balancing exploration/exploitation
2. **Expansion**: Try a new action (place component or wire)
3. **Simulation**: Evaluate circuit with SPICE if complete, else use heuristics
4. **Backpropagation**: Update node statistics with reward

### UCT Formula

```
UCT(node) = (wins / visits) + c × sqrt(ln(parent_visits) / visits)
```

Where `c = 1.0` (exploration constant)

## Circuit Validation Rules

All circuits must satisfy strict validation before SPICE simulation:

1. **No Floating Components**: All components must be electrically connected to the VIN-VOUT path
2. **Gate/Base Protection**: MOSFET gates and BJT bases cannot be directly wired to VDD/VSS
3. **Complete Connectivity**: VIN and VOUT must be electrically connected
4. **Minimum Complexity**: Circuits must contain at least 3 components

These rules ensure only physically realizable circuits are simulated.

## Reward System

### Two-Tier Reward Structure

**Heuristic Rewards** (for incomplete circuits during exploration):
```
Reward = (num_components × 5.0) +
         (num_unique_types × 8.0) +
         connection_bonus

Where connection_bonus:
  +20.0  if VIN-VOUT connected with components
  +5.0   if VIN-VOUT connected but empty
  -2.0   if VIN-VOUT not connected
```

**Typical heuristic range**: 20-60 points

**SPICE Rewards** (for complete circuits ≥3 components):
```
SPICE Reward = baseline +
               (spread × 500) +
               (voltage_range × 250) +
               (non_monotonic × 20) +
               (signal_presence × 100)

Where:
  baseline         = 100.0  (any working circuit)
  spread           = std_dev of output magnitude (frequency dependence)
  voltage_range    = max - min output voltage
  non_monotonic    = count of peaks/valleys in response
  signal_presence  = mean output magnitude

Complexity Bonus = (num_unique_types × 5.0) + (num_components × 2.0)

Total Reward = SPICE Reward + Complexity Bonus
```

**Typical SPICE range**: 100-5000+ points

### Reward Design Rationale

SPICE rewards are designed to **massively dominate** heuristic rewards:

- **Simple circuits** (flat AC response): ~100-200 points
- **Filters** (frequency-dependent): ~500-1000 points
- **Complex filters** (resonant, multi-stage): ~2000-5000+ points

This ensures MCTS heavily prioritizes finding valid, working circuits over exploration.

**Example**: RC Low-Pass Filter
- Heuristic: 59.0 points
- SPICE: 611.4 points (10.7× advantage)

## Key Features

### Connectivity Tracking
- Uses Union-Find for efficient electrical connectivity tracking
- Component pins auto-union when placed
- Wires explicitly union rows

### Action Space Constraints
1. Column-by-column placement (leftmost empty column)
2. Components must connect to active nets
3. No duplicate wires
4. Boundary checks for valid placement

### SPICE Netlist Generation
- Automatic conversion of breadboard state to SPICE format
- Proper net naming and merging
- Support for all component types including MOSFETs
- Correct device models with parameters

## Performance Characteristics

### Typical Run (10,000 iterations)
- SPICE simulations: ~10-50 (only complete circuits)
- Tree nodes created: ~3,000-5,000
- Average tree depth: ~3-5 actions
- Runtime: ~30-60 seconds

### Computational Costs
- Tree traversal: Fast (most iterations)
- SPICE simulation: Slow but rare (~0.5% of iterations)
- SPICE rewards dominate, making valid circuits highly valuable

## Usage

```bash
cd core
python3 main.py --iterations 10000 --exploration 1.0 --board-rows 20 --verbose
```

**Arguments:**
- `--iterations N`: Number of MCTS iterations (default: 10000)
- `--exploration C`: UCT exploration constant (default: 1.0)
- `--board-rows R`: Total row count for the breadboard workspace (default: 15)
- `--verbose`: Print detailed action sequence

**Output:**
- Search progress with SPICE statistics
- Best circuit action sequence
- Generated SPICE netlist (`generated_circuit.sp`)
- Best candidate circuit (`best_candidate_circuit.sp`)

## Project Structure

```
MCTS-topology-generator/
├── core/
│   ├── main.py                      # CLI entry point
│   ├── MCTS.py                      # MCTS algorithm
│   ├── topology_game_board.py       # Breadboard state & validation
│   ├── spice_simulator.py           # SPICE interface & rewards
│   ├── test_validation_rules.py     # Validation tests
│   ├── test_inverter_with_load.py   # CMOS inverter test
│   └── test_rc_filter_reward.py     # RC filter test
├── utils/
│   └── augmentation.py              # Circuit symmetry utilities
├── README.md                        # Usage documentation
├── PROJECT_OVERVIEW.md              # This file
└── VALIDATION_RULES_SUMMARY.md      # Validation details
```

## Example Circuits

### CMOS Inverter
- Components: PMOS + NMOS + Resistor
- Validation: ✅ All rules passed
- Reward: ~31 points (flat AC response)

### RC Low-Pass Filter
- Components: Resistor + Capacitor + Inductor
- Validation: ✅ All rules passed
- Reward: ~632 points (frequency-dependent)

Both circuits demonstrate proper SPICE netlist generation and validation.

## Key Achievements

1. ✅ Fully functional MCTS circuit search
2. ✅ Comprehensive circuit validation rules
3. ✅ Working SPICE integration with ngspice
4. ✅ Reward system that prioritizes valid circuits (10-100× advantage)
5. ✅ Support for passive and active components (R, C, L, transistors, diodes)
6. ✅ Automatic SPICE netlist generation
7. ✅ No floating components or invalid connections

---

**Author**: Eason Li
**Date**: 2025
