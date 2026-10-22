import sys
from src.io.loader import DataLoader

def main():
    print("Campus Route Planner - Architecture Core Framework Ready.")
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli <path_to_edges.csv> [path_to_nodes.csv]")
        return

    edges_path = sys.argv[1]
    nodes_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        graph = DataLoader.load_graph(edges_path, nodes_path)
        print(f"Successfully loaded graph with {len(graph.nodes)} buildings/nodes.")
    except Exception as e:
        print(f"Error loading graph: {e}")

if __name__ == "__main__":
    main()