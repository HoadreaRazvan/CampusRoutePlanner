from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class Node:
    id: str
    x: Optional[float] = None
    y: Optional[float] = None

@dataclass
class Edge:
    source: str
    destination: str
    weight: float

    def __post_init__(self):
        if self.weight < 0:
            raise ValueError(f"INVALID_EDGE_WEIGHT: Edge {self.source}->{self.destination} has negative weight {self.weight}")

class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.adjacency: Dict[str, List[Edge]] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.adjacency:
            self.adjacency[edge.source] = []
        self.adjacency[edge.source].append(edge)

    def get_neighbors(self, node_id: str, blocked_edges: Optional[List[Tuple[str, str]]] = None) -> List[Edge]:
        blocked_set = set(blocked_edges) if blocked_edges else set()
        return [
            edge for edge in self.adjacency.get(node_id, [])
            if (edge.source, edge.destination) not in blocked_set
        ]