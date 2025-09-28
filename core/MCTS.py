# MCTS.py

import math
import random
from topology_game_board import Breadboard
from spice_simulator import run_ac_simulation, calculate_reward_from_simulation

class MCTSNode:
    """
    Represents a single state (a breadboard layout) in the MCTS search tree.
    """
    def __init__(self, state: Breadboard, parent: 'MCTSNode' = None):
        self.state: Breadboard = state
        self.parent: 'MCTSNode' = parent
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
        best_child = max(self.children, key=lambda c: 
                         (c.wins / c.visits) + exploration_constant * math.sqrt(math.log(self.visits) / c.visits))
        return best_child

    def expand(self) -> 'MCTSNode':
        """
        Expands the tree by trying a new, unexplored action.
        It creates a new child node for the resulting state.
        """
        action = self.untried_actions.pop()
        new_state = self.state.apply_action(action)
        child_node = MCTSNode(new_state, parent=self)
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
        '''
        Runs the MCTS algorithm for a specified number of iterations using
        PySPICE to evaluate terminal states instead of random rollouts.
        '''
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
            reward = 0.0
            current_state = node.state
            
            if current_state.is_complete_and_valid():
                netlist = current_state.to_netlist()
                if netlist:
                    # Run the full SPICE simulation and scoring
                    freq, vout = run_ac_simulation(netlist)
                    reward = calculate_reward_from_simulation(freq, vout)
            
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
        final_reward = 0.0

        while current_node.children:
            # Choose the child that was explored the most
            best_child = max(current_node.children, key=lambda c: c.visits)
            
            # Find the action that led to this child
            action_taken = None
            for action in current_node.state.legal_actions():
                next_state_candidate = current_node.state.apply_action(action)
                if next_state_candidate == best_child.state:
                    action_taken = action
                    break
            
            if action_taken:
                path.append(action_taken)
            
            current_node = best_child
        
        if current_node.state.is_complete_and_valid():
            final_reward = current_node.state.get_reward()

        return path, final_reward