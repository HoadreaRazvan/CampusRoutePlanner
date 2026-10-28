import json
import threading
import urllib.error
import urllib.request

import pytest
from src.gui import api
from src.gui.server import create_server
from src.io import InputValidationError
from tests.helpers import DATA

EDGES = "from,to,minutes\nA,B,1\nB,C,2\n"


@pytest.fixture
def registry():
    return api.Registry()


def test_lists_provided_maps_first(registry):
    ids = [d["id"] for d in api.list_datasets(registry)]
    assert ids[:3] == ["graph1_brief_example", "graph2_campus", "graph3_traps"]
    assert "custom/zero_cost_cycle" in ids


def test_graph_payload(registry):
    graph = api.graph_payload(registry, "graph2_campus")
    assert graph["coordinates"] is True
    assert (len(graph["nodes"]), len(graph["edges"]), len(graph["tasks"])) == (11, 34, 6)
    assert graph["speed_check"]["edge"] in ("Gate>Rectorate", "Rectorate>Gate")
    assert graph["speed_check"]["speed"] == pytest.approx(79.41, abs=0.01)
    assert graph["too_fast"] == []


def test_solve_returns_both_runs_with_traces(registry):
    data = api.solve_payload(registry, "graph2_campus", "Gate", "Workshop", "Canteen")
    ucs, astar = data["runs"]
    assert (ucs["cost"], astar["cost"]) == (19, 19)
    assert (ucs["expanded"], astar["expanded"]) == (18, 14)
    for run in (ucs, astar):
        assert len(run["trace"]) == run["expanded"]
        assert run["trace"][0] == {"node": "Gate", "done": False, "g": 0, "f": run["trace"][0]["f"]}
        assert run["trace"][-1]["node"] == "Workshop" and run["trace"][-1]["done"] is True
    assert astar["heuristic"] == "euclidean"
    assert astar["h"]["Workshop"] == 0


def test_unsafe_speed_limit_falls_back_to_ucs(registry):
    data = api.solve_payload(registry, "graph2_campus", "Workshop", "SportsHall", v_max=70)
    ucs, astar = data["runs"]
    assert astar["heuristic"] == "zero"
    assert "faster than 70" in astar["heuristic_note"]
    assert astar["trace"] == ucs["trace"]


def test_no_route_and_blocked_edges(registry):
    data = api.solve_payload(registry, "graph1_brief_example", "S", "G", blocked=[["A", "G"], ["B", "G"], ["C", "G"]])
    assert [r["status"] for r in data["runs"]] == ["NO_FEASIBLE_ROUTE"] * 2


def test_unknown_building_is_rejected(registry):
    with pytest.raises(InputValidationError) as err:
        api.solve_payload(registry, "graph1_brief_example", "S", "Library")
    assert err.value.code == "UNKNOWN_BUILDING"


def test_unknown_dataset(registry):
    with pytest.raises(InputValidationError) as err:
        api.graph_payload(registry, "nope")
    assert err.value.code == "UNKNOWN_DATASET"


def test_open_folder(registry):
    dataset_id = registry.add_folder(str(DATA / "graph3_traps"))
    assert dataset_id == "opened/graph3_traps"
    assert api.graph_payload(registry, dataset_id)["coordinates"] is False
    with pytest.raises(InputValidationError):
        registry.add_folder(str(DATA))  # no edges.csv directly inside


def test_upload(registry):
    dataset_id = registry.add_upload("hidden graph", {"edges.csv": EDGES, "tasks.csv": "start,goal,blocked_edges,required_visit\nA,C,,\n"})
    assert dataset_id == "dropped/hidden graph"
    run = api.solve_payload(registry, dataset_id, "A", "C")["runs"][0]
    assert (run["cost"], run["path"]) == (3, ["A", "B", "C"])

    with pytest.raises(InputValidationError):
        registry.add_upload("no edges", {"tasks.csv": "start,goal\n"})
    with pytest.raises(InputValidationError) as err:
        registry.add_upload("bad", {"edges.csv": "from,to,minutes\nA,B,-1\n"})
    assert err.value.code == "INVALID_EDGE_WEIGHT"


def test_zero_time_edge_has_no_safe_speed(registry):
    nodes = "id,x,y\nA,0,0\nB,100,0\nC,200,0\n"
    edges = "from,to,minutes\nA,B,0\nB,C,2\n"
    dataset_id = registry.add_upload("zero", {"edges.csv": edges, "nodes.csv": nodes})
    assert api.graph_payload(registry, dataset_id)["speed_check"] == {"speed": None, "edge": "A>B"}


@pytest.fixture
def server():
    srv = create_server(0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def fetch(url, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def test_server_end_to_end(server):
    status, body = fetch(server + "/")
    assert status == 200 and b"Campus Route Planner" in body

    status, body = fetch(server + "/api/datasets")
    assert status == 200 and json.loads(body)["datasets"]

    status, body = fetch(server + "/api/solve", {"id": "graph1_brief_example", "start": "S", "goal": "G", "required": "B"})
    assert status == 200
    assert json.loads(body)["runs"][0]["path"] == ["S", "B", "G"]

    status, body = fetch(server + "/api/solve", {"id": "graph1_brief_example", "start": "S", "goal": "X"})
    assert status == 400 and json.loads(body)["code"] == "UNKNOWN_BUILDING"


def test_server_does_not_serve_files_outside_static(server):
    status, _ = fetch(server + "/../server.py")
    assert status == 404
    status, _ = fetch(server + "/%2e%2e/api.py")
    assert status == 404
