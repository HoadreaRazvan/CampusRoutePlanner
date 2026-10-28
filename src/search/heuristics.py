import math
from typing import List, Optional, Tuple
from src.models.graph import Graph, Edge
from src.search.best_first import Heuristic

# Client note for graph2_campus: nobody walks faster than 80 metres per minute in a straight line.
DEFAULT_V_MAX = 80.0


def zero_heuristic(node_id: str) -> float:
    return 0.0


def has_coordinates(graph: Graph) -> bool:
    return bool(graph.nodes) and all(n.x is not None and n.y is not None for n in graph.nodes.values())


def straight_line(graph: Graph, a: str, b: str) -> float:
    na, nb = graph.nodes[a], graph.nodes[b]
    return math.hypot(na.x - nb.x, na.y - nb.y)


def check_consistency(graph: Graph, v_max: float = DEFAULT_V_MAX) -> List[Edge]:
    """Returns the edges that are faster than v_max allows, i.e. where distance / v_max > travel time.

    If the list is empty, h(n) = distance(n, goal) / v_max is consistent: for every edge n->m,
    h(n) <= distance(n, m) / v_max + h(m) <= cost(n, m) + h(m) (triangle inequality).
    A consistent heuristic with h(goal) = 0 is also admissible.
    """
    return [
        edge
        for edges in graph.adjacency.values()
        for edge in edges
        if straight_line(graph, edge.source, edge.destination) / v_max > edge.weight + 1e-9
    ]


def euclidean_heuristic(graph: Graph, goal: str, v_max: float = DEFAULT_V_MAX) -> Heuristic:
    if v_max <= 0:
        raise ValueError(f"v_max must be positive, got {v_max}")
    return lambda node_id: straight_line(graph, node_id, goal) / v_max


def choose_heuristic(graph: Graph, goal: str, v_max: float = DEFAULT_V_MAX) -> Tuple[Heuristic, Optional[str]]:
    """Euclidean heuristic when the data supports it, otherwise h = 0 and the reason why."""
    if not has_coordinates(graph):
        return zero_heuristic, "not every building has coordinates, A* uses h = 0 (same as UCS)"
    too_fast = check_consistency(graph, v_max)
    if too_fast:
        names = ", ".join(f"{e.source}>{e.destination}" for e in too_fast[:5])
        return zero_heuristic, (
            f"{len(too_fast)} edge(s) faster than {v_max:g} m/min ({names}), "
            "the Euclidean heuristic could overestimate, A* uses h = 0 (same as UCS)"
        )
    return euclidean_heuristic(graph, goal, v_max), None
