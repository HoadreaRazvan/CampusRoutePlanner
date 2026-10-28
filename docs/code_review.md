# Code Review and Architecture Guidelines

**Role:** Software Architect  

---

## 1. Pull Request Guidelines

1. **No Direct Pushes to `main`**: All changes must be reviewed by at least one team member prior to merging[cite: 2, 5].
2. **Interface Compliance**: Algorithm implementations must inherit from `BaseSearchAlgorithm` in `src/search/base.py`[cite: 2].
3. **State Immutability**: The `State` dataclass must remain frozen (`frozen=True`) to maintain hashing integrity in priority queues and closed sets[cite: 3, 7].
4. **Test Pass Guarantee**: All code changes must pass `python -m pytest` without warnings or failures[cite: 5].

---

## 2. Reviewer Checklist

- [ ] Does the code adhere to the specified module boundaries?
- [ ] Are type hints provided for all public functions?
- [ ] Are exceptions handled gracefully according to the error strategy[cite: 3, 7]?