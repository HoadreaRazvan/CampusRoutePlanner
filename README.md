# Campus Route and Constraint Planner

Project 1, *Fundamentals of Artificial Intelligence*.

The system computes minimal-time routes between buildings on a campus while handling temporary
closures (blocked edges) and a mandatory intermediate stop (required visit). It implements Uniform
Cost Search and A* over the composite state `(building, visited_required)`.

## Team

<!-- Fill in names and current primary roles. -->

| Member | Primary role |
|---|---|
| | Product Owner |
| | Software Architect |
| | Tester & Evaluator |
| | AI Developer |
| | Reliability & Safety Officer |

## Quick start

Python 3.10+, no dependencies besides `pytest`.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest                          # 147 tests
python -m src.cli data/graph2_campus      # run every request of a graph with UCS and A*
```

## Running the planner

```bash
# every request in tasks.csv, both algorithms (folder with edges.csv, optional nodes.csv, tasks.csv)
python -m src.cli path/to/graph_folder

# one algorithm, results also saved as CSV
python -m src.cli data/graph2_campus --algorithm astar --csv results.csv

# a single request, without a tasks file
python -m src.cli data/graph1_brief_example --start S --goal G --required C --blocked "A>G;B>G"

# point directly at an edges file; nodes.csv / tasks.csv next to it are picked up automatically
python -m src.cli data/graph3_traps/edges.csv
```

Options: `--algorithm ucs|astar|both` (default both), `--vmax` (fastest walking speed in m/min for the
A* heuristic, default 80), `--tasks` (another tasks file), `--csv` (save results).

Example output:

```
graph: data/graph2_campus  (11 buildings, 34 edges, coordinates: yes)
requests: 6

Task_1  Gate -> Workshop   blocked: -   required: -
  UCS  SUCCESS  solution_cost=17  expanded_states=11  runtime_ms=0.031
       path_sequence: Gate -> Library -> AILab -> PrintShop -> Workshop
  A*   SUCCESS  solution_cost=17  expanded_states=9  runtime_ms=0.027
       path_sequence: Gate -> Library -> AILab -> PrintShop -> Workshop
```

Exit codes: `0` all requests answered (a route or `NO_FEASIBLE_ROUTE`), `1` some request was invalid
(e.g. unknown building), `2` the input files were rejected (the message names the file and line).

### Input format

| File | Columns | Notes |
|---|---|---|
| `edges.csv` | `from,to,minutes` | One directed edge per row; times must be ≥ 0. Also accepts `source,destination,travel_time` / `weight`. |
| `nodes.csv` | `id,x,y` | Optional coordinates in metres; enables the A* heuristic. |
| `tasks.csv` | `start,goal,blocked_edges,required_visit` | `blocked_edges` like `A>G;B>G`; empty fields mean none. |

## Benchmark

```bash
python -m experiments.run_benchmarks                          # provided graphs → results/
python -m experiments.run_benchmarks --graphs path/to/hidden_graph
```

Writes `results/benchmark.csv` and `results/benchmark.md`: cost, expanded states and runtime (median
of 50 runs) for UCS, A* with h = 0 and A* with the Euclidean heuristic. Summary on `graph2_campus`:
same costs everywhere, 77 expanded states with UCS vs 59 with A*. Discussion in
[`docs/analysis.md`](docs/analysis.md).

## Architecture

```
                     ┌─────────────────────────┐
                     │    CLI / Main Entry     │
                     │      (src/cli.py)       │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │     CSV Data Loader     │
                     │   (src/io/loader.py)    │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  Composite Search State │
                     │ (node, visited_required)│
                     └────────────┬────────────┘
                                  │
               ┌──────────────────┴──────────────────┐
               ▼                                     ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│ Uniform Cost Search (UCS)   │       │         A* Search           │
│     (src/search/ucs.py)     │       │    (src/search/astar.py)    │
└─────────────────────────────┘       └─────────────────────────────┘
```

## Repository structure

| Path | Contents |
|---|---|
| `src/models/` | Core domain models: `State`, `Graph`, `Node`, `Edge`, `Task`. |
| `src/io/` | CSV parsing and validation (`DataLoader`, `InputValidationError`). |
| `src/search/` | `BaseSearchAlgorithm`, shared best-first core, UCS, A*, heuristics. |
| `src/planner.py` | Runs requests and formats results; shared by the CLI and the benchmark. |
| `src/cli.py` | Command-line interface. |
| `experiments/` | UCS vs A* benchmark script. |
| `results/` | Benchmark results. |
| `data/` | Provided graphs (`graph1`–`graph3`) and our edge-case maps (`data/custom/`). |
| `tests/` | Unit and integration tests; invalid sample CSVs in `tests/fixtures/`. |
| `docs/` | [Architecture](docs/architecture.md), [decision log](docs/decision_log.md), [analysis](docs/analysis.md), [code review](docs/code_review.md), [AI usage](docs/ai_usage.md). |

## Limits of the system

- The planner only knows the graph it is given. It cannot check whether a real path is open or safe.
- Invalid input is rejected with a clear message, never silently accepted: missing or wrong columns,
  non-numeric or negative travel times, unknown buildings, badly written blocked edges.
- "No route exists" (`NO_FEASIBLE_ROUTE`) is a valid answer, not an error.
- One required stop per request. When several routes are equally cheap, one is returned
  deterministically.
- Without coordinates (or if an edge is faster than `--vmax`), A* uses h = 0 and behaves exactly
  like UCS; the program says so.

## How to contribute

Branch → pull request → review by another member → merge. Never push directly to `main`.
With Claude Code, type `/commit` in this folder and it guides you step by step.
Type `/git-guide` to see the commands for getting the latest code, opening a pull request
and reviewing one.
