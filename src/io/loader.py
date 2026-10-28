import csv
import math
import re
from typing import Dict, Iterator, List, Optional, Sequence, Tuple
from src.io.errors import InputValidationError
from src.models.graph import Graph, Node, Edge
from src.models.task import Task

# Accepted header names: the official format first, then the aliases from the specification.
EDGE_COLUMNS = {
    "source": ("from", "source"),
    "destination": ("to", "destination"),
    "weight": ("minutes", "travel_time", "weight"),
}
NODE_COLUMNS = {
    "id": ("id", "node_id"),
    "x": ("x",),
    "y": ("y",),
}
TASK_COLUMNS = {
    "start": ("start",),
    "destination": ("goal", "destination"),
}
OPTIONAL_TASK_COLUMNS = {
    "blocked_edges": ("blocked_edges",),
    "required_visit": ("required_visit",),
}

EMPTY_VALUES = {"", "none"}
TUPLE_PATTERN = re.compile(r"\(\s*([^(),]+?)\s*,\s*([^(),]+?)\s*\)")


class DataLoader:
    @staticmethod
    def load_graph(edges_path: str, nodes_path: Optional[str] = None) -> Graph:
        graph = Graph()

        if nodes_path:
            for line, row in DataLoader._read_rows(nodes_path, NODE_COLUMNS):
                node_id = DataLoader._required_value(row, "id", nodes_path, line)
                x = DataLoader._parse_number(row["x"], "NON_NUMERIC_COORDINATE", "x", nodes_path, line)
                y = DataLoader._parse_number(row["y"], "NON_NUMERIC_COORDINATE", "y", nodes_path, line)
                graph.add_node(Node(id=node_id, x=x, y=y))

        for line, row in DataLoader._read_rows(edges_path, EDGE_COLUMNS):
            src = DataLoader._required_value(row, "source", edges_path, line)
            dst = DataLoader._required_value(row, "destination", edges_path, line)
            weight = DataLoader._parse_number(row["weight"], "NON_NUMERIC_WEIGHT", "travel time", edges_path, line)
            if weight < 0:
                raise InputValidationError(
                    "INVALID_EDGE_WEIGHT", f"edge {src}->{dst} has negative travel time {weight}", edges_path, line
                )

            if src not in graph.nodes:
                graph.add_node(Node(id=src))
            if dst not in graph.nodes:
                graph.add_node(Node(id=dst))

            graph.add_edge(Edge(source=src, destination=dst, weight=weight))

        return graph

    @staticmethod
    def load_tasks(tasks_path: str) -> List[Task]:
        tasks = []
        columns = {**TASK_COLUMNS, **OPTIONAL_TASK_COLUMNS}
        for idx, (line, row) in enumerate(DataLoader._read_rows(tasks_path, columns, optional=OPTIONAL_TASK_COLUMNS)):
            req = row.get("required_visit") or ""
            tasks.append(Task(
                task_id=f"Task_{idx+1}",
                start=DataLoader._required_value(row, "start", tasks_path, line),
                destination=DataLoader._required_value(row, "destination", tasks_path, line),
                required_visit=None if req.lower() in EMPTY_VALUES else req,
                blocked_edges=DataLoader.parse_blocked_edges(row.get("blocked_edges") or "", tasks_path, line),
            ))
        return tasks

    @staticmethod
    def parse_blocked_edges(text: str, path: Optional[str] = None, line: Optional[int] = None) -> List[Tuple[str, str]]:
        """Parses 'A>B;C>D' (official format) or '[(A, B), (C, D)]' (format from the specification)."""
        text = text.strip()
        if text.lower() in EMPTY_VALUES:
            return []

        if "(" in text:
            pairs = TUPLE_PATTERN.findall(text)
            leftover = TUPLE_PATTERN.sub("", text).strip("[]; ,")
            if not pairs or leftover:
                raise InputValidationError(
                    "MALFORMED_BLOCKED_EDGE", f"cannot read blocked edges '{text}', expected A>B;C>D", path, line
                )
            return pairs

        blocked = []
        for piece in text.split(";"):
            piece = piece.strip()
            if not piece:
                continue
            parts = [p.strip() for p in piece.split(">")]
            if len(parts) != 2 or not all(parts):
                raise InputValidationError(
                    "MALFORMED_BLOCKED_EDGE", f"cannot read blocked edge '{piece}', expected FROM>TO", path, line
                )
            blocked.append((parts[0], parts[1]))
        return blocked

    @staticmethod
    def validate_task(graph: Graph, task: Task) -> List[str]:
        """Rejects tasks that name unknown buildings. Returns warnings for blocked edges that do not exist."""
        named = [("start", task.start), ("goal", task.destination)]
        if task.required_visit is not None:
            named.append(("required_visit", task.required_visit))
        for u, v in task.blocked_edges:
            named += [("blocked edge", u), ("blocked edge", v)]

        for role, node_id in named:
            if node_id not in graph.nodes:
                raise InputValidationError("UNKNOWN_BUILDING", f"{task.task_id}: {role} '{node_id}' is not in the graph")

        warnings = []
        for u, v in task.blocked_edges:
            if not any(edge.destination == v for edge in graph.adjacency.get(u, [])):
                warnings.append(f"{task.task_id}: blocked edge {u}>{v} does not exist in the graph and is ignored")
        return warnings

    @staticmethod
    def _read_rows(
        path: str, columns: Dict[str, Sequence[str]], optional: Optional[Dict[str, Sequence[str]]] = None
    ) -> Iterator[Tuple[int, Dict[str, str]]]:
        """Yields (line number, row) with keys renamed to the canonical column names."""
        optional = optional or {}
        try:
            f = open(path, mode="r", encoding="utf-8-sig", newline="")
        except FileNotFoundError:
            raise InputValidationError("FILE_NOT_FOUND", "file does not exist", path) from None

        with f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None or not any(h.strip() for h in header):
                raise InputValidationError("EMPTY_FILE", "file is empty or has no header", path)
            header = [h.strip().lower() for h in header]

            positions = {}
            for name, aliases in columns.items():
                found = next((header.index(a) for a in aliases if a in header), None)
                if found is not None:
                    positions[name] = found
                elif name not in optional:
                    raise InputValidationError(
                        "MISSING_COLUMN", f"missing column '{aliases[0]}' (found: {', '.join(header)})", path
                    )

            for values in reader:
                if not any(v.strip() for v in values):
                    continue
                if len(values) != len(header):
                    raise InputValidationError(
                        "MALFORMED_ROW", f"expected {len(header)} values, found {len(values)}", path, reader.line_num
                    )
                yield reader.line_num, {name: values[pos].strip() for name, pos in positions.items()}

    @staticmethod
    def _required_value(row: Dict[str, str], name: str, path: str, line: int) -> str:
        if not row[name]:
            raise InputValidationError("MISSING_VALUE", f"empty value in column '{name}'", path, line)
        return row[name]

    @staticmethod
    def _parse_number(text: str, code: str, what: str, path: str, line: int) -> float:
        try:
            value = float(text)
        except ValueError:
            raise InputValidationError(code, f"{what} '{text}' is not a number", path, line) from None
        if not math.isfinite(value):
            raise InputValidationError(code, f"{what} '{text}' is not a finite number", path, line)
        return value
