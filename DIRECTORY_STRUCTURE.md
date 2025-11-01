# Project Directory Structure

```
MCTS-topology-generator/
│
├── README.md                    # Main project documentation
├── .gitignore                   # Git ignore rules
│
├── core/                        # Core algorithm implementation
│   ├── main.py                  # Entry point - CLI interface
│   ├── MCTS.py                  # MCTS search algorithm (SOLID refactored)
│   ├── topology_game_board.py   # Breadboard environment & circuit rules
│   └── spice_simulator.py       # SPICE simulation interface & rewards
│
├── utils/                       # Utility modules
│   └── augmentation.py          # Circuit symmetry and translation
│
├── tests/                       # Comprehensive test suite
│   ├── README.md                # Test documentation
│   ├── test_almost_complete.py  # Almost-finished circuit scenarios
│   ├── test_augmentation.py     # Symmetry tests
│   ├── test_inverter_reward.py  # CMOS inverter test
│   ├── test_inverter_with_load.py
│   ├── test_mcts_fixes.py       # MCTS core functionality (5 tests)
│   ├── test_mcts_search.py      # Integration test
│   ├── test_netlist_output.py   # Netlist export sanity check
│   ├── test_rc_filter_reward.py # RC filter SPICE test
│   ├── test_validation_rules.py # Circuit validation (10 tests)
│   └── test_winning_wire_reward.py
│
├── examples/                    # Example outputs (static)
│   ├── README.md                # Examples documentation
│   ├── best_candidate_circuit.sp
│   ├── generated_circuit.sp
│   └── inverter_with_load.sp
│
├── outputs/                     # Generated artifacts (git-ignored)
│   ├── best_candidate_circuit.sp
│   └── generated_circuit.sp
│
└── docs/                        # Detailed documentation
    ├── README.md                # Documentation index
    ├── ARCHITECTURE.md          # System architecture
    ├── PROJECT_STATUS.md        # Development history
    ├── VALIDATION_RULES_SUMMARY.md
    ├── BOOSTED_SPICE_REWARDS.md
    ├── AUGMENTATION_INTEGRATION_GUIDE.md
    ├── MCTS_FIXES_SUMMARY.md
    └── CMOS_INVERTER_TEST_RESULTS.md
```

## File Counts

- **Core modules**: 4 Python files
- **Utilities**: 1 Python file
- **Tests**: 10 Python test files
- **Documentation**: 8 markdown files + 4 READMEs
- **Examples**: 3 SPICE netlists
- **Outputs**: Auto-generated SPICE netlists (ignored by git)

## Navigation Guide

### For Developers
- Start with `README.md` for overview
- Read `docs/ARCHITECTURE.md` for system design
- Review `core/main.py` for entry point
- Explore `core/MCTS.py` for algorithm details

### For Testing
- See `tests/README.md` for test documentation
- Run `tests/test_validation_rules.py` for validation tests
- Check `tests/test_mcts_search.py` for integration test

### For Circuit Examples
- Browse `examples/` for static SPICE netlists
- After running `core/main.py`, inspect `outputs/` for freshly generated netlists
- Review `examples/README.md` for netlist format

### For Technical Details
- `docs/VALIDATION_RULES_SUMMARY.md` - Circuit rules
- `docs/BOOSTED_SPICE_REWARDS.md` - Reward system
- `docs/AUGMENTATION_INTEGRATION_GUIDE.md` - Search optimization
