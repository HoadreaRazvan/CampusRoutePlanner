import argparse
import sys
from typing import List, Optional

from src.io import DataLoader, InputValidationError
from src.models.task import Task
from src.planner import (
    ALGORITHM_LABELS, ALGORITHMS, TaskRun, edge_count, format_blocked, format_cost, format_path,
    load_dataset, run_task, write_runs_csv,
)
from src.search.heuristics import DEFAULT_V_MAX, has_coordinates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="Campus Route and Constraint Planner: minimal-time routes with closed edges and a required stop.",
    )
    parser.add_argument("graph", help="folder with edges.csv (+ optional nodes.csv, tasks.csv), or the path to an edges file")
    parser.add_argument("--tasks", help="tasks file (default: tasks.csv next to the graph)")
    parser.add_argument("--algorithm", choices=[*ALGORITHMS, "both"], default="both", help="default: both")
    parser.add_argument("--vmax", type=float, default=DEFAULT_V_MAX,
                        help=f"fastest walking speed in metres/minute, used by the A* heuristic (default: {DEFAULT_V_MAX:g})")
    parser.add_argument("--start", help="run a single request instead of the tasks file")
    parser.add_argument("--goal", help="goal of the single request")
    parser.add_argument("--required", help="required stop of the single request")
    parser.add_argument("--blocked", help='closed edges of the single request, e.g. "A>B;C>D"')
    parser.add_argument("--csv", help="also write the results to this CSV file")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if (args.start is None) != (args.goal is None):
        parser.error("--start and --goal must be given together")
    if args.vmax <= 0:
        parser.error("--vmax must be positive")

    try:
        dataset = load_dataset(args.graph, args.tasks)
        if args.start is not None:
            tasks = [Task("Query", args.start, args.goal, args.required or None,
                          DataLoader.parse_blocked_edges(args.blocked or ""))]
        else:
            tasks = dataset.tasks
    except InputValidationError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    if not tasks:
        print("error: no requests to run: add tasks.csv next to the graph, use --tasks, or give --start and --goal",
              file=sys.stderr)
        return 2

    graph = dataset.graph
    algorithms = list(ALGORITHMS) if args.algorithm == "both" else [args.algorithm]
    print(f"graph: {args.graph}  ({len(graph.nodes)} buildings, {edge_count(graph)} edges, "
          f"coordinates: {'yes' if has_coordinates(graph) else 'no'})")
    print(f"requests: {len(tasks)}\n")

    runs: List[TaskRun] = []
    for task in tasks:
        print(f"{task.task_id}  {task.start} -> {task.destination}   "
              f"blocked: {format_blocked(task.blocked_edges) or '-'}   required: {task.required_visit or '-'}")
        for name in algorithms:
            run = run_task(graph, task, name, args.vmax)
            runs.append(run)
            print_run(run)
        print()

    warnings = list(dict.fromkeys(w for run in runs for w in run.warnings))
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if args.csv:
        write_runs_csv(args.csv, runs)
        print(f"results written to {args.csv}")

    found = sum(1 for r in runs if r.status == "SUCCESS")
    none = sum(1 for r in runs if r.status == "NO_FEASIBLE_ROUTE")
    invalid = sum(1 for r in runs if r.status == "INVALID_REQUEST")
    print(f"summary over {len(runs)} runs: {found} SUCCESS, {none} NO_FEASIBLE_ROUTE, {invalid} INVALID_REQUEST")
    return 1 if invalid else 0


def print_run(run: TaskRun) -> None:
    label = f"  {ALGORITHM_LABELS[run.algorithm]:<5}"
    if run.error:
        print(f"{label}INVALID_REQUEST  {run.error}")
        return
    result = run.result
    metrics = f"expanded_states={result.expanded_states}  runtime_ms={result.runtime_ms:.3f}"
    if result.success:
        print(f"{label}SUCCESS  solution_cost={format_cost(result.total_cost)}  {metrics}")
        print(f"{'':7}path_sequence: {format_path(result.path)}")
    else:
        print(f"{label}{result.status_message}  {metrics}")


if __name__ == "__main__":
    sys.exit(main())
