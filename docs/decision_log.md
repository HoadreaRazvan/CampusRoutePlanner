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