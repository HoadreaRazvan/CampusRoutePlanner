import csv

import pytest
from src.cli import main
from tests.helpers import DATA
from tests.test_loader import FIXTURES


def run_cli(capsys, *args):
    code = main([str(a) for a in args])
    out, err = capsys.readouterr()
    return code, out, err


def test_runs_every_task_of_a_folder(capsys):
    code, out, err = run_cli(capsys, DATA / "graph1_brief_example")
    assert code == 0
    assert out.count("Task_") == 7
    assert "solution_cost=7" in out
    assert "path_sequence: S -> B -> G" in out
    assert "NO_FEASIBLE_ROUTE" in out
    assert "expanded_states=" in out and "runtime_ms=" in out
    assert "coordinates" in err  # A* explains that it falls back to h = 0


def test_accepts_the_edges_file_directly(capsys):
    code, out, _ = run_cli(capsys, DATA / "graph2_campus" / "edges.csv", "--algorithm", "astar")
    assert code == 0
    assert "coordinates: yes" in out
    assert "UCS" not in out
    assert "solution_cost=17" in out


def test_single_request(capsys):
    code, out, _ = run_cli(capsys, DATA / "graph1_brief_example", "--start", "S", "--goal", "G", "--blocked", "C>G")
    assert code == 0
    assert out.count("path_sequence: S -> B -> G") == 2


def test_single_request_with_required_stop(capsys):
    code, out, _ = run_cli(capsys, DATA / "graph3_traps", "--start", "Entrance", "--goal", "Lab",
                           "--required", "Kitchen", "--algorithm", "ucs")
    assert code == 0
    assert "solution_cost=12" in out
    assert "Lab -> Kitchen -> Lounge -> Lab" in out


def test_no_route_is_not_an_error(capsys):
    code, out, _ = run_cli(capsys, DATA / "graph3_traps", "--start", "Entrance", "--goal", "Observatory")
    assert code == 0
    assert "NO_FEASIBLE_ROUTE" in out


def test_unknown_building_is_reported(capsys):
    code, out, _ = run_cli(capsys, DATA / "graph1_brief_example", "--start", "S", "--goal", "Library")
    assert code == 1
    assert "INVALID_REQUEST" in out
    assert "UNKNOWN_BUILDING" in out


def test_invalid_graph_file_gives_clear_error(capsys):
    code, out, err = run_cli(capsys, FIXTURES / "negative_weight.csv")
    assert code == 2
    assert "INVALID_EDGE_WEIGHT" in err
    assert "Traceback" not in err


def test_missing_folder(capsys):
    code, _, err = run_cli(capsys, DATA / "does_not_exist")
    assert code == 2
    assert "FILE_NOT_FOUND" in err


def test_bad_blocked_argument(capsys):
    code, _, err = run_cli(capsys, DATA / "graph1_brief_example", "--start", "S", "--goal", "G", "--blocked", "C-G")
    assert code == 2
    assert "MALFORMED_BLOCKED_EDGE" in err


def test_writes_csv(capsys, tmp_path):
    out_file = tmp_path / "results.csv"
    code, _, _ = run_cli(capsys, DATA / "graph2_campus", "--csv", out_file)
    assert code == 0
    rows = list(csv.DictReader(open(out_file, encoding="utf-8")))
    assert len(rows) == 12  # 6 tasks x 2 algorithms
    assert rows[0]["solution_cost"] == "17"
    assert rows[0]["path_sequence"] == "Gate -> Library -> AILab -> PrintShop -> Workshop"


@pytest.mark.parametrize("args", [["--start", "S"], ["--vmax", "0"]])
def test_bad_arguments_exit(capsys, args):
    with pytest.raises(SystemExit) as err:
        main([str(DATA / "graph1_brief_example"), *args])
    assert err.value.code == 2
