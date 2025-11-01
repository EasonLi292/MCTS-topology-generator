# Quick Start Guide

This guide provides a quick overview for reviewing the MCTS Circuit Topology Generator project.

## Project Overview (30 seconds)

**What it does**: Uses Monte Carlo Tree Search to automatically discover analog circuit topologies by placing components on a virtual breadboard and evaluating them with SPICE simulation.

**Key Innovation**: Combines MCTS exploration with real electrical simulation (ngspice) to find functional circuits without human design.

## Running the Code (2 minutes)

### Prerequisites
```bash
# Install ngspice
brew install ngspice  # macOS
# OR
sudo apt-get install ngspice  # Linux

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install PySpice numpy
```

### Basic Run
```bash
cd core
python3 main.py --iterations 1000
```

Expected output: Search progress, best circuit found, SPICE netlist saved to file.

> Tip: Add `--board-rows N` (e.g., `--board-rows 20`) to grow or shrink the vertical workspace. Smaller boards (default 15 rows) tighten the search area and often improve convergence speed.

## Code Quality Highlights (1 minute)

✅ **SOLID Principles Applied**
- Single Responsibility: Each function has one clear purpose
- Well-documented: 100+ function docstrings
- Type hints throughout
- Small functions (5-20 lines typical)

✅ **Testing**
- 20+ comprehensive tests
- All core tests pass (run `python3 tests/test_validation_rules.py`)

✅ **Organization**
- Clean separation: MCTS algorithm, Environment, Simulation, Utils
- Professional directory structure (core/, tests/, docs/, examples/)

## Key Files to Review (5 minutes)

### Algorithm Implementation
1. **`core/MCTS.py`** (556 lines)
   - Monte Carlo Tree Search implementation
   - Refactored into 25+ focused functions
   - Key classes: `MCTSNode`, `CircuitStatistics`, `MCTS`

2. **`core/topology_game_board.py`** (1036 lines)
   - Virtual breadboard environment
   - Circuit validation rules
   - SPICE netlist generation
   - Refactored into 50+ focused methods

3. **`core/spice_simulator.py`** (376 lines)
   - Interface to ngspice
   - Reward calculation based on frequency response
   - Refactored into 15+ helper functions

### Testing
4. **`tests/test_validation_rules.py`**
   - 8 comprehensive validation tests
   - Run to see all tests pass

## Architecture (2 minutes)

```
User Input → main.py
              ↓
          MCTS Search (MCTS.py)
              ↓
    Breadboard State (topology_game_board.py)
              ↓
    SPICE Simulation (spice_simulator.py)
              ↓
          Reward → Backpropagation
```

**Key Concepts**:
- **Breadboard**: Configurable-height virtual breadboard (8 columns; CLI default 15 rows) with pre-placed VIN/VOUT rails
- **MCTS Phases**: Selection → Expansion → Simulation → Backpropagation
- **Reward System**: SPICE-based (dominant) + heuristic guidance

## Documentation (browse as needed)

- **README.md** - Main documentation with usage examples
- **docs/ARCHITECTURE.md** - Detailed system design
- **docs/VALIDATION_RULES_SUMMARY.md** - Circuit validation rules
- **tests/README.md** - Test suite documentation

## Example Output

See `examples/` directory for:
- `best_candidate_circuit.sp` - Highest reward circuit found
- `generated_circuit.sp` - Final circuit from search
- Sample SPICE netlists in standard format

## Questions?

For detailed explanations, see:
- System design: `docs/ARCHITECTURE.md`
- Code quality: `README.md` → "Code Quality" section
- Testing: `tests/README.md`
