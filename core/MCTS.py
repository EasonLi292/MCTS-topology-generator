# MCTS.py

import math
import random
from topology_game_board import Breadboard
from spice_simulator import run_ac_simulation, calculate_reward_from_simulation

class MCTSNode:
    """
    Represents a single state (a breadboard layout) in the MCTS search tree.
    """
    def __init__(self, state: Breadboard, parent: 'MCTSNode' = None, action_from_parent: tuple = None):
        self.state: Breadboard = state
        self.parent: 'MCTSNode' = parent
        self.action_from_parent: tuple = action_from_parent  # Action that led to this node
        self.children: list['MCTSNode'] = []

        # Statistics for the UCT formula
        self.wins: float = 0.0
        self.visits: int = 0

        # A list of actions that have not yet been explored from this node
        self.untried_actions: list[tuple] = self.state.legal_actions()

    def select_child(self, exploration_constant: float = 1.41) -> 'MCTSNode':
        """
        Selects the best child node using the UCT (Upper Confidence Bound for Trees) formula.
        This balances exploiting known good paths and exploring less-visited ones.
        """
        if not self.children:
            raise ValueError("Cannot select child from node with no children")

        def uct_value(child: 'MCTSNode') -> float:
            if child.visits == 0:
                return float('inf')  # Prioritize unvisited children
            exploitation = child.wins / child.visits
            exploration = exploration_constant * math.sqrt(math.log(self.visits) / child.visits)
            return exploitation + exploration

        best_child = max(self.children, key=uct_value)
        return best_child

    def expand(self) -> 'MCTSNode':
        """
        Expands the tree by trying a new, unexplored action.
        It creates a new child node for the resulting state.
        """
        if not self.untried_actions:
            raise ValueError("Cannot expand node with no untried actions")

        action = self.untried_actions.pop()
        new_state = self.state.apply_action(action)
        child_node = MCTSNode(new_state, parent=self, action_from_parent=action)
        self.children.append(child_node)
        return child_node

    def update(self, reward: float):
        """
        Backpropagates the result of a simulation up the tree.
        Updates the visit counts and win scores for this node.
        """
        self.visits += 1
        self.wins += reward

class MCTS:
    """
    The main class to run the Monte Carlo Tree Search algorithm.
    """
    def __init__(self, initial_state: Breadboard):
        self.root = MCTSNode(initial_state)

    def search(self, iterations: int):
        """
        Runs the MCTS algorithm for a specified number of iterations using
        PySPICE to evaluate terminal states instead of random rollouts.
        """
        for i in range(iterations):
            if (i % 1000 == 0):
                print(f"Running iteration {i}/{iterations}...")

            node = self.root

            # 1. Selection: Traverse the tree to find a promising leaf node
            while not node.untried_actions and node.children:
                node = node.select_child()

            # 2. Expansion: If the node is not terminal, expand it by one action
            if node.untried_actions:
                node = node.expand()

            # 3. Simulation: Evaluate the state of the new node using PySPICE.
            # Note: We are not performing a random "rollout" to the end.
            # We evaluate the quality of the circuit as soon as it's complete.
            current_state = node.state

            # Calculate heuristic reward based on circuit complexity
            num_components = len([c for c in current_state.placed_components
                                 if c.type not in ['wire', 'vin', 'vout']])
            num_wires = len([c for c in current_state.placed_components if c.type == 'wire'])
            unique_types = len({c.type for c in current_state.placed_components
                               if c.type not in ['wire', 'vin', 'vout']})

            # Base heuristic reward: components are good, diversity is better, excessive wires are bad
            heuristic_reward = (num_components * 2.0) + (unique_types * 5.0) - (num_wires * 0.5)

            if current_state.is_complete_and_valid():
                # Complete circuit gets bonus
                completion_bonus = 10.0

                netlist = current_state.to_netlist()
                if netlist:
                    try:
                        # Run the full SPICE simulation and scoring
                        freq, vout = run_ac_simulation(netlist)
                        spice_reward = calculate_reward_from_simulation(freq, vout)

                        # If SPICE simulation worked, use it; otherwise use heuristic
                        if spice_reward > 0:
                            reward = spice_reward + completion_bonus
                        else:
                            reward = heuristic_reward + completion_bonus
                    except Exception as e:
                        # SPICE simulation failed, use heuristic
                        reward = heuristic_reward + completion_bonus
                else:
                    # Netlist generation failed (should be rare)
                    reward = -1.0
            else:
                # Incomplete circuit uses heuristic only
                reward = heuristic_reward
            
            # 4. Backpropagation: Update the nodes from the leaf back to the root
            while node:
                node.update(reward)
                node = node.parent
                
        print("Search complete.")

    def get_best_solution(self) -> tuple[list[tuple], float]:
        """
        Returns the best sequence of actions found during the search.
        The "best" is defined as the path most visited from the root.
        """
        path = []
        current_node = self.root
        best_avg_reward = 0.0

        while current_node.children:
            # Choose the child that was explored the most
            best_child = max(current_node.children, key=lambda c: c.visits)

            # Use the stored action instead of reconstructing it
            if best_child.action_from_parent:
                path.append(best_child.action_from_parent)

            current_node = best_child

        # Use the average reward from MCTS statistics (what we actually optimized for)
        if current_node.visits > 0:
            best_avg_reward = current_node.wins / current_node.visits

        return path, best_avg_reward