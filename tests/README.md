# Test Suite

This directory contains comprehensive tests for the MCTS Circuit Topology Generator.

## Running Tests

All tests should be run from the project root directory:

```bash
# Core suites
python3 tests/test_mcts_fixes.py           # MCTS core functionality
python3 tests/test_validation_rules.py     # Circuit validation rules
python3 tests/test_mcts_search.py          # Integration test (short search)

# Circuit benchmarks
python3 tests/test_rc_filter_reward.py     # RC filter with SPICE
python3 tests/test_inverter_reward.py      # CMOS inverter circuit
python3 tests/test_inverter_with_load.py   # CMOS inverter + load
python3 tests/test_winning_wire_reward.py  # Reward for final wire

# Netlist and completion harnesses
python3 tests/test_netlist_output.py       # Netlist export sanity check
python3 tests/test_almost_complete.py      # Almost-finished circuit scenarios
python3 tests/test_partial_circuit.py      # Guided completion demo
```

## Test Organization

### Core Functionality Tests
- **test_mcts_fixes.py** - Tests MCTS node operations, UCT selection, and backpropagation
- **test_mcts_search.py** - End-to-end MCTS search workflow test

### Validation Tests
- **test_validation_rules.py** - Comprehensive circuit validation rules:
  - Floating component detection
  - Gate/base pin protection rules
  - Circuit completeness checks

### Circuit-Specific Tests
- **test_rc_filter_reward.py** - RC low-pass filter construction and SPICE evaluation
- **test_inverter_reward.py** - CMOS inverter circuit test
- **test_inverter_with_load.py** - CMOS inverter with load resistor
- **test_winning_wire_reward.py** - Reward from the final completing wire
- **test_partial_circuit.py** - Demonstrates MCTS finishing a prepared circuit
- **test_transistor_bridge_reward.py** - Regression for the two-transistor bridge fallback reward

### Augmentation Tests
- **test_augmentation.py** - Circuit symmetry and translation tests (needs update for current VIN/VOUT positions)

### Netlist & Completion Harnesses
- **test_netlist_output.py** - Validates generated netlists run successfully in ngspice
- **test_almost_complete.py** - Exercises MCTS on almost-finished circuits

## Test Results Summary

All core tests pass successfully:
- ✅ MCTS core functionality (5/5 tests)
- ✅ Validation rules (10/10 tests)
- ✅ MCTS search integration (short & guided modes)
- ✅ Netlist export + ngspice sanity checks
- ✅ Circuit-specific benchmarks (inverter, RC filter, winning wire)
