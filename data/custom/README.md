# Custom edge-case maps

Small maps built by the team to test special cases (same CSV format as the provided graphs).
Expected answers are in `tests/test_edge_cases.py`.

| Folder | What it checks |
| --- | --- |
| `zero_cost_cycle` | A cycle of 0-minute edges must not loop forever; a required stop inside the cycle costs 0. |
| `parallel_edges` | Two edges A>B with different times: the cheaper one is used; blocking A>B closes both. |
| `waypoint_round_trip` | Start = goal with a stop elsewhere; the stop is a dead-end spur, so the route must revisit Hub; required stop = goal; required stop = start. |
| `blocked_bridge` | One one-way bridge B>C between two areas: blocking it, travelling against it, a disconnected island, and a stop that is only reachable after the goal. |
