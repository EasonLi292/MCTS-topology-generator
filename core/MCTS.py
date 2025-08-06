"""Core Monte Carlo Tree Search (MCTS) utilities."""

import math
from dataclasses import dataclass, field
from typing import List, Optional
from copy import deepcopy

# The original implementation attempted to import ``Breadboard`` using a
# direct module name. When this file is imported as part of the ``core``
# package (e.g. ``from core.MCTS import MCTSNode``), that absolute import
# fails because ``topology_game_board`` is not on ``sys.path``. Using a
# relative import ensures the module resolves correctly regardless of how
# the package is executed.
from .topology_game_board import Breadboard

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