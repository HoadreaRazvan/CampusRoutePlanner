from typing import List, Optional, Tuple
from src.models.graph import Graph
from src.search.base import BaseSearchAlgorithm, SearchResult
from src.search.best_first import Heuristic, best_first_search
from src.search.heuristics import DEFAULT_V_MAX, choose_heuristic


class AStarSearch(BaseSearchAlgorithm):
    """Informed search: expands states in order of f = g + h.

    Without an explicit heuristic it uses distance / v_max when every building has coordinates
    and no edge breaks the speed limit; otherwise h = 0 and `last_warning` says why.
    """

    def __init__(self, heuristic: Optional[Heuristic] = None, v_max: float = DEFAULT_V_MAX):
        self.heuristic = heuristic
        self.v_max = v_max
        self.last_warning: Optional[str] = None

    def solve(
        self,
        graph: Graph,
        start: str,
        destination: str,
        required_visit: Optional[str] = None,
        blocked_edges: Optional[List[Tuple[str, str]]] = None
    ) -> SearchResult:
        heuristic = self.heuristic
        self.last_warning = None
        if heuristic is None:
            heuristic, self.last_warning = choose_heuristic(graph, destination, self.v_max)
        return best_first_search(graph, start, destination, heuristic, required_visit, blocked_edges)
