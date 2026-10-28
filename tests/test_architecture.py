import pytest
from src.models.state import State
from src.models.graph import Graph, Node, Edge
from src.search.base import SearchResult

def test_state_hashing_and_equality():
    s1 = State("A", False)
    s2 = State("A", False)
    s3 = State("A", True)

    assert s1 == s2
    assert s1 != s3
    assert len({s1, s2, s3}) == 2

def test_negative_weight_rejection():
    with pytest.raises(ValueError, match="INVALID_EDGE_WEIGHT"):
        Edge(source="A", destination="B", weight=-5.0)

def test_graph_blocked_edges():
    g = Graph()
    g.add_edge(Edge("A", "B", 5.0))
    g.add_edge(Edge("A", "C", 10.0))

    assert len(g.get_neighbors("A")) == 2

    neighbors = g.get_neighbors("A", blocked_edges=[("A", "B")])
    assert len(neighbors) == 1
    assert neighbors[0].destination == "C"

def test_no_route_result_creation():
    res = SearchResult.no_route(expanded_states=15, runtime_ms=2.1)
    assert res.success is False
    assert res.status_message == "NO_FEASIBLE_ROUTE"