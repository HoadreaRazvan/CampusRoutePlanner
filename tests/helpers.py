from pathlib import Path
from typing import List, Tuple

import pytest
from src.io import DataLoader
from src.models.graph import Graph
from src.models.task import Task
from src.search.base import BaseSearchAlgorithm, SearchResult

DATA = Path(__file__).resolve().parent.parent / "data"


def load_folder(folder: Path) -> Tuple[Graph, List[Task]]:
    """Loads edges.csv, nodes.csv (if present) and tasks.csv, and validates every task."""
    nodes = folder / "nodes.csv"
    graph = DataLoader.load_graph(str(folder / "edges.csv"), str(nodes) if nodes.exists() else None)
    tasks = DataLoader.load_tasks(str(folder / "tasks.csv"))
    for task in tasks:
        DataLoader.validate_task(graph, task)
    return graph, tasks


def run(algorithm: BaseSearchAlgorithm, graph: Graph, task: Task) -> SearchResult:
    return algorithm.solve(graph, task.start, task.destination, task.required_visit, task.blocked_edges)


def assert_valid_route(graph: Graph, task: Task, result: SearchResult) -> None:
    """Checks the route on its own, without knowing which of several equally good routes was chosen."""
    assert result.success, f"{task.task_id}: expected a route, got {result.status_message}"
    path = result.path
    assert path[0] == task.start
    assert path[-1] == task.destination
    if task.required_visit is not None:
        assert task.required_visit in path

    blocked = set(task.blocked_edges)
    cost = 0.0
    for u, v in zip(path, path[1:]):
        assert (u, v) not in blocked, f"{task.task_id}: route uses blocked edge {u}>{v}"
        weights = [e.weight for e in graph.adjacency.get(u, []) if e.destination == v]
        assert weights, f"{task.task_id}: {u}>{v} is not an edge of the graph"
        cost += min(weights)
    assert cost == pytest.approx(result.total_cost)


def assert_no_route(result: SearchResult) -> None:
    assert not result.success
    assert result.status_message == "NO_FEASIBLE_ROUTE"
    assert result.path == []
