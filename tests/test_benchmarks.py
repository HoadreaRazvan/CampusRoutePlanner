import csv

from experiments.run_benchmarks import main
from tests.helpers import DATA


def test_benchmark_writes_results(tmp_path, capsys):
    code = main(["--repeats", "1", "--warmup", "0", "--out", str(tmp_path)])
    assert code == 0
    rows = list(csv.DictReader(open(tmp_path / "benchmark.csv", encoding="utf-8")))
    assert len(rows) == (7 + 6 + 9) * 3  # tasks x variants
    assert "## Summary per graph" in (tmp_path / "benchmark.md").read_text(encoding="utf-8")


def test_euclidean_heuristic_only_where_coordinates_exist(tmp_path, capsys):
    main(["--graphs", str(DATA / "graph1_brief_example"), str(DATA / "graph2_campus"),
          "--repeats", "1", "--warmup", "0", "--out", str(tmp_path)])
    rows = list(csv.DictReader(open(tmp_path / "benchmark.csv", encoding="utf-8")))
    euclidean = {r["graph"]: r["heuristic"] for r in rows if r["variant"] == "A* (Euclidean)"}
    assert euclidean == {"graph1_brief_example": "zero", "graph2_campus": "euclidean"}
