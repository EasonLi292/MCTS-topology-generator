# MCTS Circuit Generation Results

This directory contains results from MCTS topology generation experiments.

## Current Results

### After Heuristic Scaling Improvements (Nov 18, 2024)

**Key Achievement:** MCTS can now discover complete circuits from scratch!

#### 1. Almost-Complete Test (2 moves away)
- **File:** `mcts_almost_complete_1000iter.txt`
- **Result:** SUCCESS in 1,000 iterations
- **Improvement:** 9x faster than before scaling fix (9,000 → 1,000 iterations)
- **Circuit:** 3 resistors + 2 inductors + 2 capacitors (mixed passive elements)

#### 2. From-Scratch Full Search
- **File:** `mcts_from_scratch_8000iter.txt`
- **Result:** SUCCESS in 8,000 iterations (16% of 50K budget)
- **Previous:** FAILED at 50,000 iterations
- **Circuit Quality:** Excellent (105/100 score)
- **Components:** 7 total, 6 unique types
  - 1× NMOS, 1× PMOS, 1× PNP BJT
  - 2× Inductors, 1× Capacitor, 1× Resistor
- **Topology:** Novel hybrid design combining:
  - BJT amplification
  - CMOS logic/inverter
  - LC resonator/oscillator
  - Multi-stage architecture

### Heuristic Scaling Impact

**Before:**
- Raw heuristic scores: 0-240+
- Hard capped at 20.0
- Lost granularity (all high-quality circuits looked identical)

**After:**
- Scaled: raw_score × (20.0 / 240.0)
- Preserves relative differences
- Better gradient for MCTS exploration

**Results:**
- Almost-complete: 9x faster
- From-scratch: Now succeeds (previously failed)

## File Naming Convention

- `mcts_almost_complete_*.txt` - Tests starting 1-2 moves from completion
- `mcts_from_scratch_*.txt` - Tests starting from empty board
- `*_result.txt` - Successful completions
- `*_partial.txt` - Best attempt when not completed

## Usage

To analyze any result file:
```bash
python3 analyze_circuit.py outputs/mcts_from_scratch_8000iter.txt
```

## Legacy Files

- `best_candidate_circuit.sp` - Previous generation (before scaling fix)
- `generated_circuit.sp` - Previous generation (before scaling fix)
