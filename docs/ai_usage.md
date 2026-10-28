# Use of AI tools

Required by the project brief: record substantial AI assistance and how its output was checked.

## Tool

Claude Code (Anthropic), used from the terminal inside this repository.

## What it was used for

| Area | Files | Assistance |
|---|---|---|
| Work plan | — | Split the project into steps and commits; listed the traps in the provided graphs. |
| CSV loading and validation | `src/io/` | Adapted the loader to the real file formats (`minutes`, `id`, `goal`, `A>B`) and wrote the error codes. |
| Search | `src/search/` | Shared best-first core, UCS, A*, heuristic consistency check and fallback. |
| Tests and sample data | `tests/`, `data/custom/` | Test suite, invalid sample CSVs, custom edge-case maps. |
| CLI and benchmark | `src/cli.py`, `src/planner.py`, `experiments/` | Command-line interface and UCS vs A* comparison. |
| Graphical interface | `src/gui/` | Local web app: search replay, race mode, interactive requests, file drop. |
| Documentation | `docs/analysis.md`, `docs/decision_log.md` (ADR-04 to ADR-11), `README.md` | First drafts. |

## How the output was checked

- **Independent reference answers.** Before the search code was written, the expected cost of all 22
  provided requests was computed by a separate throw-away script (not part of the project code). The
  tests assert these values for both algorithms.
- **Route validity checked independently of the algorithm** (`tests/helpers.py`): every step is a real,
  unblocked edge, the required stop is visited, and the reported cost equals the sum of the edges.
- **Heuristic:** admissibility checked against the true cost for all 121 pairs of buildings in
  `graph2_campus`; consistency checked on every edge.
- **A\* with h = 0 versus UCS:** identical path, cost and expanded states on every request.
- **Invalid input:** each sample file in `tests/fixtures/` must produce its specific error code.
- **GUI:** the API is tested directly and through the running server (`tests/test_gui.py`); the replay
  length must equal the reported expanded states. The pages were checked with headless-browser screenshots.
- One mistake was caught by the tests this way: the plan stated that `graph3_traps` has 11 buildings;
  it has 12.
- Every change goes through a pull request reviewed by another team member.

## Checked by the team

<!-- Each member: add one line after reviewing / tracing the code by hand. -->

| Member | What was checked | How |
|---|---|---|
| | | |
