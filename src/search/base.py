from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional
from src.models.graph import Graph

@dataclass
class SearchResult:
    path: List[str]
    total_cost: float
    expanded_states: int
    runtime_ms: float
    success: bool
    status_message: str = "SUCCESS"

    @classmethod
    def no_route(cls, expanded_states: int = 0, runtime_ms: float = 0.0) -> "SearchResult":
        return cls(
            path=[],
            total_cost=float("inf"),
            expanded_states=expanded_states,
            runtime_ms=runtime_ms,
            success=False,
            status_message="NO_FEASIBLE_ROUTE"
        )

class BaseSearchAlgorithm(ABC):
    @abstractmethod
    def solve(
        self,
        graph: Graph,
        start: str,
        destination: str,
        required_visit: Optional[str] = None,
        blocked_edges: Optional[List[Tuple[str, str]]] = None
    ) -> SearchResult:
        """Executes the search query and returns telemetry metrics."""
        pass