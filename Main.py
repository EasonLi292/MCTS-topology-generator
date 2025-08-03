from core.topology_game_board import Breadboard
from core.MCTS import MCTSNode, mcts_step

def train_mcts():
    root = MCTSNode(Breadboard())
    for _ in range(1000):
        root = mcts_step(root)
    best_circuit = max(root.children, key=lambda n: n.total_reward / n.visits).breadboard
    print(f"Best circuit found with reward: {best_circuit}")

if __name__ == "__main__":
    train_mcts()