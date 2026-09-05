# Issue Documentation Standard

All issue planning documents must be written in **English** and follow the structure
described below. This applies to any agent creating a `docs/issue_N_*.md` file.

---

## Canonical File Naming

```
docs/issue_{N}_{short_slug}.md
```

Examples: `issue_1_edgar_client.md`, `issue_6_chunker.md`.

---

## Required Document Structure

Every issue doc must contain these sections **in order**:

### Header
```markdown
# Workflow and Specification: Issue {N} — {Issue Title}

**Milestone**: {Milestone name}
**GitHub Issue**: #{N}
**Branch**: `feature/issue-{N}-{short-slug}`
```

### Section 1 — Start the Branch
Exact shell commands to:
1. Checkout `develop` and pull latest.
2. Create the feature branch.

### Section 2 — Configure Dependencies
If the issue adds runtime dependencies:
- Show the **exact diff** to apply in `pyproject.toml` (use a `diff` code block).
- Show the shell commands to activate `.venv` and reinstall with `pip install -e ".[dev]"`.
- Include a one-liner verification command (`python -c "import pkg; ..."`).

If no new dependencies are needed, omit this section.

### Section 3 — Development
One subsection per file to create or modify, in dependency order.
Each subsection lists the class/function names and their key behavioral contracts.
Do **not** write full implementation code — describe what the class does and its key rules.

### Section 4 — Testing
- State that all tests use mocked transports (no real network calls).
- List the test file structure to create.
- Provide a **table** of test cases: `| test_name | What it verifies |`.
- Provide the exact `pytest` commands to run (all tests, individual file, single test, with coverage).

### Section 5 — Code Quality
Always include these four commands verbatim:
```bash
make format
make lint
make type-check
make check
```

### Section 6 — Push to GitHub and Close
Exact shell commands for:
1. `git add` of the relevant paths.
2. `git commit` with conventional commit format referencing the issue number.
3. `git push -u origin {branch}`.
4. `gh pr create` with `--base develop`, `--title`, and `--body "Closes #{N}. ..."`.

### Closing Criteria
A checklist of the minimum passing conditions before the PR can be merged:
- `pytest --cov-fail-under=90` passes.
- `make check` passes with no warnings.
- PR references `Closes #{N}`.

---

## Language and Style Rules

- All content in **English**.
- Use `diff` code blocks for file changes to show exact lines added/removed.
- Avoid full implementation code in the doc — describe contracts and behavior only.
- Keep section headers consistent with the canonical names above.
- Use `> [!NOTE]` or `> [!IMPORTANT]` alerts sparingly for critical side-notes.
