from typing import List, Optional, Tuple
from src.models.graph import Graph
from src.search.base import BaseSearchAlgorithm, SearchResult
from src.search.best_first import best_first_search
from src.search.heuristics import zero_heuristic


class UniformCostSearch(BaseSearchAlgorithm):
    """Uninformed baseline: expands states in order of path cost g only."""

    def solve(
        self,
        graph: Graph,
        start: str,
        destination: str,
        required_visit: Optional[str] = None,
        blocked_edges: Optional[List[Tuple[str, str]]] = None
    ) -> SearchResult:
        return best_first_search(graph, start, destination, zero_heuristic, required_visit, blocked_edges)
