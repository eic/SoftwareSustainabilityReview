# Agent instructions

This repository holds the EIC Software Sustainability Review: human-owned rubrics (`rubrics/`), the list
of assessed projects (`projects.yaml`), review passes (`passes/`), and the `ssr` tooling (`ssr/`) that
collects metrics, validates assessments, and builds the GitHub Pages site.

- **To run a review pass or (re)assess projects**, follow `.claude/skills/review-pass/SKILL.md` step
  by step. It applies to any agent, not only Claude Code.
- Rubrics, `projects.yaml`, and the tooling change only through separate, human-reviewed PRs. Never
  mix them into a pass PR.
- Tests: `uv run --extra test pytest`. Checks: `uv run ssr validate`. Site: `uv run ssr build-site`.
- Assessments must not name individuals or include e-mail addresses. Metrics count people and never
  identify them.
