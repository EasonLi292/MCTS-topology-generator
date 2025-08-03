import math
from dataclasses import dataclass, field
from typing import List, Optional
from copy import deepcopy
from topology_game_board import Breadboard

@dataclass
class MCTSNode:
    breadboard: Breadboard
    parent: Optional["MCTSNode"] = None
    children: List["MCTSNode"] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0

    def uct_score(self, exploration_weight=1.4) -> float: ...

def mcts_step(root: MCTSNode) -> MCTSNode:
    # Selection, Expansion, Simulation, Backpropagation
    ...