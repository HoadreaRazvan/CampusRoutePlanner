# Analysis: decisions, results and limitations

Project 1, Campus Route and Constraint Planner. Numbers below come from
`python -m experiments.run_benchmarks` (full tables in [`results/benchmark.md`](../results/benchmark.md)).

## 1. Problem formulation

| Concept | Our choice |
|---|---|
| **State** | `(building, visited_required)`. The flag is part of the state (AC-03). |
| **Initial state** | `(start, required_visit is None or start == required_visit)` |
| **Actions** | Walk along an outgoing edge that is not blocked for this request. |
| **Transition** | `(u, f) → (v, f or v == required_visit)` |
| **Goal test** | `building == goal and visited_required`, checked when the state is **removed** from the queue. |
| **Path cost** | Sum of the edge travel times (minutes, ≥ 0). |

**Why the flag matters.** Reaching building *u* before and after the required stop are two different
situations: the remaining work is not the same. If the state were only the building, the search would
close *u* the first time it reaches it (usually without the stop) and could then miss the only valid
route. The flag doubles the state space to at most 2·|V| states (22 for `graph2_campus`), which keeps
the search exact and still cheap.

**Revisiting buildings.** Because the state includes the flag, a route may pass through the same
building twice: `Entrance → … → Lab → Kitchen → Lounge → Lab` (`graph3_traps`, via Kitchen, cost 12).
Forbidding repeated buildings would wrongly return `NO_FEASIBLE_ROUTE` here.

**Blocked edges** only remove actions for one request; the graph itself is not changed.

## 2. The two methods

Both are implemented by one best-first search (`src/search/best_first.py`) that always expands the
state with the lowest `f = g + h`; only `h` differs.

| | Uniform Cost Search | A* |
|---|---|---|
| Expands next | lowest path cost `g` | lowest `g + h`, h = estimate of the remaining cost |
| Optimal when | edge costs ≥ 0 | h is admissible (tree search) / consistent (graph search with a closed set, as here) |
| Information used | edges only | edges + coordinates |

**A\* with h = 0 is UCS.** With `h = 0`, `f = g`, so the queue order, the expanded states and the
returned path are identical. The tests check this on every provided task (same path, cost **and**
expanded-state count), and the benchmark shows the same totals for `UCS` and `A* (h=0)`.

**Goal test on removal.** A goal state can be *generated* through an expensive edge before a cheaper
route to it has been explored. Testing when the state is removed from the queue guarantees that no
cheaper route is still waiting. This matters with zero-cost edges (`HallA → HallB` costs 0 in
`graph3_traps`).

## 3. The heuristic

`h(n) = straight_line_distance(n, goal) / v_max`, with `v_max = 80 m/min` (client note: nobody walks
faster than 80 metres per minute in a straight line).

**Admissible.** A walk from *n* to the goal covers at least the straight-line distance, and at most
80 m/min, so it takes at least `distance / 80` minutes: `h(n) ≤ h*(n)`.

**Consistent.** For any edge `n → m` with travel time `c`:
`h(n) ≤ dist(n, m)/v_max + h(m) ≤ c + h(m)` — the first step is the triangle inequality, the second
holds if the edge respects the speed limit (`dist(n, m)/v_max ≤ c`).

**Checked against the data, not assumed.** The second step depends on the data, so the program checks
it on every edge before using the heuristic (`check_consistency`). In `graph2_campus` all 34 edges pass;
the fastest one, Gate ↔ Rectorate, implies 79.4 m/min — just under the limit. If any edge were faster,
the heuristic could overestimate, so A* falls back to `h = 0` and prints why. The same happens when a
graph has no coordinates (graph1, graph3, and probably the hidden graph). A test also checks
`h(n) ≤ true cost` for all 121 pairs of buildings in `graph2_campus`.

**The heuristic ignores the required stop** (it only aims at the goal). It stays admissible, but when
the stop is far from the straight line it is a weak estimate. A stronger admissible option is
`(dist(n, stop) + dist(stop, goal)) / v_max` while the stop is still pending; we did not need it.

## 4. Fair comparison

- Same graphs, same requests, same code path for all variants; only `h` changes.
- Ties broken by `(f, g, insertion order)`, so expanded-state counts are deterministic.
- **Expanded states** = states removed from the queue and expanded; outdated duplicate entries are
  skipped and not counted.
- **Runtime** = `time.perf_counter()` inside the search only (no file loading or validation); median
  of 50 runs after 2 warm-up runs, because single sub-millisecond timings are noisy.
- Cost, expanded states and runtime are reported separately; the benchmark fails if two variants
  ever return different costs for the same request.

## 5. Results

Total expanded states per graph (all requests; identical costs for every variant):

| Graph | Requests | UCS | A* (h=0) | A* (Euclidean) |
|---|---|---|---|---|
| graph1_brief_example | 7 | 29 | 29 | 29 (no coordinates → h = 0) |
| graph2_campus | 6 | 77 | 77 | **59** (−23 %) |
| graph3_traps | 9 | 61 | 61 | 61 (no coordinates → h = 0) |

Per request on `graph2_campus` (UCS → A* Euclidean): 11 → 9, 11 → 11, 18 → 14, 9 → 7, 9 → 5, 19 → 13.

**Interpretation.**
- The heuristic helps most when the goal is far and the straight line points the right way
  (Workshop → SportsHall: 9 → 5).
- It helps little or not at all when a closure forces a detour away from the straight line
  (Gate → Workshop with PrintShop > Workshop blocked: 11 → 11): the heuristic does not know about
  closures, so it still ranks states near the closed shortcut as promising.
- Requests with a required stop still gain (18 → 14, 19 → 13), but less than they could, because the
  heuristic only aims at the final goal (section 3).
- Runtime differences are a few microseconds on graphs this small, and partly offset by the cost of
  computing `h`. Expanded states are the more reliable measure of search effort here.
- On graphs without coordinates A* *is* UCS. A more complex method did not produce a better result
  there — the information to support it was missing.

**Trap cases handled** (`graph3_traps` and `data/custom/`): a zero-cost edge, three equally cheap
routes, a disconnected building, one-way edges, a required stop that is a dead end, a route that must
revisit a building, start = goal, required stop = start, parallel edges, a zero-cost cycle.

## 6. Limitations

- The planner only knows the supplied graph; it cannot tell whether a path is really open or safe.
- One required stop per request (the specification asks for one). Several stops would need the state
  to track a set of visited stops (2^k flags) or an ordering.
- When several routes are equally cheap, we return one of them deterministically, not all of them.
- The heuristic is only as good as the coordinates and the `v_max` given by the client; if either is
  wrong the safety check falls back to `h = 0`, which is correct but slower.
- Runtimes are measured on one machine and are only comparable within the same run.
