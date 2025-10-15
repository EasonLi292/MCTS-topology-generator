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

    def select_child(self, exploration_constant: float = 1.0) -> 'MCTSNode':
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
        # Track statistics
        spice_success_count = 0
        spice_fail_count = 0
        max_reward_seen = 0.0

        for i in range(iterations):
            if (i % 1000 == 0):
                print(f"Running iteration {i}/{iterations}... (SPICE: {spice_success_count} success, {spice_fail_count} fail, max reward: {max_reward_seen:.2f})")

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
            # This encourages exploration toward circuits with diverse components
            num_components = len([c for c in current_state.placed_components
                                 if c.type not in ['wire', 'vin', 'vout']])
            num_wires = len([c for c in current_state.placed_components if c.type == 'wire'])
            unique_types = len({c.type for c in current_state.placed_components
                               if c.type not in ['wire', 'vin', 'vout']})

            # REDUCED heuristic reward for incomplete circuits to prevent premature convergence
            # Component diversity is key but scaled down: 0.2 per component, 0.5 per unique type
            heuristic_reward = (num_components * 0.2) + (unique_types * 0.5) - (num_wires * 0.1)

            if current_state.is_complete_and_valid():
                netlist = current_state.to_netlist()
                if netlist:
                    try:
                        # Run the full SPICE simulation and scoring
                        freq, vout = run_ac_simulation(netlist)
                        spice_reward = calculate_reward_from_simulation(freq, vout)

                        # SPICE results are MOST IMPORTANT - they dominate the reward
                        if spice_reward > 0:
                            # Progressive completion bonus: reward circuit complexity
                            complexity_bonus = (unique_types * 5.0) + (num_components * 2.0)

                            # SPICE reward now comes pre-scaled from simulator (baseline 5.0+)
                            # Add complexity bonus to encourage diverse, multi-component circuits
                            reward = spice_reward + complexity_bonus
                            spice_success_count += 1
                            if reward > max_reward_seen:
                                max_reward_seen = reward
                        else:
                            # SPICE failed or returned 0 - use small positive reward
                            # Avoid negative rewards which poison the search tree
                            reward = max(0.01, heuristic_reward * 0.1)
                            spice_fail_count += 1
                    except Exception as e:
                        # SPICE simulation crashed - use small positive reward
                        reward = max(0.01, heuristic_reward * 0.1)
                        spice_fail_count += 1
                else:
                    # Netlist generation failed - shouldn't happen for valid circuits
                    # Use small positive reward to avoid poisoning the tree
                    reward = max(0.01, heuristic_reward * 0.1)
            else:
                # Incomplete circuit uses small heuristic only to guide exploration
                # Ensure it's always positive to avoid tree poisoning
                reward = max(0.0, heuristic_reward)
            
            # 4. Backpropagation: Update the nodes from the leaf back to the root
            while node:
                node.update(reward)
                node = node.parent
                
        print("Search complete.")

    def get_best_solution(self) -> tuple[list[tuple], float]:
        """
        Returns the best complete circuit found during the search.
        Searches the entire tree for complete circuits and returns the best one.
        """
        best_path = []
        best_reward = 0.0

        # Recursively search for all complete circuits
        def find_complete_circuits(node: MCTSNode, path: list[tuple]) -> list[tuple[list[tuple], float]]:
            circuits = []

            # Check if this node represents a complete circuit
            if node.state.is_complete_and_valid():
                avg_reward = node.wins / node.visits if node.visits > 0 else 0
                circuits.append((path.copy(), avg_reward))

            # Recursively check children
            # Lower threshold for deeper nodes since they naturally get fewer visits
            min_visits = max(1, 5 - len(path))  # Depth 0: 5 visits, depth 1: 4 visits, depth 4+: 1 visit
            for child in node.children:
                if child.visits >= min_visits:
                    child_path = path + ([child.action_from_parent] if child.action_from_parent else [])
                    circuits.extend(find_complete_circuits(child, child_path))

            return circuits

        # Find all complete circuits
        all_circuits = find_complete_circuits(self.root, [])

        if all_circuits:
            # Select the circuit with highest average reward
            best_path, best_reward = max(all_circuits, key=lambda x: x[1])
        else:
            # Fallback to greedy selection if no complete circuits found
            current_node = self.root
            while current_node.children:
                valid_children = [c for c in current_node.children if c.visits >= 5]
                if not valid_children:
                    best_child = max(current_node.children, key=lambda c: c.visits)
                else:
                    best_child = max(valid_children, key=lambda c: c.wins / c.visits if c.visits > 0 else 0)

                if best_child.action_from_parent:
                    best_path.append(best_child.action_from_parent)
                current_node = best_child

            best_reward = current_node.wins / current_node.visits if current_node.visits > 0 else 0.0

        return best_path, best_reward