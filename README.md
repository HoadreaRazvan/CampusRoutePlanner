# Campus Route and Constraint Planner

Project 1, *Fundamentals of Artificial Intelligence*.

## Setup

Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest        # runs the tests (once the team has added them)
```

## Limits of the system

- The planner only knows the graph it is given. It cannot check whether a real path is open or safe.
- Invalid input is rejected with a clear message, never silently accepted: missing or wrong
  columns, non-numeric or negative travel times, unknown buildings, badly written blocked edges.
- "No route exists" is a valid answer, not an error.

## How to contribute

Branch → pull request → review by another member → merge. Never push directly to `main`.
With Claude Code, type `/commit` in this folder and it guides you step by step.
Type `/git-guide` to see the commands for getting the latest code, opening a pull request
and reviewing one.
