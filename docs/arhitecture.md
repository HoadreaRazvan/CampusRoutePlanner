# System Architecture Specification

**Project:** Campus Route and Constraint Planner  
**Role:** Software Architect  

---

## 1. High-Level Architecture

The application is structured into four decoupled layers:

1. **CLI / Entry Point (`src/cli.py`)**: Handles command-line invocation, option parsing, and formatted output generation.
2. **I/O & Validation Layer (`src/io/loader.py`)**: Parses `edges.csv`, `nodes.csv`, and `tasks.csv`, validating structural constraints and edge weight non-negativity ($cost \ge 0$)[cite: 3, 7].
3. **Core Domain Models (`src/models/`)**: Contains immutable state definitions, graph data structures, and task constraints[cite: 3, 7].
4. **Search Engine Layer (`src/search/`)**: Implements search strategies deriving from `BaseSearchAlgorithm`[cite: 2, 3, 7].

---

## 2. State Space Formalization

Per Acceptance Criterion AC-03[cite: 3, 7], state space search cannot depend solely on the current building identifier $u$, because visiting a mandatory waypoint (`required_visit`) changes the valid state transitions and goal validity.

The search state is explicitly defined as an immutable tuple:

$$\text{State} = (u, \text{has\_visited\_required})$$

- **$u \in V$**: The current building node identifier[cite: 3, 7].
- **$\text{has\_visited\_required} \in \{\text{True}, \text{False}\}$**: Boolean flag indicating whether the mandatory waypoint has been visited[cite: 3, 7].

Reaching building $u$ with $\text{has\_visited\_required} = \text{False}$ is treated as a separate graph node from $(u, \text{True})$, preventing premature pruning of valid routes[cite: 3, 7].

---

## 3. Class Contracts & Abstract Interfaces

All search algorithms must subclass `BaseSearchAlgorithm` and return a structured `SearchResult` telemetry object containing execution metrics (`path`, `total_cost`, `expanded_states`, `runtime_ms`)[cite: 3, 7].

---

## 4. Error & Fault Handling Strategy

- **Negative Edge Weights**: Raises `ValueError("INVALID_EDGE_WEIGHT")` during graph loading[cite: 3, 7].
- **Unreachable Goal**: Returns `SearchResult.no_route()` with `status_message="NO_FEASIBLE_ROUTE"`[cite: 3, 7].
- **Malformed CSVs**: Raises descriptive `ValueError` or `KeyError` messages before search initialization[cite: 3, 7].