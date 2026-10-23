---
name: git-guide
description: Show a team member the exact git commands to (1) get the latest version of the code and (2) send their work through a pull request that another member reviews. Use when someone asks how to update/pull/sync the repo, how to open a PR, how to review a PR, or "what commands do I run".
---

# Git guide for the team

Show the person the commands for what they asked, in order, with one line on what each does.
Run them for the person only if they ask you to. If any command fails or prints a conflict, stop
and explain it before going further.

## 1. Get the latest version of the code

Run this every time before you start working.

```bash
git switch main      # go to the main branch
git pull             # download everything the team has merged
```

If `git pull` refuses because you have local changes, commit them on your branch first (section 2),
or keep them aside with `git stash` → `git pull` → `git stash pop`.

**If you are already working on a branch** and `main` has moved on, bring the new changes into it:

```bash
git switch main
git pull
git switch <your-branch>
git merge main       # if there are conflicts: fix the files, then git add <files> and git commit
```

## 2. Send your work through a pull request

```bash
git switch main
git pull                                  # start from the latest version
git switch -c <issue-number>-<short-name> # your own branch, e.g. 3-csv-loader

# ... work on the files ...

git status                                # see what changed
git add <file1> <file2>                   # add only your files
git commit -m "#3 read edges.csv"         # short message: what changed
git push -u origin <your-branch>          # send the branch to GitHub
```

Then on GitHub:

1. Open the link that `git push` prints (`.../pull/new/<your-branch>`), or go to the repo →
   **Pull requests** → **New pull request** and pick your branch.
2. Write a title and a short description (`Closes #3` if there is an issue).
3. Under **Reviewers** pick **another team member**.
4. Click **Create pull request**.
5. Do **not** merge it yourself. Wait for the review.

Need to change something after the review? Commit and push again on the same branch; the pull
request updates by itself:

```bash
git add <files>
git commit -m "#3 fix review comments"
git push
```

## 3. Review a colleague's pull request

1. On GitHub: **Pull requests** → open it → **Files changed**, read the code.
2. To try it on your computer:
   ```bash
   git fetch
   git switch <their-branch>
   python -m pytest
   ```
3. On GitHub: **Review changes** → **Approve** or **Request changes**, with a comment.
4. After approval, click **Merge pull request**.

## 4. After a merge

```bash
git switch main
git pull                         # get the merged version
git branch -d <your-branch>      # delete the old local branch
```

## Golden rules

- Always `git pull` on `main` before creating a new branch.
- Never commit or push directly to `main`.
- Every pull request is reviewed by someone other than the author.
