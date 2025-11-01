# MCTS Topology Generator

Monte Carlo Tree Search (MCTS) based circuit topology generator that uses SPICE simulation to discover and optimize analog circuits.

## Overview

This project uses MCTS to explore the space of possible circuit topologies on a virtual breadboard. The algorithm:
- Places components (resistors, capacitors, inductors, transistors, diodes)
- Connects them with wires
- Evaluates circuits using ngspice AC simulation
- Rewards circuits based on frequency-dependent behavior and complexity

## Prerequisites

- Python 3.12+
- ngspice (for circuit simulation)

### Installing ngspice

**macOS (Homebrew):**
```bash
brew install ngspice
```

**Linux (apt):**
```bash
sudo apt-get install ngspice
```

**Verify installation:**
```bash
ngspice --version
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/EasonLi292/MCTS-topology-generator.git
cd MCTS-topology-generator
```

2. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install PySpice numpy
```

## Usage

### Basic Usage

Run the MCTS circuit generator with default settings (10,000 iterations):

```bash
cd core
python3 main.py
```

### Advanced Options

```bash
python3 main.py --iterations 20000 --exploration 1.5 --board-rows 20 --verbose
```

**Arguments:**
- `--iterations N`: Number of MCTS search iterations (default: 10000)
- `--exploration C`: UCT exploration constant (default: 1.0)
  - Lower values (0.5-1.0): More exploitation of known good circuits
  - Higher values (1.5-2.5): More exploration of new circuit topologies
- `--board-rows R`: Total number of rows in the breadboard (default CLI run: 15; larger values re-enable the full 30-row workspace)
- `--verbose`: Print detailed action sequence

### Output

The program outputs:
1. **Search progress**: Shows SPICE simulation success/failure rates and max reward
2. **Best circuit found**: Action sequence to build the circuit
3. **SPICE netlists**: Written to the git-ignored `outputs/` directory

Example output:
```
======================================================================
MCTS CIRCUIT TOPOLOGY GENERATOR
======================================================================
Iterations: 10000
Exploration constant: 1.0
======================================================================

Starting MCTS search...
Running iteration 0/10000... (SPICE: 0 success, 0 fail, max reward: 0.00)
Running iteration 1000/10000... (SPICE: 3 success, 9 fail, max reward: 0.01)
Running iteration 2000/10000... (SPICE: 9 success, 65 fail, max reward: 7.01)
...
Search complete.

======================================================================
RESULTS
======================================================================
Best path length: 3 actions
Average reward: 7.0100
  1. ('inductor', 5, 1)
  2. ('wire', 5, 0, 5, 1)
  3. ('wire', 6, 1, 20, 0)

Netlist saved to: outputs/generated_circuit.sp
```

## Project Structure

```
MCTS-topology-generator/
├── core/                        # Core algorithm implementation
│   ├── main.py                  # Entry point
│   ├── MCTS.py                  # MCTS algorithm (refactored with SOLID principles)
│   ├── topology_game_board.py   # Breadboard environment & circuit rules
│   └── spice_simulator.py       # SPICE simulation & reward calculation
├── utils/                       # Utility modules
│   └── augmentation.py          # Circuit symmetry and augmentation
├── tests/                       # Comprehensive test suite
│   ├── test_almost_complete.py  # Almost-finished circuit scenarios
│   ├── test_netlist_output.py   # Netlist export sanity check
│   ├── test_validation_rules.py # Circuit validation tests
│   ├── test_mcts_search.py      # Integration tests
│   └── ...                      # Additional circuit-specific tests
├── examples/                    # Example SPICE netlists
│   ├── best_candidate_circuit.sp
│   └── generated_circuit.sp
├── outputs/                     # Generated SPICE netlists (ignored by git)
│   ├── best_candidate_circuit.sp
│   └── generated_circuit.sp
├── docs/                        # Detailed documentation
│   ├── ARCHITECTURE.md          # System architecture overview
│   ├── VALIDATION_RULES_SUMMARY.md
│   └── ...                      # Additional technical docs
└── README.md                    # This file
```

See [`docs/README.md`](docs/README.md) for detailed documentation.

## How It Works

### 1. Breadboard Environment
- Virtual breadboard with configurable height (8 columns × user-selected rows; CLI default 15)
- Input (VIN) and output (VOUT) markers pre-placed
- Components placed in columns 1-7
- Wires connect components across rows

### 2. MCTS Search
The algorithm uses four phases:
1. **Selection**: Navigate tree using UCT formula balancing exploration/exploitation
2. **Expansion**: Try a new action (place component or wire)
3. **Simulation**: Evaluate circuit with SPICE if complete, else use heuristics
4. **Backpropagation**: Update node statistics with reward

### 3. Reward System
Rewards combine multiple factors:
- **SPICE reward** (dominant): Based on frequency response characteristics
  - Baseline: 5.0 for any working circuit
  - Spread bonus: 50× standard deviation of output magnitude
  - Range bonus: 25× (max - min) output voltage
- **Complexity bonus**: 5.0 per unique component type + 2.0 per component
- **Heuristic reward** (incomplete circuits): Small positive values to guide search

### 4. Circuit Completion
A circuit is complete when:
- VIN and VOUT are electrically connected
- Circuit contains at least 1 non-wire component
- Circuit passes SPICE simulation

## Troubleshooting

**"ngspice: command not found"**
- Install ngspice using package manager (see Prerequisites)
- Verify installation path in `spice_simulator.py:40` if using custom install location

**"DYLD_LIBRARY_PATH" errors (macOS)**
- The code automatically sets this for Homebrew installations
- For custom installs, update `spice_simulator.py:9`

**All circuits have low rewards**
- Try increasing iterations: `--iterations 50000`
- Adjust exploration: `--exploration 0.7` for more exploitation
- The search may need more time to find complex circuits

**SPICE simulation failures**
- Check ngspice is working: `ngspice --version`
- Review `outputs/generated_circuit.sp` for malformed netlist
- Some component configurations may be invalid (expected behavior)

## Code Quality

This codebase follows **SOLID principles** and software engineering best practices:

- ✅ **Single Responsibility**: Each function/class has one clear purpose
- ✅ **Small Functions**: Functions are typically 5-20 lines (refactored from 50-150+)
- ✅ **Comprehensive Documentation**: Every function has detailed docstrings
- ✅ **Type Hints**: Full type annotations throughout
- ✅ **Tested**: Comprehensive test suite with 20+ tests
- ✅ **Clean Architecture**: Separated concerns (MCTS, Environment, Simulation, Utils)

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for design details.

## Testing

Run the test suite to verify functionality:

```bash
# Core MCTS tests
python3 tests/test_mcts_fixes.py

# Circuit validation tests
python3 tests/test_validation_rules.py

# Integration test
python3 tests/test_mcts_search.py
```

See [`tests/README.md`](tests/README.md) for detailed test documentation.

## Recent Improvements

**v2.0 - Code Refactoring (Latest)**
- Complete refactoring to follow SOLID principles
- Broke down large functions into focused, testable units
- Added comprehensive documentation and type hints
- Organized project structure with dedicated directories

**v1.1 - Bug Fixes & Performance**
- Fixed critical component placement bug
- Increased SPICE reward scaling (2.7× improvement)
- Eliminated negative reward poisoning
- Improved solution selection algorithm

## License

MIT License

## Contributing

Issues and pull requests welcome!
