import pytest
from src.search import AStarSearch, UniformCostSearch
from tests.helpers import DATA, assert_no_route, assert_valid_route, load_folder, run

# Expected optimal cost per task in data/custom/<map>/tasks.csv, in file order. None = NO_FEASIBLE_ROUTE.
EXPECTED_COSTS = {
    "zero_cost_cycle": [2, 5, None, 0],
    "parallel_edges": [3, 2, 4],
    "waypoint_round_trip": [6, 8, 4, 4, None],
    "blocked_bridge": [6, None, None, None, 6, None],
}

CASES = [(name, index, cost) for name, costs in EXPECTED_COSTS.items() for index, cost in enumerate(costs)]


@pytest.mark.parametrize("algorithm", [UniformCostSearch, AStarSearch])
@pytest.mark.parametrize("name, index, cost", CASES)
def test_custom_maps(algorithm, name, index, cost):
    graph, tasks = load_folder(DATA / "custom" / name)
    result = run(algorithm(), graph, tasks[index])
    if cost is None:
        assert_no_route(result)
    else:
        assert_valid_route(graph, tasks[index], result)
        assert result.total_cost == cost


def test_required_stop_inside_zero_cost_cycle():
    graph, tasks = load_folder(DATA / "custom" / "zero_cost_cycle")
    assert run(UniformCostSearch(), graph, tasks[3]).path == ["A", "B", "C", "A"]


def test_cheaper_parallel_edge_is_used():
    graph, tasks = load_folder(DATA / "custom" / "parallel_edges")
    assert run(UniformCostSearch(), graph, tasks[0]).path == ["A", "B", "C"]


def test_round_trip_to_dead_end_stop():
    graph, tasks = load_folder(DATA / "custom" / "waypoint_round_trip")
    assert run(UniformCostSearch(), graph, tasks[0]).path == ["Home", "Hub", "Store", "Hub", "Home"]
    assert run(UniformCostSearch(), graph, tasks[1]).path == ["Home", "Hub", "Store", "Hub", "Office"]
