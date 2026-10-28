---
name: commit
description: Help a team member commit their work to this repo the team's way - own branch, tests pass, clear message, push, pull request. Use when someone wants to commit, push, or open a PR.
---

# Commit to the team repo

Team rule: **branch → pull request → review by another member → merge.** Never commit on `main`.
Commits must be in the name of the person running this session.

1. **Identity.** Run `git config user.name` and `git config user.email`. Ask the person to
   confirm they are their own. If not, set them with `git config user.name "..."` and
   `git config user.email "..."`.
2. **Branch.** Run `git branch --show-current`. If on `main`, create a branch:
   `git switch -c <issue-number>-<short-name>` (e.g. `3-csv-loader`). Ask for the issue number.
3. **Tests.** If the repo has tests, run `python -m pytest`. If something fails, do not
   commit; show the error.
4. **Stage.** Show `git status`, confirm with the person which files to add, then
   `git add <files>`. Never add `.venv/`, `__pycache__/` or passwords/tokens.
5. **Commit.** Message format: `#<issue> <what changed>`, e.g. `#3 read edges.csv`.
   Propose it, let the person adjust it, then `git commit -m "..."`.
6. **Push.** `git push -u origin <branch>`.
7. **Pull request.** Give the link `https://github.com/<owner>/<repo>/compare/<branch>?expand=1`
   (owner/repo from `git remote -v`). Remind them to ask **another member** for a review.
   Never merge the PR yourself.

If a significant decision was made, or AI helped substantially, remind them to note it in the
team's decision log (or in the commit message if there is no log yet).
