# MCTS.py
# Monte Carlo Tree Search implementation for circuit topology generation.
# Refactored to follow SOLID principles with small, focused functions.

import math
import random
from topology_game_board import Breadboard
from spice_simulator import run_ac_simulation, calculate_reward_from_simulation

# Reward tuning constants
INCOMPLETE_REWARD_CAP = 40.0
COMPLETION_BASELINE_REWARD = 45.0


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

        Args:
            exploration_constant: Weight for exploration vs exploitation trade-off

        Returns:
            The child node with highest UCT value

        Raises:
            ValueError: If this node has no children
        """
        if not self.children:
            raise ValueError("Cannot select child from node with no children")

        best_child = max(self.children, key=lambda child: self._calculate_uct_value(child, exploration_constant))
        return best_child

    def _calculate_uct_value(self, child: 'MCTSNode', exploration_constant: float) -> float:
        """
        Calculates the UCT (Upper Confidence bound applied to Trees) value for a child node.

        UCT = exploitation_term + exploration_term
        - Exploitation term: average reward (wins/visits)
        - Exploration term: encourages visiting less-explored nodes

        Args:
            child: The child node to evaluate
            exploration_constant: Weight for the exploration term

        Returns:
            UCT value (higher = more promising)
        """
        # Unvisited children get infinite priority
        if child.visits == 0:
            return float('inf')

        # Calculate exploitation term: average reward
        exploitation = child.wins / child.visits

        # Calculate exploration term: prefer less-visited nodes
        exploration = exploration_constant * math.sqrt(math.log(self.visits) / child.visits)

        return exploitation + exploration

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

class CircuitStatistics:
    """
    Tracks statistics during MCTS search.
    Follows Single Responsibility Principle: only handles statistics tracking.
    """
    def __init__(self):
        self.spice_success_count: int = 0
        self.spice_fail_count: int = 0
        self.max_reward_seen: float = 0.0

    def record_spice_success(self, reward: float):
        """Records a successful SPICE simulation and updates max reward."""
        self.spice_success_count += 1
        if reward > self.max_reward_seen:
            self.max_reward_seen = reward

    def record_spice_failure(self):
        """Records a failed SPICE simulation."""
        self.spice_fail_count += 1

    def print_progress(self, iteration: int, total_iterations: int):
        """
        Prints search progress to console.

        Args:
            iteration: Current iteration number
            total_iterations: Total number of iterations
        """
        print(f"Running iteration {iteration}/{total_iterations}... "
              f"(SPICE: {self.spice_success_count} success, {self.spice_fail_count} fail, "
              f"max reward: {self.max_reward_seen:.2f})")


class MCTS:
    """
    The main class to run the Monte Carlo Tree Search algorithm.
    Follows SOLID principles with separated concerns and focused methods.
    """
    def __init__(self, initial_state: Breadboard):
        self.root = MCTSNode(initial_state)
        self.best_candidate_state = None
        self.best_candidate_reward = 0.0

    def search(self, iterations: int):
        """
        Runs the MCTS algorithm for a specified number of iterations.

        Args:
            iterations: Number of MCTS iterations to perform
        """
        stats = CircuitStatistics()

        for i in range(iterations):
            # Print progress every 1000 iterations
            if (i % 1000 == 0):
                stats.print_progress(i, iterations)

            # Execute one MCTS iteration
            self._execute_iteration(stats)

        print("Search complete.")

    def _execute_iteration(self, stats: CircuitStatistics):
        """
        Executes a single MCTS iteration: selection, expansion, simulation, and backpropagation.

        Args:
            stats: Statistics tracker for this search session
        """
        # 1. Selection: Traverse tree to find a promising leaf node
        node = self._select_leaf_node()

        # 2. Expansion: Expand the node if it has untried actions
        if node.untried_actions:
            node = node.expand()

        # 3. Simulation: Evaluate the circuit and calculate reward
        reward = self._evaluate_circuit(node.state, stats)

        # Track best candidate
        self._update_best_candidate(node.state, reward)

        # 4. Backpropagation: Update statistics up the tree
        self._backpropagate(node, reward)

    def _select_leaf_node(self) -> MCTSNode:
        """
        Selects a leaf node by traversing the tree using UCT.

        Traverses from root to a leaf node by repeatedly selecting the best child
        until reaching a node with untried actions or no children.

        Returns:
            A leaf node (either has untried actions or is terminal)
        """
        node = self.root
        while not node.untried_actions and node.children:
            node = node.select_child()
        return node

    def _evaluate_circuit(self, state: Breadboard, stats: CircuitStatistics) -> float:
        """
        Evaluates a circuit state and returns a reward score.

        Uses a combination of heuristics and SPICE simulation.
        Complete circuits are evaluated using SPICE for accurate electrical analysis.

        Args:
            state: The breadboard state to evaluate
            stats: Statistics tracker to record simulation results

        Returns:
            Reward score (higher = better circuit)
        """
        # Calculate circuit metrics
        metrics = self._calculate_circuit_metrics(state)

        # Calculate heuristic reward for incomplete circuits
        heuristic_reward = self._calculate_heuristic_reward(metrics)

        # Complete circuits get SPICE evaluation
        if state.is_complete_and_valid() and metrics['num_components'] >= 1:
            return self._evaluate_with_spice(state, metrics, heuristic_reward, stats)
        else:
            # Incomplete circuit: use heuristic only (always positive)
            # Cap lower than completed baseline so MCTS still prefers completion
            return max(0.0, min(heuristic_reward, INCOMPLETE_REWARD_CAP))

    def _calculate_circuit_metrics(self, state: Breadboard) -> dict:
        """
        Calculates various metrics about the circuit composition.

        Args:
            state: The breadboard state to analyze

        Returns:
            Dictionary containing circuit metrics:
            - num_components: Count of non-wire, non-IO components
            - num_wires: Count of wire connections
            - unique_types: Count of unique component types
            - vin_row: Row position of VIN (-1 if not found)
            - vout_row: Row position of VOUT (-1 if not found)
            - vin_vout_connected: Boolean indicating if VIN and VOUT are electrically connected
        """
        connectivity = state.get_connectivity_summary()

        # Count components (excluding wires and I/O)
        num_components = len([c for c in state.placed_components
                             if c.type not in ['wire', 'vin', 'vout']])

        # Count wires
        num_wires = len([c for c in state.placed_components if c.type == 'wire'])

        # Count unique component types
        unique_types = len({c.type for c in state.placed_components
                           if c.type not in ['wire', 'vin', 'vout']})

        # Find VIN and VOUT positions
        vin_row = next((c.pins[0][0] for c in state.placed_components if c.type == 'vin'), -1)
        vout_row = next((c.pins[0][0] for c in state.placed_components if c.type == 'vout'), -1)

        # FIXED: Check if VIN and VOUT are connected through COMPONENT GRAPH
        # Use same metric as validation (reachable_vout) instead of union-find
        # This prevents rewarding direct VIN→VOUT wires that won't become valid
        vin_vout_connected = connectivity.get('reachable_vout', False)

        supply_connected = connectivity["rails_in_component"]["VDD"] and connectivity["rails_in_component"]["0"]

        return {
            'num_components': num_components,
            'num_wires': num_wires,
            'unique_types': unique_types,
            'vin_row': vin_row,
            'vout_row': vout_row,
            'vin_vout_connected': vin_vout_connected,
            'touches_vdd': connectivity.get('touches_vdd', False),
            'touches_vss': connectivity.get('touches_vss', False),
            'supply_connected': supply_connected,
            'has_active_components': connectivity.get('has_active_components', False),
            'vin_on_power_rail': connectivity.get('vin_on_power_rail', False),
            'vout_on_power_rail': connectivity.get('vout_on_power_rail', False),
            'degenerate_component': connectivity.get('degenerate_component', False),
            'vin_vout_distinct': connectivity.get('vin_vout_distinct', True),
            'connectivity': connectivity
        }

    def _calculate_connection_bonus(self, metrics: dict) -> float:
        """
        Calculates reward bonus for VIN-VOUT connectivity.

        Args:
            metrics: Circuit metrics dictionary

        Returns:
            Connection bonus value (can be positive or negative)
        """
        if metrics['vin_vout_connected']:
            # Connected! But only give bonus if there are components in the circuit
            # This prevents the algorithm from just wiring vin→vout directly
            if metrics['num_components'] > 0:
                base = 20.0
            else:
                base = 5.0  # Small bonus for empty direct connection
        else:
            # Not connected yet - small penalty to encourage connection
            base = -2.0

        if metrics['num_components'] > 0 and metrics.get('supply_connected'):
            base += 10.0

        return base

    def _calculate_heuristic_reward(self, metrics: dict) -> float:
        """
        Calculates heuristic reward based on circuit complexity.

        Encourages circuits with diverse components and proper connectivity.
        IMPROVED: Added progressive rewards for meeting validation criteria.

        Args:
            metrics: Circuit metrics dictionary

        Returns:
            Heuristic reward score
        """
        connection_bonus = self._calculate_connection_bonus(metrics)
        conn = metrics.get('connectivity', {})

        # Heavy penalties for invalid power-rail placements or degenerate structures
        if metrics.get('vin_on_power_rail') or metrics.get('vout_on_power_rail'):
            return -25.0
        if not metrics.get('vin_vout_distinct', True):
            return -20.0
        if metrics.get('degenerate_component'):
            return -15.0

        # Reward component count and diversity
        heuristic_reward = (metrics['num_components'] * 5.0) + \
                          (metrics['unique_types'] * 8.0) + \
                          connection_bonus

        # IMPROVED: Progressive rewards for meeting validation requirements
        # This guides the search toward valid circuits step-by-step
        if conn.get('touches_vdd', False):
            heuristic_reward += 8.0  # Reward touching VDD
        if conn.get('touches_vss', False):
            heuristic_reward += 8.0  # Reward touching VSS
        if conn.get('reachable_vout', False):
            heuristic_reward += 15.0  # Big reward for VIN->VOUT path
        if conn.get('all_components_reachable', False):
            heuristic_reward += 10.0  # Reward having all components connected

        return heuristic_reward

    def _evaluate_with_spice(self, state: Breadboard, metrics: dict,
                             heuristic_reward: float, stats: CircuitStatistics) -> float:
        """
        Evaluates a complete circuit using SPICE simulation.

        Args:
            state: The breadboard state to simulate
            metrics: Circuit metrics dictionary
            heuristic_reward: Fallback heuristic reward if SPICE fails
            stats: Statistics tracker

        Returns:
            Reward score based on SPICE simulation results
        """
        netlist = state.to_netlist()
        if not netlist:
            # Netlist generation failed - but it's still a complete circuit
            # Give it a baseline reward higher than any incomplete circuit (if component count justifies it)
            return self._baseline_completion_reward(metrics['num_components'])

        try:
            # Run the full SPICE simulation and scoring
            freq, vout = run_ac_simulation(netlist)
            spice_reward = calculate_reward_from_simulation(freq, vout)

            if spice_reward > 0:
                # SPICE simulation succeeded
                return self._calculate_final_reward(spice_reward, metrics, stats)
            else:
                # SPICE failed or returned 0 - but it's still a complete circuit
                # Give baseline reward higher than incomplete circuits
                stats.record_spice_failure()
                return self._baseline_completion_reward(metrics['num_components'])

        except Exception as e:
            # SPICE simulation crashed - but it's still a complete circuit
            # Give baseline reward higher than incomplete circuits
            stats.record_spice_failure()
            return self._baseline_completion_reward(metrics['num_components'])

    def _calculate_final_reward(self, spice_reward: float, metrics: dict,
                                stats: CircuitStatistics) -> float:
        """
        Calculates final reward combining SPICE results and complexity bonuses.

        Args:
            spice_reward: Base reward from SPICE simulation
            metrics: Circuit metrics dictionary
            stats: Statistics tracker

        Returns:
            Final combined reward score
        """
        # Progressive completion bonus: reward circuit complexity
        complexity_bonus = (metrics['unique_types'] * 5.0) + (metrics['num_components'] * 2.0)

        # SPICE reward now comes pre-scaled from simulator (baseline 100.0+)
        # Add complexity bonus to encourage diverse, multi-component circuits
        reward = spice_reward + complexity_bonus

        # Ensure completed circuits ALWAYS score higher than incomplete (capped at INCOMPLETE_REWARD_CAP)
        baseline_reward = self._baseline_completion_reward(metrics['num_components'])
        reward = max(reward, baseline_reward)

        stats.record_spice_success(reward)
        return reward

    def _baseline_completion_reward(self, num_components: int) -> float:
        """Computes the minimum reward assigned to a completed circuit."""
        return COMPLETION_BASELINE_REWARD + max(0, num_components)

    def _update_best_candidate(self, state: Breadboard, reward: float):
        """
        Updates the best candidate circuit if current reward is higher.

        Args:
            state: Current circuit state
            reward: Reward for this circuit
        """
        if reward > self.best_candidate_reward:
            self.best_candidate_reward = reward
            self.best_candidate_state = state

    def _backpropagate(self, node: MCTSNode, reward: float):
        """
        Backpropagates reward from a leaf node to the root.

        Updates visit counts and reward statistics for all nodes
        along the path from the given node to the root.

        Args:
            node: Starting node (typically a leaf)
            reward: Reward value to propagate
        """
        while node:
            node.update(reward)
            node = node.parent

    def get_best_solution(self) -> tuple[list[tuple], float]:
        """
        Returns the best complete circuit found during the search.
        Searches the entire tree for complete circuits and returns the best one.

        Returns:
            Tuple of (action_path, average_reward)
        """
        # Find all complete circuits in the tree
        all_circuits = self._find_all_complete_circuits()

        if all_circuits:
            # Select the circuit with highest average reward
            best_path, best_reward = max(all_circuits, key=lambda x: x[1])
        else:
            # Fallback to greedy selection if no complete circuits found
            best_path, best_reward = self._greedy_path_selection()

        return best_path, best_reward

    def _find_all_complete_circuits(self) -> list[tuple[list[tuple], float]]:
        """
        Recursively searches the tree for all complete and valid circuits.

        Returns:
            List of (path, average_reward) tuples for each complete circuit found
        """
        return self._search_for_circuits(self.root, [])

    def _search_for_circuits(self, node: MCTSNode, path: list[tuple]) -> list[tuple[list[tuple], float]]:
        """
        Recursively searches from a node for complete circuits.

        Args:
            node: Current node to search from
            path: Path of actions taken to reach this node

        Returns:
            List of (path, average_reward) tuples
        """
        circuits = []

        # Check if this node represents a complete circuit
        if self._is_valid_complete_circuit(node):
            avg_reward = self._calculate_average_reward(node)
            circuits.append((path.copy(), avg_reward))

        # Recursively check children with sufficient visits
        min_visits = self._calculate_min_visits_threshold(len(path))
        for child in node.children:
            if child.visits >= min_visits:
                child_path = self._extend_path(path, child)
                circuits.extend(self._search_for_circuits(child, child_path))

        return circuits

    def _is_valid_complete_circuit(self, node: MCTSNode) -> bool:
        """
        Checks if a node represents a complete and valid circuit.

        Args:
            node: Node to check

        Returns:
            True if the node has a complete circuit with at least 1 component
        """
        if not node.state.is_complete_and_valid():
            return False

        num_components = len([c for c in node.state.placed_components
                             if c.type not in ['wire', 'vin', 'vout']])
        return num_components >= 1

    def _calculate_average_reward(self, node: MCTSNode) -> float:
        """
        Calculates the average reward for a node.

        Args:
            node: Node to calculate reward for

        Returns:
            Average reward (wins/visits), or 0 if unvisited
        """
        return node.wins / node.visits if node.visits > 0 else 0.0

    def _calculate_min_visits_threshold(self, depth: int) -> int:
        """
        Calculates the minimum visit threshold for a node at a given depth.

        Lower threshold for deeper nodes since they naturally get fewer visits.

        Args:
            depth: Depth in the tree (path length)

        Returns:
            Minimum number of visits required
        """
        # Depth 0: 5 visits, depth 1: 4 visits, depth 4+: 1 visit
        return max(1, 5 - depth)

    def _extend_path(self, path: list[tuple], child: MCTSNode) -> list[tuple]:
        """
        Extends a path with a child's action.

        Args:
            path: Current action path
            child: Child node to add

        Returns:
            Extended path (original path is not modified)
        """
        if child.action_from_parent:
            return path + [child.action_from_parent]
        return path

    def _greedy_path_selection(self) -> tuple[list[tuple], float]:
        """
        Fallback method: greedily selects best path when no complete circuits found.

        Traverses from root, always selecting the best child by average reward.

        Returns:
            Tuple of (action_path, final_average_reward)
        """
        best_path = []
        current_node = self.root

        while current_node.children:
            best_child = self._select_best_child(current_node)

            if best_child.action_from_parent:
                best_path.append(best_child.action_from_parent)
            current_node = best_child

        best_reward = self._calculate_average_reward(current_node)
        return best_path, best_reward

    def _select_best_child(self, node: MCTSNode) -> MCTSNode:
        """
        Selects the best child from a node based on visit counts and average reward.

        Prefers children with at least 5 visits, falling back to most-visited child.

        Args:
            node: Parent node

        Returns:
            Best child node
        """
        # Filter children with sufficient visits
        valid_children = [c for c in node.children if c.visits >= 5]

        if not valid_children:
            # No well-visited children, pick most visited
            return max(node.children, key=lambda c: c.visits)
        else:
            # Pick child with best average reward
            return max(valid_children, key=lambda c: self._calculate_average_reward(c))
