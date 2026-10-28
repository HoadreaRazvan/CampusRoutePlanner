import math

import pytest
from src.models.graph import Edge, Graph, Node
from src.search import AStarSearch, UniformCostSearch
from src.search.heuristics import check_consistency, choose_heuristic, euclidean_heuristic, zero_heuristic
from tests.helpers import DATA, load_folder


def test_campus_edges_respect_speed_limit():
    graph, _ = load_folder(DATA / "graph2_campus")
    assert check_consistency(graph, 80.0) == []


def test_euclidean_heuristic_is_admissible_on_campus():
    # h(n) <= true cheapest cost from n to the goal, for every pair of buildings.
    graph, _ = load_folder(DATA / "graph2_campus")
    for goal in graph.nodes:
        h = euclidean_heuristic(graph, goal)
        assert h(goal) == 0
        for node in graph.nodes:
            true_cost = UniformCostSearch().solve(graph, node, goal).total_cost
            assert h(node) <= true_cost + 1e-9


def test_campus_uses_euclidean_heuristic():
    graph, _ = load_folder(DATA / "graph2_campus")
    heuristic, warning = choose_heuristic(graph, "Workshop")
    assert warning is None
    # Gate (0, 300) -> Workshop (1080, 250)
    assert heuristic("Gate") == pytest.approx(math.hypot(1080, 50) / 80)


def test_no_coordinates_falls_back_to_zero():
    graph, tasks = load_folder(DATA / "graph1_brief_example")
    heuristic, warning = choose_heuristic(graph, "G")
    assert heuristic is zero_heuristic
    assert "coordinates" in warning

    astar = AStarSearch()
    result = astar.solve(graph, "S", "G")
    assert astar.last_warning is not None
    assert result.expanded_states == UniformCostSearch().solve(graph, "S", "G").expanded_states


def test_edge_faster_than_speed_limit_falls_back_to_zero():
    graph = Graph()
    graph.add_node(Node("A", 0, 0))
    graph.add_node(Node("B", 800, 0))
    graph.add_edge(Edge("A", "B", 5))  # 800 m in 5 minutes = 160 m/min
    assert [(e.source, e.destination) for e in check_consistency(graph, 80.0)] == [("A", "B")]

    heuristic, warning = choose_heuristic(graph, "B")
    assert heuristic is zero_heuristic
    assert "A>B" in warning


def test_v_max_must_be_positive():
    graph, _ = load_folder(DATA / "graph2_campus")
    with pytest.raises(ValueError):
        euclidean_heuristic(graph, "Gate", v_max=0)
