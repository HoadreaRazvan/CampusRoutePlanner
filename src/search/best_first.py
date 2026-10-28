import heapq
import time
from typing import Callable, Dict, List, Optional, Tuple
from src.models.graph import Graph
from src.models.state import State
from src.search.base import SearchResult

Heuristic = Callable[[str], float]


def best_first_search(
    graph: Graph,
    start: str,
    destination: str,
    heuristic: Heuristic,
    required_visit: Optional[str] = None,
    blocked_edges: Optional[List[Tuple[str, str]]] = None,
    trace: Optional[List[Tuple[str, bool, float, float]]] = None
) -> SearchResult:
    """Shared core of UCS (h = 0) and A*: always expands the state with the lowest f = g + h.

    The goal test runs when a state is popped, not when it is generated, so the first goal
    popped is optimal (as long as h is consistent). States are (building, visited_required),
    so the same building can be reached twice: once before and once after the required stop.

    If `trace` is given, every expanded state is appended to it as (building, visited_required, g, f),
    in expansion order (used by the GUI to replay the search).
    """
    began = time.perf_counter()
    blocked = list(blocked_edges or [])

    start_state = State(start, required_visit is None or start == required_visit)
    counter = 0
    frontier = [(heuristic(start), 0.0, counter, start_state)]
    best_g: Dict[State, float] = {start_state: 0.0}
    parent: Dict[State, Optional[State]] = {start_state: None}
    closed = set()
    expanded = 0

    while frontier:
        f, g, _, state = heapq.heappop(frontier)
        if state in closed:
            continue  # stale entry: this state was already expanded with a lower cost
        closed.add(state)
        expanded += 1
        if trace is not None:
            trace.append((state.current_node, state.has_visited_required, g, f))

        if state.current_node == destination and state.has_visited_required:
            return SearchResult(
                path=_rebuild_path(parent, state),
                total_cost=g,
                expanded_states=expanded,
                runtime_ms=_elapsed_ms(began),
                success=True
            )

        for edge in graph.get_neighbors(state.current_node, blocked):
            visited = state.has_visited_required or edge.destination == required_visit
            child = State(edge.destination, visited)
            new_g = g + edge.weight
            if child in closed or new_g >= best_g.get(child, float("inf")):
                continue
            best_g[child] = new_g
            parent[child] = state
            counter += 1
            heapq.heappush(frontier, (new_g + heuristic(edge.destination), new_g, counter, child))

    return SearchResult.no_route(expanded_states=expanded, runtime_ms=_elapsed_ms(began))


def _rebuild_path(parent: Dict[State, Optional[State]], state: State) -> List[str]:
    path = []
    current: Optional[State] = state
    while current is not None:
        path.append(current.current_node)
        current = parent[current]
    return path[::-1]


def _elapsed_ms(began: float) -> float:
    return (time.perf_counter() - began) * 1000
