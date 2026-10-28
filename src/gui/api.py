"""JSON API behind the web GUI. Pure functions over a dataset registry, so they can be tested without a server."""
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.io import DataLoader, InputValidationError
from src.models.task import Task
from src.planner import ALGORITHM_LABELS, Dataset, edge_count, load_dataset
from src.search import AStarSearch, UniformCostSearch
from src.search.best_first import best_first_search
from src.search.heuristics import DEFAULT_V_MAX, check_consistency, choose_heuristic, has_coordinates, zero_heuristic

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"
UPLOAD_NAMES = ("edges.csv", "nodes.csv", "tasks.csv")


class Registry:
    """Datasets the GUI can show: the folders under data/ plus folders opened or files dropped at runtime."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.external: Dict[str, Tuple[Path, str]] = {}

    def folders(self) -> Dict[str, Tuple[Path, str]]:
        found: Dict[str, Tuple[Path, str]] = {}
        if self.data_dir.is_dir():
            for edges in self.data_dir.rglob("edges.csv"):
                folder = edges.parent
                rel = folder.relative_to(self.data_dir).as_posix()
                found[rel] = (folder, "Custom" if rel.startswith("custom/") else "Provided")
        ordered = dict(sorted(found.items(), key=lambda item: (item[1][1] != "Provided", item[0])))
        ordered.update(self.external)
        return ordered

    def path_of(self, dataset_id: str) -> Path:
        folders = self.folders()
        if dataset_id not in folders:
            raise InputValidationError("UNKNOWN_DATASET", f"no dataset called '{dataset_id}'")
        return folders[dataset_id][0]

    def add_folder(self, path: str) -> str:
        folder = Path(path).expanduser()
        if folder.is_file():
            folder = folder.parent
        if not (folder / "edges.csv").is_file():
            raise InputValidationError("FILE_NOT_FOUND", "the folder has no edges.csv", str(folder))
        load_dataset(str(folder))  # reject invalid data now, with the loader's message
        dataset_id = f"opened/{folder.name}"
        suffix = 2
        while dataset_id in self.external and self.external[dataset_id][0] != folder:
            dataset_id, suffix = f"opened/{folder.name}-{suffix}", suffix + 1
        self.external[dataset_id] = (folder, "Opened")
        return dataset_id

    def add_upload(self, name: str, files: Dict[str, str]) -> str:
        files = {k.lower(): v for k, v in files.items() if k.lower() in UPLOAD_NAMES and v is not None}
        if "edges.csv" not in files:
            raise InputValidationError("FILE_NOT_FOUND", "drop at least an edges file (edges.csv)")
        folder = Path(tempfile.mkdtemp(prefix="campus-route-"))
        for file_name, text in files.items():
            (folder / file_name).write_text(text, encoding="utf-8")
        load_dataset(str(folder))
        clean = "".join(c for c in name if c.isalnum() or c in "-_ ").strip() or "dropped"
        dataset_id = f"dropped/{clean}"
        suffix = 2
        while dataset_id in self.external:
            dataset_id, suffix = f"dropped/{clean}-{suffix}", suffix + 1
        self.external[dataset_id] = (folder, "Dropped")
        return dataset_id


def list_datasets(registry: Registry) -> List[dict]:
    items = []
    for dataset_id, (folder, group) in registry.folders().items():
        try:
            dataset = load_dataset(str(folder))
            items.append({
                "id": dataset_id, "name": folder.name if group != "Custom" else dataset_id.split("/", 1)[1],
                "group": group, "buildings": len(dataset.graph.nodes), "edges": edge_count(dataset.graph),
                "tasks": len(dataset.tasks), "coordinates": has_coordinates(dataset.graph), "error": None,
            })
        except InputValidationError as err:
            items.append({"id": dataset_id, "name": folder.name, "group": group, "error": str(err)})
    return items


def graph_payload(registry: Registry, dataset_id: str, v_max: float = DEFAULT_V_MAX) -> dict:
    dataset = load_dataset(str(registry.path_of(dataset_id)))
    graph = dataset.graph
    coordinates = has_coordinates(graph)
    too_fast = check_consistency(graph, v_max) if coordinates else []
    return {
        "id": dataset_id,
        "name": registry.path_of(dataset_id).name,
        "coordinates": coordinates,
        "nodes": [{"id": n.id, "x": n.x, "y": n.y} for n in graph.nodes.values()],
        "edges": [
            {"source": e.source, "target": e.destination, "weight": e.weight}
            for edges in graph.adjacency.values() for e in edges
        ],
        "tasks": [task_payload(t) for t in dataset.tasks],
        "speed_check": speed_check(dataset) if coordinates else None,
        "too_fast": [f"{e.source}>{e.destination}" for e in too_fast],
    }


def speed_check(dataset: Dataset) -> dict:
    """The fastest edge in the data: the heuristic is safe for any v_max at or above this speed.

    A zero-time edge between two different points has no finite speed; then no v_max is safe ("speed": None).
    """
    graph = dataset.graph
    best: Optional[Tuple[float, str]] = None
    for edges in graph.adjacency.values():
        for e in edges:
            a, b = graph.nodes[e.source], graph.nodes[e.destination]
            distance = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5
            if distance == 0:
                continue
            speed = distance / e.weight if e.weight > 0 else float("inf")
            if best is None or speed > best[0]:
                best = (speed, f"{e.source}>{e.destination}")
    if best is None:
        return {"speed": 0, "edge": None}
    return {"speed": None if best[0] == float("inf") else round(best[0], 2), "edge": best[1]}


def task_payload(task: Task) -> dict:
    return {
        "id": task.task_id, "start": task.start, "goal": task.destination,
        "required": task.required_visit, "blocked": [list(pair) for pair in task.blocked_edges],
    }


def solve_payload(
    registry: Registry,
    dataset_id: str,
    start: str,
    goal: str,
    required: Optional[str] = None,
    blocked: Optional[List[List[str]]] = None,
    v_max: float = DEFAULT_V_MAX,
) -> dict:
    if v_max <= 0:
        raise InputValidationError("INVALID_VMAX", "v_max must be positive")
    graph = load_dataset(str(registry.path_of(dataset_id))).graph
    blocked_pairs = [(str(u), str(v)) for u, v in (blocked or [])]
    task = Task("GUI", start, goal, required or None, blocked_pairs)
    warnings = DataLoader.validate_task(graph, task)

    runs = []
    for name in ("ucs", "astar"):
        if name == "ucs":
            search, heuristic, heuristic_note = UniformCostSearch(), zero_heuristic, None
        else:
            search = AStarSearch(v_max=v_max)
            heuristic, heuristic_note = choose_heuristic(graph, goal, v_max)
        result = search.solve(graph, start, goal, task.required_visit, blocked_pairs)

        trace: List[Tuple[str, bool, float, float]] = []
        best_first_search(graph, start, goal, heuristic, task.required_visit, blocked_pairs, trace)
        runs.append({
            "algorithm": name,
            "label": ALGORITHM_LABELS[name],
            "status": result.status_message,
            "cost": result.total_cost if result.success else None,
            "path": result.path,
            "expanded": result.expanded_states,
            "runtime_ms": round(result.runtime_ms, 4),
            "heuristic": "zero" if heuristic is zero_heuristic else "euclidean",
            "heuristic_note": heuristic_note,
            "h": {n: round(heuristic(n), 3) for n in graph.nodes} if name == "astar" else None,
            "trace": [{"node": n, "done": d, "g": g, "f": round(f, 3)} for n, d, g, f in trace],
        })
    return {
        "request": task_payload(task),
        "warnings": warnings,
        "runs": runs,
    }
