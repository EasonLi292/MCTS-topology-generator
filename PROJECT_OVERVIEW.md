# Project Overview

This repository implements an end-to-end pipeline that **discovers analog circuit
topologies** with Monte Carlo Tree Search (MCTS) and validates them with
`ngspice`. The system uses a **row-only connectivity model** where each breadboard
row functions as a single electrical net, simplifying the state space while
maintaining full circuit functionality.

The code is organized so each stage of the pipeline (state representation, search,
simulation, reward shaping, and verification) is both testable and swappable—handy
context when explaining the system to reviewers.

---

## 1. Execution Flow

1. `core/main.py` parses CLI options, builds an empty `Breadboard`, and launches
   `MCTS.search(iterations=N)`.
2. The search repeatedly calls `Breadboard.legal_actions()` to place components
   or wires, and `Breadboard.apply_action()` to spawn child states.
3. When a state satisfies `Breadboard.is_complete_and_valid()`, the tree asks
   `spice_simulator.run_ac_simulation()` + `calculate_reward_from_simulation()`
   for an electrical reward.
4. Rewards are back-propagated through the tree (`MCTSNode.update()`), and the
   best path is exported as a SPICE netlist via `Breadboard.to_netlist()`.

---

## 2. Core Modules & Key Functions

### Breadboard Environment — `core/topology_game_board.py`

**Row-Only Model**: Each row is a single electrical net. Components span multiple rows,
and wires connect rows together. No column-based placement—all connectivity is row-based.

| Function / Method | Purpose |
| --- | --- |
| `Breadboard.__init__(rows)` | Creates the virtual board with fixed VIN/VOUT rows and initializes row-based union-find nets. |
| `RowPinIndex` | Tracks which component pins occupy each row (multiple pins can share a row). |
| `can_place_component(comp_type, row)` | Enforces work-area, activation, and uniqueness rules before placement. |
| `can_place_wire(r1, r2)` | Validates wiring rules (no same-row, no duplicate, forbidden pairs, gate/base protection). |
| `apply_action(action)` | Returns an immutable clone after placing a component (`comp_type, row`) or wire (`"wire", r1, r2`). |
| `is_complete_and_valid()` | Confirms VIN/VOUT presence, component connectivity via graph BFS, and gate/base safety. |
| `_compute_connectivity_summary()` | Builds adjacency graph from components (edges between nets) and validates via BFS. |
| `to_netlist()` | Emits a SPICE-ready description with nets named by union-find roots. |

### Monte Carlo Tree Search — `core/MCTS.py`

| Function / Method | Purpose |
| --- | --- |
| `MCTS.search(iterations)` | Runs the selection → expansion → simulation → backprop loop. |
| `_calculate_circuit_metrics(state)` | Extracts structural features (component counts, VIN–VOUT reachability, rail contact). |
| `_calculate_heuristic_reward(metrics)` | Scores incomplete states so the tree still gets guidance before SPICE. |
| `_evaluate_with_spice(state, metrics, stats)` | Calls SPICE for complete states and folds in complexity bonuses. |
| `_calculate_final_reward(spice_reward, metrics, stats)` | Guarantees finished circuits outrank incomplete ones. |
| `get_best_solution()` | Traverses the explored tree to recover the best-valid action path. |

### SPICE Interface — `core/spice_simulator.py`

| Function / Method | Purpose |
| --- | --- |
| `run_ac_simulation(netlist)` | Writes a temporary `.sp` file and executes `ngspice -b`. |
| `_parse_ac_results(output)` | Reads the AC sweep table (`frequency`, `real`, `imag`). |
| `calculate_reward_from_simulation(freq, vout)` | Converts the AC response into a score dominated by spread/range metrics. |
| `_calculate_spread_reward`, `_calculate_range_reward`, `_calculate_non_monotonic_bonus`, `_calculate_signal_presence_bonus` | Isolated helpers for each reward component, making the scoring function easy to tune. |

### Driver & Verification Utilities

- `core/main.py`: CLI orchestration, result printing, saving generated netlists.
- `verify_system.py`: High-level smoke test that exercises board setup, action
  application, SPICE export, and reward calculation in one script.

---

## 3. Supporting Assets

- **`utils/augmentation.py`** — Generates vertically translated copies of a
  board so reward statistics can be shared between symmetric states.
- **`tests/`** — 20+ targeted suites covering placement rules, reward shaping,
  SPICE netlist emission, and miniature MCTS runs.
- **`docs/ARCHITECTURE.md` & `docs/VALIDATION_RULES_SUMMARY.md`** — Deep dives
  into the design decisions and electrical guardrails respectively.

---

## 4. Spotlighted Technical Choices

- **Row-Only Connectivity Model:** Each breadboard row is a single electrical net
  (like a real breadboard). Components span rows but don't auto-unify them; instead,
  they create edges in an adjacency graph for validation. Wires explicitly merge rows
  via union-find. See `docs/ROW_ONLY_MODEL.md` for detailed architecture.

- **Two-Layer Connectivity System:**
  1. **Union-Find (Physical Wiring)**: Tracks which rows are wired together - used
     for net naming and active net queries (O(α(n)) efficiency)
  2. **Component Graph (Logical Connectivity)**: Components create edges between nets
     they span - used for BFS validation and degenerate component detection

- **Progressive Rewards:** Heuristic bonuses unlock in stages (touching VDD,
  touching VSS, VIN→VOUT path, all components reachable), which stabilizes MCTS
  before the first successful SPICE simulation.

- **Degenerate Component Detection:** Components must span at least 2 different nets
  (checked BEFORE union-find merging), preventing placement of electrically useless
  components that would waste action space.

- **Immutable State Transitions:** `apply_action()` clones the board (including
  `RowPinIndex`), keeping tree nodes independent for potential parallel rollouts.

---

## 5. Key Documentation

- **`docs/ROW_ONLY_MODEL.md`** - Deep dive into the row-only connectivity architecture,
  union-find vs component graph, net naming, and validation
- **`docs/VALIDATION_RULES_SUMMARY.md`** - Complete circuit validation rules and examples
- **`tests/test_multipin_connectivity.py`** - Tests proving components span nets without
  auto-union, and connectivity works via graph traversal

This document gives a concise but technically grounded view that pairs well
with the README when presenting the project to faculty or reviewers.
