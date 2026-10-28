"""Glue between the loader and the search algorithms, shared by the CLI, the benchmarks and any UI."""
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from src.io import DataLoader, InputValidationError
from src.models.graph import Graph
from src.models.task import Task
from src.search import AStarSearch, UniformCostSearch
from src.search.base import BaseSearchAlgorithm, SearchResult
from src.search.heuristics import DEFAULT_V_MAX

ALGORITHMS = ("ucs", "astar")
ALGORITHM_LABELS = {"ucs": "UCS", "astar": "A*"}
CSV_COLUMNS = [
    "task_id", "start", "goal", "blocked_edges", "required_visit", "algorithm", "status",
    "solution_cost", "path_sequence", "expanded_states", "runtime_ms", "error",
]


@dataclass
class Dataset:
    graph: Graph
    tasks: List[Task]
    edges_path: Path
    nodes_path: Optional[Path]
    tasks_path: Optional[Path]


@dataclass
class TaskRun:
    task: Task
    algorithm: str
    result: Optional[SearchResult]
    warnings: List[str]
    error: Optional[str] = None

    @property
    def status(self) -> str:
        return "INVALID_REQUEST" if self.error else self.result.status_message


def resolve_paths(location: str) -> Tuple[Path, Optional[Path], Optional[Path]]:
    """Accepts a folder holding edges.csv (+ optional nodes.csv, tasks.csv) or the path to an edges file."""
    path = Path(location)
    if path.is_dir():
        folder, edges = path, path / "edges.csv"
    else:
        folder, edges = path.parent, path
    nodes, tasks = folder / "nodes.csv", folder / "tasks.csv"
    return edges, nodes if nodes.is_file() else None, tasks if tasks.is_file() else None


def load_dataset(location: str, tasks_path: Optional[str] = None) -> Dataset:
    edges, nodes, tasks = resolve_paths(location)
    if tasks_path:
        tasks = Path(tasks_path)
    graph = DataLoader.load_graph(str(edges), str(nodes) if nodes else None)
    task_list = DataLoader.load_tasks(str(tasks)) if tasks else []
    return Dataset(graph, task_list, edges, nodes, tasks)


def make_algorithm(name: str, v_max: float = DEFAULT_V_MAX) -> BaseSearchAlgorithm:
    if name == "ucs":
        return UniformCostSearch()
    if name == "astar":
        return AStarSearch(v_max=v_max)
    raise ValueError(f"unknown algorithm '{name}', expected one of: {', '.join(ALGORITHMS)}")


def run_task(graph: Graph, task: Task, algorithm: str, v_max: float = DEFAULT_V_MAX) -> TaskRun:
    """Validates one request and solves it. An invalid request is reported, not raised."""
    try:
        warnings = DataLoader.validate_task(graph, task)
    except InputValidationError as err:
        return TaskRun(task, algorithm, None, [], str(err))

    search = make_algorithm(algorithm, v_max)
    result = search.solve(graph, task.start, task.destination, task.required_visit, task.blocked_edges)
    if getattr(search, "last_warning", None):
        warnings.append(search.last_warning)
    return TaskRun(task, algorithm, result, warnings)


def edge_count(graph: Graph) -> int:
    return sum(len(edges) for edges in graph.adjacency.values())


def format_cost(cost: float) -> str:
    return f"{cost:g}"


def format_path(path: Sequence[str]) -> str:
    return " -> ".join(path)


def format_blocked(blocked: Sequence[Tuple[str, str]]) -> str:
    return ";".join(f"{u}>{v}" for u, v in blocked)


def write_runs_csv(path: str, runs: Sequence[TaskRun]) -> None:
    with open(path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for run in runs:
            result = run.result
            found = result is not None and result.success
            writer.writerow({
                "task_id": run.task.task_id,
                "start": run.task.start,
                "goal": run.task.destination,
                "blocked_edges": format_blocked(run.task.blocked_edges),
                "required_visit": run.task.required_visit or "",
                "algorithm": run.algorithm,
                "status": run.status,
                "solution_cost": format_cost(result.total_cost) if found else "",
                "path_sequence": format_path(result.path) if found else "",
                "expanded_states": result.expanded_states if result else "",
                "runtime_ms": f"{result.runtime_ms:.4f}" if result else "",
                "error": run.error or "",
            })
