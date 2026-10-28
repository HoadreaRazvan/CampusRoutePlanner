# Benchmark: UCS vs A*

Runtime is the median of 50 runs after 2 warm-up run(s), measured inside the search (loading and validation excluded). Timings depend on the machine; expanded states and costs do not.

`A* (Euclidean)` falls back to h = 0 on graphs without coordinates, so there it equals `A* (h=0)`.

## Summary per graph

| Graph | Tasks | Variant | Routes found | Total expanded states | Total median runtime (ms) |
|---|---|---|---|---|---|
| graph1_brief_example | 7 | UCS | 5 | 29 | 0.0384 |
| graph1_brief_example | 7 | A* (h=0) | 5 | 29 | 0.0384 |
| graph1_brief_example | 7 | A* (Euclidean) | 5 | 29 | 0.0388 |
| graph2_campus | 6 | UCS | 6 | 77 | 0.1525 |
| graph2_campus | 6 | A* (h=0) | 6 | 77 | 0.1518 |
| graph2_campus | 6 | A* (Euclidean) | 6 | 59 | 0.1323 |
| graph3_traps | 9 | UCS | 6 | 61 | 0.0755 |
| graph3_traps | 9 | A* (h=0) | 6 | 61 | 0.0750 |
| graph3_traps | 9 | A* (Euclidean) | 6 | 61 | 0.0767 |

## graph1_brief_example

| Task | Request | Cost | UCS expanded | A* (h=0) expanded | A* (Euclidean) expanded | UCS ms | A* (h=0) ms | A* (Euclidean) ms |
|---|---|---|---|---|---|---|---|---|
| Task_1 | S → G | 7 | 5 | 5 | 5 | 0.0070 | 0.0070 | 0.0070 |
| Task_2 | S → G, blocked C>G | 7 | 5 | 5 | 5 | 0.0066 | 0.0066 | 0.0067 |
| Task_3 | S → G, via C | 7 | 5 | 5 | 5 | 0.0073 | 0.0074 | 0.0073 |
| Task_4 | S → G, via B | 7 | 6 | 6 | 6 | 0.0075 | 0.0074 | 0.0075 |
| Task_5 | S → G, blocked A>G;B>G;C>G | no route | 4 | 4 | 4 | 0.0045 | 0.0045 | 0.0046 |
| Task_6 | G → S | no route | 1 | 1 | 1 | 0.0009 | 0.0009 | 0.0010 |
| Task_7 | S → C | 4 | 3 | 3 | 3 | 0.0046 | 0.0046 | 0.0047 |

## graph2_campus

| Task | Request | Cost | UCS expanded | A* (h=0) expanded | A* (Euclidean) expanded | UCS ms | A* (h=0) ms | A* (Euclidean) ms |
|---|---|---|---|---|---|---|---|---|
| Task_1 | Gate → Workshop | 17 | 11 | 11 | 9 | 0.0232 | 0.0215 | 0.0206 |
| Task_2 | Gate → Workshop, blocked PrintShop>Workshop | 18 | 11 | 11 | 11 | 0.0210 | 0.0212 | 0.0234 |
| Task_3 | Gate → Workshop, via Canteen | 19 | 18 | 18 | 14 | 0.0368 | 0.0368 | 0.0304 |
| Task_4 | DormA → AILab | 14 | 9 | 9 | 7 | 0.0167 | 0.0184 | 0.0164 |
| Task_5 | Workshop → SportsHall | 16 | 9 | 9 | 5 | 0.0183 | 0.0183 | 0.0122 |
| Task_6 | Gate → Workshop, blocked Library>AILab;Aula>AILab, via Rectorate | 19 | 19 | 19 | 13 | 0.0365 | 0.0356 | 0.0293 |

## graph3_traps

| Task | Request | Cost | UCS expanded | A* (h=0) expanded | A* (Euclidean) expanded | UCS ms | A* (h=0) ms | A* (Euclidean) ms |
|---|---|---|---|---|---|---|---|---|
| Task_1 | Entrance → Office | 7 | 6 | 6 | 6 | 0.0082 | 0.0082 | 0.0083 |
| Task_2 | Entrance → Lab | 9 | 7 | 7 | 7 | 0.0095 | 0.0096 | 0.0104 |
| Task_3 | Entrance → Observatory | no route | 10 | 10 | 10 | 0.0122 | 0.0122 | 0.0124 |
| Task_4 | Office → Entrance | no route | 5 | 5 | 5 | 0.0051 | 0.0051 | 0.0052 |
| Task_5 | Entrance → Lab, via Archive | no route | 10 | 10 | 10 | 0.0128 | 0.0122 | 0.0124 |
| Task_6 | Entrance → Lab, via Kitchen | 12 | 11 | 11 | 11 | 0.0137 | 0.0137 | 0.0137 |
| Task_7 | Entrance → Office, blocked HallA>HallB | 10 | 4 | 4 | 4 | 0.0041 | 0.0041 | 0.0042 |
| Task_8 | Entrance → Entrance | 0 | 1 | 1 | 1 | 0.0009 | 0.0009 | 0.0009 |
| Task_9 | HallA → Roof, via HallA | 7 | 7 | 7 | 7 | 0.0090 | 0.0090 | 0.0092 |
