# Project Overview

This repository implements an end-to-end pipeline that **discovers analog circuit
topologies** with Monte Carlo Tree Search (MCTS) and validates them with
`ngspice`. The code is organized so each stage of the pipeline (state
representation, search, simulation, reward shaping, and verification) is both
testable and swappable—handy context when explaining the system to reviewers.

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

| Function / Method | Purpose |
| --- | --- |
| `Breadboard.__init__(rows)` | Creates the virtual board with fixed VIN/VOUT rows and initializes union-find nets. |
| `can_place_component(component, row, col)` | Enforces work-area, activation, and uniqueness rules before a part is placed. |
| `can_place_wire(r1, c1, r2, c2)` | Validates wiring rules (no duplicate wires, VIN/VOUT safety, control-pin to rail blocks). |
| `apply_action(action)` | Returns an immutable clone after placing a component or wire. |
| `is_complete_and_valid()` | Confirms VIN/VOUT presence, connectivity, and gate/base safety. |
| `get_connectivity_summary()` | Builds the net graph that powers both validation and heuristic signals. |
| `to_netlist()` | Emits a SPICE-ready description (models, supplies, components, probes, AC sweep). |

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

- **Union-Find Nets:** Breadboard rows share disjoint-set representatives so
  wire placement instantly merges nets while keeping VIN/VOUT rails isolated.
- **Progressive Rewards:** Heuristic bonuses unlock in stages (touching VDD,
  touching VSS, VIN→VOUT path, all components reachable), which stabilizes MCTS
  before the first successful SPICE simulation.
- **Immutable State Transitions:** `apply_action()` clones the board, which
  keeps tree nodes independent and makes it easy to parallelize future rollouts.

This document gives a concise but technically grounded view that pairs well
with the README when presenting the project to faculty or reviewers.
