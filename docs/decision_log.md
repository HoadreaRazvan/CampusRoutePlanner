# Architectural Decision Records (ADR)

## ADR-01: Composite Search State Representation
* **Status:** Accepted
* **Context:** A simple search state based solely on current building $u$ fails when a path visits the destination before completing a required waypoint[cite: 3, 7].
* **Decision:** Represent search states as immutable dataclasses containing `(current_node: str, has_visited_required: bool)`[cite: 3, 7].
* **Consequences:** Guarantees search completeness and optimality under mandatory waypoint constraints[cite: 3, 7].

## ADR-02: Strict Priority Queue Determinism
* **Status:** Accepted
* **Context:** In cases of equal $g(n)$ or $f(n)$ costs, priority queue tie-breaking could lead to non-deterministic node expansion counts across environments[cite: 2].
* **Decision:** Priority queue elements are pushed as tuples containing `(f_score, g_score, tie_breaker_counter, state, path)`.
* **Consequences:** Ensures 100% deterministic, reproducible experimental metrics across execution environments[cite: 2].

## ADR-03: Admissible and Consistent Euclidean Heuristic
* **Status:** Accepted
* **Context:** A* search requires an admissible ($h(n) \le h^*(n)$) and consistent heuristic function[cite: 3, 7].
* **Decision:** The spatial heuristic is computed as $h(n) = \frac{d_{\text{euclidean}}(n, \text{goal})}{v_{\max}}$, where $v_{\max}$ is the maximum possible campus transit speed[cite: 3, 7]. When coordinates are unavailable, $h(n) = 0$, identically reducing A* to Uniform Cost Search (UCS)[cite: 3, 7].
* **Consequences:** Ensures theoretical optimality guarantees for A* search[cite: 3, 7].

## ADR-04: Goal Test When a State Is Removed From the Queue
* **Status:** Accepted
* **Context:** A goal state can be generated through an expensive edge before a cheaper route to it has been explored, especially with zero-cost edges (`graph3_traps`: `HallA → HallB` costs 0).
* **Decision:** The goal test runs when a state is popped from the priority queue, not when it is generated.
* **Consequences:** The first goal popped is optimal for UCS and for A* with a consistent heuristic. The search may expand a few more states than an early goal test would.

## ADR-05: Definition of `expanded_states`
* **Status:** Accepted
* **Context:** The queue can hold outdated duplicates of a state (pushed before a cheaper route was found). AC-05 asks for the number of states removed from the queue.
* **Alternatives:** Count every pop (duplicates included); count every generated state.
* **Decision:** Count a state when it is removed from the queue **and expanded**. Outdated entries for states already in the closed set are skipped and not counted. The goal state counts.
* **Consequences:** The number measures real search work and does not depend on how many duplicates were pushed. Documented next to every reported result.

## ADR-06: Routes May Revisit Buildings
* **Status:** Accepted
* **Context:** Some valid routes pass through a building twice, e.g. `… → Lab → Kitchen → Lounge → Lab` when Kitchen is the required stop.
* **Decision:** Graph search over the composite state `(building, visited_required)`; a building may appear twice in a path if the flag differs.
* **Consequences:** No false `NO_FEASIBLE_ROUTE`. At most 2·|V| states are expanded, so the search still terminates, even with zero-cost cycles.

## ADR-07: Equally Good Routes and Path Storage (amends ADR-02)
* **Status:** Accepted
* **Context:** Several routes can have the same minimal cost (`graph3_traps`: Entrance → Lab has three routes of 9 minutes).
* **Decision:** Return one route, chosen deterministically by `(f, g, insertion order)`. Queue entries are `(f, g, counter, state)`; the path is rebuilt from a parent map instead of being stored in every entry.
* **Consequences:** Same input → same output on every machine. Tests check the cost and the validity of the route (`tests/helpers.py: assert_valid_route`), not one specific path, unless the optimal route is unique.

## ADR-08: Heuristic Safety Check and Fallback to h = 0 (extends ADR-03)
* **Status:** Accepted
* **Context:** `distance / v_max` is only admissible if no edge is faster than `v_max`. This is a property of the data, and the hidden graph may have no coordinates at all.
* **Decision:** `v_max = 80 m/min` (client note, configurable with `--vmax`). Before using the heuristic, check every edge (`check_consistency`). If coordinates are missing or any edge is too fast, use `h = 0` and print a warning saying why.
* **Consequences:** A* never returns a suboptimal route because of bad data; in the worst case it behaves exactly like UCS. In `graph2_campus` all 34 edges pass (fastest: Gate ↔ Rectorate, 79.4 m/min).

## ADR-09: Input Validation Policy
* **Status:** Accepted
* **Context:** AC-06 requires controlled handling of malformed input, negative weights and unreachable goals.
* **Decision:**
  * Errors in the graph files (missing column, negative or non-numeric time, malformed row, missing file) stop the program with a coded `InputValidationError` and the file and line number; the CLI exits with code 2 and no traceback.
  * A request naming an unknown building is reported as `INVALID_REQUEST`; the other requests still run (exit code 1).
  * Blocking an edge that does not exist (between known buildings) is only a warning.
  * `required_visit == start` counts as already visited; `start == goal` with no required stop returns the one-building route with cost 0.
  * `NO_FEASIBLE_ROUTE` is a normal answer (exit code 0), not an error.
* **Consequences:** The hidden graph can be run end to end even if one request is wrong, and every rejection says what to fix.

## ADR-10: Runtime Measurement
* **Status:** Accepted
* **Context:** Single timings below one millisecond are dominated by noise.
* **Decision:** `runtime_ms` is measured with `time.perf_counter()` inside the search (loading and validation excluded). The benchmark reports the median of 50 runs after 2 warm-up runs.
* **Consequences:** Runtimes are comparable between algorithms within one run on one machine; expanded states remain the main measure of search effort.
