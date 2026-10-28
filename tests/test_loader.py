from pathlib import Path

import pytest
from src.io import DataLoader, InputValidationError
from src.models.task import Task

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name: str, with_nodes: bool = False):
    folder = DATA / name
    nodes = str(folder / "nodes.csv") if with_nodes else None
    return DataLoader.load_graph(str(folder / "edges.csv"), nodes)


def edge_count(graph) -> int:
    return sum(len(edges) for edges in graph.adjacency.values())


@pytest.mark.parametrize("name, with_nodes, nodes, edges", [
    ("graph1_brief_example", False, 5, 6),
    ("graph2_campus", True, 11, 34),
    ("graph3_traps", False, 12, 15),
])
def test_provided_graphs_load(name, with_nodes, nodes, edges):
    graph = load(name, with_nodes)
    assert len(graph.nodes) == nodes
    assert edge_count(graph) == edges


def test_zero_weight_edge_is_accepted():
    graph = load("graph3_traps")
    weights = {e.destination: e.weight for e in graph.adjacency["HallA"]}
    assert weights["HallB"] == 0


def test_coordinates_are_read():
    graph = load("graph2_campus", with_nodes=True)
    assert (graph.nodes["Workshop"].x, graph.nodes["Workshop"].y) == (1080, 250)


@pytest.mark.parametrize("name", ["graph1_brief_example", "graph2_campus", "graph3_traps"])
def test_provided_tasks_load_and_validate(name):
    graph = load(name)
    tasks = DataLoader.load_tasks(str(DATA / name / "tasks.csv"))
    assert tasks
    for task in tasks:
        assert DataLoader.validate_task(graph, task) == []


def test_task_fields_are_parsed():
    tasks = DataLoader.load_tasks(str(DATA / "graph1_brief_example" / "tasks.csv"))
    assert tasks[0] == Task("Task_1", "S", "G", None, [])
    assert tasks[1].blocked_edges == [("C", "G")]
    assert tasks[2].required_visit == "C"
    assert tasks[4].blocked_edges == [("A", "G"), ("B", "G"), ("C", "G")]


@pytest.mark.parametrize("text, expected", [
    ("", []),
    ("A>G", [("A", "G")]),
    (" A > G ; B>G; ", [("A", "G"), ("B", "G")]),
    ("[(A, G), (B, G)]", [("A", "G"), ("B", "G")]),
])
def test_parse_blocked_edges(text, expected):
    assert DataLoader.parse_blocked_edges(text) == expected


@pytest.mark.parametrize("text", ["A-G", "A>", ">G", "A>B>C", "(A G)"])
def test_parse_blocked_edges_rejects_bad_format(text):
    with pytest.raises(InputValidationError) as err:
        DataLoader.parse_blocked_edges(text)
    assert err.value.code == "MALFORMED_BLOCKED_EDGE"


@pytest.mark.parametrize("fixture, code, line", [
    ("negative_weight.csv", "INVALID_EDGE_WEIGHT", 3),
    ("missing_column.csv", "MISSING_COLUMN", None),
    ("non_numeric.csv", "NON_NUMERIC_WEIGHT", 3),
    ("empty.csv", "EMPTY_FILE", None),
    ("malformed_row.csv", "MALFORMED_ROW", 3),
    ("does_not_exist.csv", "FILE_NOT_FOUND", None),
])
def test_invalid_edges_files_are_rejected(fixture, code, line):
    with pytest.raises(InputValidationError) as err:
        DataLoader.load_graph(str(FIXTURES / fixture))
    assert err.value.code == code
    assert err.value.line == line


def test_invalid_coordinates_are_rejected():
    with pytest.raises(InputValidationError) as err:
        DataLoader.load_graph(str(DATA / "graph1_brief_example" / "edges.csv"), str(FIXTURES / "nodes_non_numeric.csv"))
    assert err.value.code == "NON_NUMERIC_COORDINATE"


def test_negative_weight_error_is_still_a_value_error():
    with pytest.raises(ValueError, match="INVALID_EDGE_WEIGHT"):
        DataLoader.load_graph(str(FIXTURES / "negative_weight.csv"))


def test_malformed_blocked_edge_in_tasks_file():
    with pytest.raises(InputValidationError) as err:
        DataLoader.load_tasks(str(FIXTURES / "tasks_bad_blocked.csv"))
    assert err.value.code == "MALFORMED_BLOCKED_EDGE"
    assert err.value.line == 2


def test_unknown_building_is_rejected():
    graph = load("graph1_brief_example")
    first, second = DataLoader.load_tasks(str(FIXTURES / "tasks_unknown_building.csv"))
    assert DataLoader.validate_task(graph, first) == []
    with pytest.raises(InputValidationError) as err:
        DataLoader.validate_task(graph, second)
    assert err.value.code == "UNKNOWN_BUILDING"
    assert "Library" in str(err.value)


def test_blocking_a_missing_edge_only_warns():
    graph = load("graph1_brief_example")
    warnings = DataLoader.validate_task(graph, Task("T", "S", "G", blocked_edges=[("G", "S")]))
    assert len(warnings) == 1
    assert "G>S" in warnings[0]
