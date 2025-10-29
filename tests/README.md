# Test Suite

This directory contains comprehensive tests for the MCTS Circuit Topology Generator.

## Running Tests

All tests should be run from the project root directory:

```bash
# Run individual test suites
python3 tests/test_mcts_fixes.py           # MCTS core functionality
python3 tests/test_validation_rules.py     # Circuit validation rules
python3 tests/test_mcts_search.py          # Integration test (short search)

# Run specific circuit tests
python3 tests/test_rc_filter_reward.py     # RC filter with SPICE
python3 tests/test_inverter_reward.py      # CMOS inverter circuit
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

### Augmentation Tests
- **test_augmentation.py** - Circuit symmetry and translation tests (needs update for current VIN/VOUT positions)

## Test Results Summary

All core tests pass successfully:
- ✅ MCTS core functionality (5/5 tests)
- ✅ Validation rules (8/8 tests)
- ✅ MCTS search integration (1/1 test)
- ✅ RC filter with SPICE simulation
