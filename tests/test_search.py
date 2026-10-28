import pytest
from src.search import AStarSearch, UniformCostSearch
from src.search.heuristics import zero_heuristic
from tests.helpers import DATA, assert_no_route, assert_valid_route, load_folder, run

# Optimal cost of every task in tasks.csv, in file order. None = NO_FEASIBLE_ROUTE.
EXPECTED_COSTS = {
    "graph1_brief_example": [7, 7, 7, 7, None, None, 4],
    "graph2_campus": [17, 18, 19, 14, 16, 19],
    "graph3_traps": [7, 9, None, None, None, 12, 10, 0, 7],
}

CASES = [(name, index, cost) for name, costs in EXPECTED_COSTS.items() for index, cost in enumerate(costs)]
ALGORITHMS = {"ucs": UniformCostSearch, "astar": AStarSearch}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("name, index, cost", CASES)
def test_optimal_cost_on_provided_graphs(algorithm, name, index, cost):
    graph, tasks = load_folder(DATA / name)
    result = run(ALGORITHMS[algorithm](), graph, tasks[index])
    if cost is None:
        assert_no_route(result)
    else:
        assert_valid_route(graph, tasks[index], result)
        assert result.total_cost == cost


@pytest.mark.parametrize("name", EXPECTED_COSTS)
def test_astar_with_zero_heuristic_is_ucs(name):
    graph, tasks = load_folder(DATA / name)
    for task in tasks:
        ucs = run(UniformCostSearch(), graph, task)
        astar = run(AStarSearch(heuristic=zero_heuristic), graph, task)
        assert (astar.path, astar.total_cost, astar.expanded_states) == (ucs.path, ucs.total_cost, ucs.expanded_states)


def test_astar_expands_fewer_states_on_campus():
    graph, tasks = load_folder(DATA / "graph2_campus")
    ucs = [run(UniformCostSearch(), graph, t).expanded_states for t in tasks]
    astar = [run(AStarSearch(), graph, t).expanded_states for t in tasks]
    assert all(a <= u for a, u in zip(astar, ucs))
    assert sum(astar) < sum(ucs)


def test_expanded_states_match_reference_table():
    # Reference values from the plan, valid for tie-breaking (f, g, insertion order) and
    # "expanded" = popped and not already closed.
    graph, tasks = load_folder(DATA / "graph2_campus")
    assert [run(UniformCostSearch(), graph, t).expanded_states for t in tasks] == [11, 11, 18, 9, 9, 19]
    assert [run(AStarSearch(), graph, t).expanded_states for t in tasks] == [9, 11, 14, 7, 5, 13]


def test_route_can_revisit_a_building():
    graph, tasks = load_folder(DATA / "graph3_traps")
    result = run(UniformCostSearch(), graph, tasks[5])  # Entrance -> Lab via Kitchen
    assert result.path[-4:] == ["Lab", "Kitchen", "Lounge", "Lab"]


def test_start_equals_goal():
    graph, tasks = load_folder(DATA / "graph3_traps")
    result = run(UniformCostSearch(), graph, tasks[7])
    assert (result.path, result.total_cost, result.expanded_states) == (["Entrance"], 0, 1)


def test_required_visit_on_start_is_already_done():
    graph, tasks = load_folder(DATA / "graph3_traps")
    result = run(UniformCostSearch(), graph, tasks[8])  # HallA -> Roof, required HallA
    assert result.path == ["HallA", "HallB", "Stairs", "Office", "Roof"]


def test_blocked_edge_changes_route():
    graph, tasks = load_folder(DATA / "graph1_brief_example")
    result = run(UniformCostSearch(), graph, tasks[1])  # S -> G with C>G closed
    assert result.path == ["S", "B", "G"]


def test_results_are_deterministic():
    graph, tasks = load_folder(DATA / "graph3_traps")
    first = [run(UniformCostSearch(), graph, t).path for t in tasks]
    second = [run(UniformCostSearch(), graph, t).path for t in tasks]
    assert first == second


def test_telemetry_is_filled():
    graph, tasks = load_folder(DATA / "graph2_campus")
    result = run(AStarSearch(), graph, tasks[0])
    assert result.expanded_states > 0
    assert result.runtime_ms >= 0
    assert result.status_message == "SUCCESS"
