# Test Suite

This directory contains comprehensive tests for the MCTS Circuit Topology Generator.

## Running Tests

All tests should be run from the project root directory:

```bash
# Core suites
python3 tests/test_mcts_fixes.py               # MCTS core functionality
python3 tests/test_validation_rules.py         # Circuit validation rules
python3 tests/test_mcts_search.py              # Integration test (short search)
python3 tests/test_component_metadata.py       # Component catalog invariants
python3 tests/test_component_placement_boundaries.py  # Placement bounds

# Circuit benchmarks
python3 tests/test_rc_filter_reward.py         # RC filter with SPICE
python3 tests/test_inverter_reward.py          # CMOS inverter circuit
python3 tests/test_inverter_with_load.py       # CMOS inverter + load
python3 tests/test_transistor_bridge_reward.py # Two-transistor bridge fallback
python3 tests/test_winning_wire_reward.py      # Reward for final wire

# Netlist and completion harnesses
python3 tests/test_netlist_output.py           # Netlist export sanity check
python3 tests/test_almost_complete.py          # Almost-finished circuit scenarios
python3 tests/test_partial_circuit.py          # Guided completion demo
python3 tests/test_valid_circuit.py            # Golden reference topology
python3 tests/test_search_space.py             # Macro-level action space coverage
python3 tests/test_search_space_correct.py     # Regression for search constraints
python3 tests/test_wire_validation_rules.py    # Wire placement guardrails
python3 tests/test_connectivity_summary.py     # Connectivity summary edge cases
```

## Test Organization

### Core Functionality Tests
- **test_mcts_fixes.py** - Tests MCTS node operations, UCT selection, and backpropagation
- **test_mcts_search.py** - End-to-end MCTS search workflow test
- **test_search_space.py / test_search_space_correct.py** - Ensure the generated action space respects constraints and regressions remain fixed

### Validation Tests
- **test_validation_rules.py** - Comprehensive circuit validation rules (floating components, control pin protection, completeness)
- **test_valid_circuit.py** - Golden reference circuit should pass validation and reward checks
- **test_partial_circuit.py** - Demonstrates MCTS finishing a prepared circuit
- **test_component_metadata.py** - Confirms catalog metadata consistency (pin counts, uniqueness flags)
- **test_component_placement_boundaries.py** - Guards placement boundaries and reserved columns
- **test_wire_validation_rules.py** - Verifies wiring guardrails (power rail restrictions, duplicates)
- **test_connectivity_summary.py** - Regression tests for connectivity summary edge cases

### Circuit-Specific Tests
- **test_rc_filter_reward.py** - RC low-pass filter construction and SPICE evaluation
- **test_inverter_reward.py** - CMOS inverter circuit test
- **test_inverter_with_load.py** - CMOS inverter with load resistor
- **test_transistor_bridge_reward.py** - Regression for the two-transistor bridge fallback reward
- **test_winning_wire_reward.py** - Reward from the final completing wire

### Augmentation Tests
- **test_augmentation.py** - Circuit symmetry and translation tests (needs update for current VIN/VOUT positions)

### Netlist & Completion Harnesses
- **test_netlist_output.py** - Validates generated netlists run successfully in ngspice
- **test_almost_complete.py** - Exercises MCTS on almost-finished circuits

## Test Results Summary

All core tests pass successfully:
- ✅ MCTS core functionality (expanded coverage of nodes + action space)
- ✅ Validation suite (placement, metadata, connectivity, wires)
- ✅ MCTS search integration (short & guided modes)
- ✅ Netlist export + ngspice sanity checks
- ✅ Circuit-specific benchmarks (inverter family, RC filter, transistor bridge, winning wire)
