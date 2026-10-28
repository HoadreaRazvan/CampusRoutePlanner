# Project Requirements and Acceptance Criteria Specification

**Project 1: Campus Route and Constraint Planner**  
**Role Responsible:** Product Owner (Voice of the Client)  
**Client:** Campus Maintenance Team  
**Evaluation:** Fundamentals of Artificial Intelligence · Master's Programme

---

## 1. Project Background and System Boundary

The campus maintenance team requires an automated planning tool to calculate optimal transit paths between campus buildings. Real-world daily maintenance scenarios introduce temporary pathway closures and mandatory intermediate stops (e.g., retrieving special keys, tools, or permits) before reaching the target work site.

### Scope and Boundaries
* **Operating Domain:** The system determines valid, minimal-time routes strictly within the provided graph structure and user constraints.
* **Out of Scope:** The system does not interface with physical GPS sensors, real-time campus mapping services (e.g., Google Maps), or computer vision feeds. It cannot verify whether an unblocked path is physically walkable beyond the supplied configuration.

---

## 2. Input Specifications

The software must ingest and validate three standardized data sources:

1. **Campus Network Topology (`edges.csv`)**
   * Directed graph representation: `source,destination,travel_time` (or `from,to,weight`).
   * Edge weights define non-negative transit duration ($cost \ge 0$).
2. **Geographical Coordinates (`nodes.csv`)** *(provided in `graph2_campus`)*
   * Cartesian coordinates: `node_id,x,y`.
   * Serves as spatial ground-truth to calculate admissible, consistent heuristics for informed search.
3. **Transit Requests (`tasks.csv`)**
   * `start`: Starting building identifier.
   * `destination`: Final target building identifier.
   * `required_visit`: Mandatory building waypoint (pickup/checkpoint) that must be visited prior to destination arrival.
   * `blocked_edges`: Semicolon/comma-delimited list of temporarily unavailable directed edges (e.g., `[(u1, v1), (u2, v2)]`).

---

## 3. Formal Acceptance Criteria (AC)

### AC-01: Mandatory Waypoint Satisfaction
* **Given** a transit query with `start`, `destination`, and a designated `required_visit`,
* **When** a route is computed,
* **Then** the sequence of visited nodes must include `required_visit` before the journey terminates at `destination`.
* *Constraint Rule:* Reaching `destination` before `required_visit` has been visited does not constitute a valid goal state.

### AC-02: Edge Exclusion and Dynamic Closures
* **Given** a list of blocked edges in `tasks.csv`,
* **When** generating transitions from state $u$ to state $v$,
* **Then** no blocked connection $(u, v)$ shall be traversed by the search agent.

### AC-03: Search State Formulation
* To ensure optimal substructure without prematurely pruning valid paths, the internal search state must be explicitly represented as a composite tuple:
  $$\text{State} = (u, \text{visited\_required})$$
  where $u \in V$ is the current building identifier and $\text{visited\_required} \in \{\text{True}, \text{False}\}$.
* Reaching building $u$ without visiting the required stop is not equivalent to reaching $u$ with the stop completed; the two must occupy separate nodes in the state space graph.

### AC-04: Algorithm Support and Solution Optimality
* The engine must implement and support two search strategies:
  1. **Uniform Cost Search (UCS):** Uninformed baseline guaranteeing the optimal path cost.
  2. **A\* Search:** Informed search leveraging spatial coordinates.
* **Heuristic Correctness:**
  * When $h(n) = 0$, A\* search behavior must collapse identically to UCS.
  * When using Euclidean straight-line distance divided by the maximum theoretical campus speed $v_{\max}$, the heuristic must remain strictly admissible ($h(n) \le h^*(n)$) and monotonic/consistent.
* Both algorithms must yield identical minimum solution costs on all deterministic benchmark graphs.

### AC-05: Telemetry and Reporting Metrics
* Upon completing every query, the system must report:
  1. `solution_cost`: Total travel time of the returned path.
  2. `path_sequence`: Ordered list of buildings from start to destination.
  3. `expanded_states`: Total number of state nodes removed from the priority queue.
  4. `runtime_ms`: Execution wall-clock time in milliseconds.

### AC-06: Robustness and Fault Handling
* **Unreachable Goal:** If no path satisfies the constraints (e.g., disconnected graph or closed bridge), the system must output a controlled `NO_FEASIBLE_ROUTE` status without uncaught runtime exceptions.
* **Negative Edge Weights:** If any edge in `edges.csv` has a weight $< 0$, execution must immediately abort with an `INVALID_EDGE_WEIGHT` error.
* **Malformed Input:** Missing columns, corrupted rows, or unknown building identifiers must trigger descriptive validation warnings.

---

## 4. Evaluation Datasets

| Dataset | Primary Evaluation Purpose |
| :--- | :--- |
| **`graph1_brief_example`** | **Smoke & Logic Verification:** Minimal reference graph from briefing slides; confirms waypoint diversion and blocked-edge avoidance. |
| **`graph2_campus`** | **A\* Heuristic Benchmark:** Full-scale topology with `nodes.csv` coordinates for testing Euclidean admissible heuristics. |
| **`graph3_traps`** | **Adversarial & Metric Analysis:** Dead-ends and suboptimal cycles designed to compare expanded state counts between UCS and A\*. |

---

## 5. Final Demonstration Checklist (4-Minute Defense)

- [ ] **Standard Execution (2 min):** Demonstrate an ordinary transit request, highlighting correct waypoint resolution, minimal travel time, and output telemetry.
- [ ] **Edge Case / Failure Mode (2 min):** Demonstrate system handling when a critical connector is blocked, illustrating route recalculation or clean termination with `NO_FEASIBLE_ROUTE`.
- [ ] **Code Reproducibility:** Ensure repository can be cloned, installed, and verified on an unseen test graph within 30 seconds.