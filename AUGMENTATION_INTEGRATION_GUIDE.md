# Augmentation Integration Guide

## Overview

The augmentation system exploits **vertical translation symmetry** in breadboard circuits to accelerate MCTS search by:
1. Recognizing electrically equivalent circuits at different vertical positions
2. Sharing rewards across symmetric states
3. Reducing redundant exploration

## Key Insight

A circuit with a resistor at rows 5-6 is electrically **identical** to the same circuit at rows 10-11 (just vertically shifted). However, MCTS treats these as completely different states, wasting computation exploring both.

**Solution**: Use canonical forms to identify and deduplicate symmetric states.

## Integration Strategies

### Strategy 1: Canonical State Deduplication (Recommended for PoC)

**Where**: In `MCTSNode.expand()` method

**How**: Before expanding a new node, check if its canonical form has already been explored.

```python
# In MCTS.py, modify the search loop:

from utils.augmentation import canonical_hash

class MCTS:
    def __init__(self, initial_state: Breadboard):
        self.root = MCTSNode(initial_state)
        self.canonical_cache = {}  # canonical_hash -> best reward seen

    def search(self, iterations: int):
        for i in range(iterations):
            # ... existing selection/expansion code ...

            # Before simulation, check if we've seen this canonical form
            canon_hash = canonical_hash(node.state)

            if canon_hash in self.canonical_cache:
                # Use cached reward instead of running SPICE
                reward = self.canonical_cache[canon_hash]
                print(f"Cache hit! Using cached reward: {reward:.4f}")
            else:
                # Normal simulation
                # ... existing simulation code ...

                # Cache the result
                self.canonical_cache[canon_hash] = reward

            # ... existing backpropagation code ...
```

**Benefits**:
- Simple to implement (5-10 lines of code)
- Immediate performance gain (avoid redundant SPICE simulations)
- No change to core MCTS logic

**Limitations**:
- Doesn't pre-populate symmetric variants
- Only helps after discovering one variant

---

### Strategy 2: Reward Broadcast (Advanced)

**Where**: After computing a reward for a complete circuit

**How**: When a circuit receives a reward, immediately propagate it to all symmetric variants.

```python
# In MCTS.py, after computing reward:

from utils.augmentation import generate_translations, canonical_hash

# After computing reward for a complete circuit:
if current_state.is_complete_and_valid():
    freq, vout = run_ac_simulation(netlist)
    reward = calculate_reward_from_simulation(freq, vout)

    # Broadcast to all symmetric variants
    translations = generate_translations(current_state)
    for trans_board in translations:
        trans_canon_hash = canonical_hash(trans_board)
        # Update cache with best reward seen
        if trans_canon_hash not in self.canonical_cache:
            self.canonical_cache[trans_canon_hash] = reward
        else:
            self.canonical_cache[trans_canon_hash] = max(
                self.canonical_cache[trans_canon_hash],
                reward
            )
```

**Benefits**:
- Proactively populates cache with all symmetric variants
- Accelerates discovery of good circuits at different positions
- Maximizes cache hit rate

**Limitations**:
- Slightly more complex
- Generates O(k) boards per reward (where k = valid translation count, typically 10-20)

---

### Strategy 3: Canonical Tree Structure (Expert)

**Where**: Core MCTS tree structure

**How**: Modify the tree to use canonical hashes for node identification, merging symmetric states into single nodes.

```python
# In MCTSNode.__init__:
class MCTSNode:
    def __init__(self, state: Breadboard, parent: 'MCTSNode' = None,
                 action_from_parent: tuple = None):
        self.state = state
        self.canonical_state = get_canonical_form(state)  # Store canonical form
        self.canon_hash = hash(self.canonical_state)
        # ... rest of init

# In MCTS class:
class MCTS:
    def __init__(self, initial_state: Breadboard):
        self.root = MCTSNode(initial_state)
        self.node_registry = {}  # canon_hash -> MCTSNode (merge equivalent nodes)

    def search(self, iterations: int):
        # ... selection phase ...

        # When expanding, check if canonical form already exists
        if node.untried_actions:
            action = node.untried_actions.pop()
            new_state = node.state.apply_action(action)

            canon_hash_new = canonical_hash(new_state)
            if canon_hash_new in self.node_registry:
                # Reuse existing node for this canonical form
                child_node = self.node_registry[canon_hash_new]
            else:
                # Create new node
                child_node = MCTSNode(new_state, parent=node, action_from_parent=action)
                self.node_registry[canon_hash_new] = child_node

            node.children.append(child_node)
```

**Benefits**:
- Most powerful: truly merges symmetric states
- Maximizes statistical efficiency (all visits to symmetric states contribute to one node)
- Best long-term performance

**Limitations**:
- Complex to implement correctly
- Requires careful handling of parent/child relationships
- May have subtle bugs

---

## Recommended Implementation Path

### For Proof of Concept:
**Use Strategy 1** (Canonical State Deduplication with Caching)

1. Add `canonical_cache = {}` to MCTS.__init__()
2. Check cache before simulation in MCTS.search()
3. Store results in cache after simulation

**Expected gain**: 3-5x speedup on repeated topologies

### For Production:
**Combine Strategy 1 + Strategy 2** (Caching + Reward Broadcast)

1. Implement Strategy 1 first
2. Add reward broadcast to populate cache proactively
3. Monitor cache hit rate to validate effectiveness

**Expected gain**: 5-10x speedup with high cache hit rates

---

## Performance Monitoring

Add these metrics to track augmentation effectiveness:

```python
class MCTS:
    def __init__(self, initial_state: Breadboard):
        self.root = MCTSNode(initial_state)
        self.canonical_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def search(self, iterations: int):
        # ... in simulation phase ...
        canon_hash = canonical_hash(node.state)

        if canon_hash in self.canonical_cache:
            reward = self.canonical_cache[canon_hash]
            self.cache_hits += 1
        else:
            # Run simulation
            reward = calculate_reward_from_simulation(freq, vout)
            self.canonical_cache[canon_hash] = reward
            self.cache_misses += 1

        # ... at end of search ...
        hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses)
        print(f"Cache hit rate: {hit_rate:.2%}")
        print(f"Unique topologies explored: {len(self.canonical_cache)}")
```

---

## Example Usage

```python
from core.topology_game_board import Breadboard
from core.MCTS import MCTS
from utils.augmentation import (
    canonical_hash,
    generate_translations,
    count_unique_topologies
)

# Initialize MCTS with augmentation
initial_board = Breadboard()
mcts = MCTS(initial_board)

# Run search
mcts.search(iterations=10000)

# Get results
path, reward = mcts.get_best_solution()

# Analyze performance
print(f"Cache hit rate: {mcts.cache_hits / (mcts.cache_hits + mcts.cache_misses):.2%}")
print(f"Unique topologies: {len(mcts.canonical_cache)}")
print(f"Total iterations: 10000")
```

---

## Testing Augmentation

Verify augmentation is working correctly:

```bash
# Run augmentation unit tests
python3 utils/test_augmentation.py

# Run MCTS with caching enabled
python3 core/test_mcts_search.py

# Check for these indicators:
# 1. Cache hit rate > 0% (ideally 20-50%)
# 2. Unique topologies < total iterations
# 3. Faster convergence to good circuits
```

---

## Troubleshooting

**Problem**: Cache hit rate is 0%

**Solution**: Check that `canonical_hash()` is being called correctly. Verify circuits are actually repeating.

**Problem**: Different rewards for same canonical form

**Solution**: This is expected if circuits are incomplete (heuristic rewards vary). Only complete circuits should have identical rewards.

**Problem**: Cache growing too large

**Solution**: Implement cache eviction (LRU cache) or only cache complete circuits with high rewards.

---

## Next Steps

1. **Implement Strategy 1** (5-10 minutes)
2. **Run test search** (1000 iterations) and measure cache hit rate
3. **If hit rate > 10%**, proceed to Strategy 2
4. **Benchmark**: Compare search time with/without caching

Expected timeline:
- Strategy 1 implementation: 10 minutes
- Testing and validation: 20 minutes
- Strategy 2 (optional): 30 minutes
- **Total**: 30-60 minutes for significant performance gain
