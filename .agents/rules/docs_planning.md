---
description: Ensure all planning and issue tracking documents are stored in the docs/ folder.
---
# Issue Planning Rule

When the user asks to "armar el plan para el issue X", do NOT use the standard `implementation_plan.md` artifact.
Instead, directly create a new markdown file inside the `docs/` folder (e.g., `docs/issue_17_dockerization.md`) following the established structure for issues in this project.

**CRITICAL REQUIREMENT:**
Every issue plan must include explicit Git and Test commands logically ordered. For example:
- **Step 1 (At the beginning):** Exact command to create the feature branch (`git checkout -b feature/issue-X`).
- **Final Step (At the end):** Exact commands to run tests locally (e.g. `pytest`, `docker compose up -d db`, `curl`), add, commit, push, and close the issue on GitHub.
