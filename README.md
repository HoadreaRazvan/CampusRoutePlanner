Campus Route and Constraint Planner

Project 1, Fundamentals of Artificial Intelligence.

System Overview & Architecture

The system computes optimal transit routes between buildings on a university campus while handling dynamic constraints such as closed pathways and mandatory intermediate stops.

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


Setup

Python 3.10+.

python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest        # runs the tests (once the team has added them)


Repository Structure

src/models/: Core domain models (State, Graph, Node, Edge, Task).

src/search/: Abstract search interface BaseSearchAlgorithm and algorithm implementations (UCS, A*).

src/io/: CSV data parsing and validation (DataLoader).

docs/: System architecture (architecture.md), decision records (decision_log.md), and code review guidelines (code_review.md).

tests/: Automated unit and integration tests.

Limits of the system

The planner only knows the graph it is given. It cannot check whether a real path is open or safe.

Invalid input is rejected with a clear message, never silently accepted: missing or wrong columns, non-numeric or negative travel times, unknown buildings, badly written blocked edges.

"No route exists" is a valid answer, not an error.

How to contribute

Branch → pull request → review by another member → merge. Never push directly to main.
With Claude Code, type /commit in this folder and it guides you step by step.