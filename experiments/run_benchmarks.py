"""Compares UCS, A* with h = 0 and A* with the Euclidean heuristic on every task of the benchmark graphs.

Run from the repository root:
    python -m experiments.run_benchmarks                       # provided graphs, results in results/
    python -m experiments.run_benchmarks --graphs path/to/hidden_graph --repeats 20
"""
import argparse
import csv
import statistics
from pathlib import Path
from typing import Callable, Dict, List, Optional

from src.io import DataLoader
from src.planner import format_blocked, format_cost, format_path, load_dataset
from src.search import AStarSearch, UniformCostSearch
from src.search.base import BaseSearchAlgorithm
from src.search.heuristics import choose_heuristic, zero_heuristic

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GRAPHS = [ROOT / "data" / name for name in ("graph1_brief_example", "graph2_campus", "graph3_traps")]

VARIANTS: Dict[str, Callable[[], BaseSearchAlgorithm]] = {
    "UCS": UniformCostSearch,
    "A* (h=0)": lambda: AStarSearch(heuristic=zero_heuristic),
    "A* (Euclidean)": AStarSearch,
}

COLUMNS = [
    "graph", "task_id", "start", "goal", "blocked_edges", "required_visit", "variant", "heuristic", "status",
    "solution_cost", "expanded_states", "runtime_ms_median", "runtime_ms_min", "path_sequence",
]


def benchmark(graph_folders: List[Path], repeats: int, warmup: int) -> List[dict]:
    rows = []
    for folder in graph_folders:
        dataset = load_dataset(str(folder))
        graph = dataset.graph
        for task in dataset.tasks:
            DataLoader.validate_task(graph, task)
            _, warning = choose_heuristic(graph, task.destination)
            for variant, factory in VARIANTS.items():
                heuristic = "zero" if variant != "A* (Euclidean)" or warning else "euclidean"
                times = []
                for i in range(warmup + repeats):
                    result = factory().solve(
                        graph, task.start, task.destination, task.required_visit, task.blocked_edges
                    )
                    if i >= warmup:
                        times.append(result.runtime_ms)
                rows.append({
                    "graph": folder.name,
                    "task_id": task.task_id,
                    "start": task.start,
                    "goal": task.destination,
                    "blocked_edges": format_blocked(task.blocked_edges),
                    "required_visit": task.required_visit or "",
                    "variant": variant,
                    "heuristic": heuristic,
                    "status": result.status_message,
                    "solution_cost": format_cost(result.total_cost) if result.success else "",
                    "expanded_states": result.expanded_states,
                    "runtime_ms_median": round(statistics.median(times), 4),
                    "runtime_ms_min": round(min(times), 4),
                    "path_sequence": format_path(result.path),
                })
    return rows


def write_csv(path: Path, rows: List[dict]) -> None:
    with open(path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def to_markdown(rows: List[dict], repeats: int, warmup: int) -> str:
    variants = list(VARIANTS)
    lines = [
        "# Benchmark: UCS vs A*",
        "",
        f"Runtime is the median of {repeats} runs after {warmup} warm-up run(s), measured inside the search "
        "(loading and validation excluded). Timings depend on the machine; expanded states and costs do not.",
        "",
        "`A* (Euclidean)` falls back to h = 0 on graphs without coordinates, so there it equals `A* (h=0)`.",
        "",
        "## Summary per graph",
        "",
        "| Graph | Tasks | Variant | Routes found | Total expanded states | Total median runtime (ms) |",
        "|---|---|---|---|---|---|",
    ]
    graphs = list(dict.fromkeys(r["graph"] for r in rows))
    for graph in graphs:
        graph_rows = [r for r in rows if r["graph"] == graph]
        task_count = len({r["task_id"] for r in graph_rows})
        for variant in variants:
            vr = [r for r in graph_rows if r["variant"] == variant]
            found = sum(1 for r in vr if r["status"] == "SUCCESS")
            expanded = sum(r["expanded_states"] for r in vr)
            runtime = sum(r["runtime_ms_median"] for r in vr)
            lines.append(f"| {graph} | {task_count} | {variant} | {found} | {expanded} | {runtime:.4f} |")

    for graph in graphs:
        graph_rows = [r for r in rows if r["graph"] == graph]
        lines += [
            "",
            f"## {graph}",
            "",
            "| Task | Request | Cost | " + " | ".join(f"{v} expanded" for v in variants) + " | "
            + " | ".join(f"{v} ms" for v in variants) + " |",
            "|---|---|---|" + "---|" * (2 * len(variants)),
        ]
        for task_id in dict.fromkeys(r["task_id"] for r in graph_rows):
            by_variant = {r["variant"]: r for r in graph_rows if r["task_id"] == task_id}
            first = by_variant[variants[0]]
            request = f"{first['start']} → {first['goal']}"
            if first["blocked_edges"]:
                request += f", blocked {first['blocked_edges']}"
            if first["required_visit"]:
                request += f", via {first['required_visit']}"
            cost = first["solution_cost"] or "no route"
            expanded = " | ".join(str(by_variant[v]["expanded_states"]) for v in variants)
            runtime = " | ".join(f"{by_variant[v]['runtime_ms_median']:.4f}" for v in variants)
            lines.append(f"| {task_id} | {request} | {cost} | {expanded} | {runtime} |")
    return "\n".join(lines) + "\n"


def check_costs_agree(rows: List[dict]) -> List[str]:
    """All variants must return the same cost for the same task (AC-04)."""
    problems = []
    for key in dict.fromkeys((r["graph"], r["task_id"]) for r in rows):
        costs = {r["variant"]: r["solution_cost"] for r in rows if (r["graph"], r["task_id"]) == key}
        if len(set(costs.values())) > 1:
            problems.append(f"{key[0]} {key[1]}: costs differ {costs}")
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m experiments.run_benchmarks", description=__doc__.splitlines()[0])
    parser.add_argument("--graphs", nargs="+", type=Path, default=DEFAULT_GRAPHS, help="graph folders")
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--out", type=Path, default=ROOT / "results", help="output folder (default: results/)")
    args = parser.parse_args(argv)

    rows = benchmark(args.graphs, max(1, args.repeats), max(0, args.warmup))
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "benchmark.csv", rows)
    (args.out / "benchmark.md").write_text(to_markdown(rows, args.repeats, args.warmup), encoding="utf-8")
    print(f"{len(rows)} rows written to {args.out / 'benchmark.csv'} and {args.out / 'benchmark.md'}")

    problems = check_costs_agree(rows)
    for problem in problems:
        print(f"error: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
