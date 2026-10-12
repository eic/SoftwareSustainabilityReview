# Review passes

One directory per pass, named `YYYY-MM-DD` (with a `-2`, `-3`, … suffix for a second pass on the same day),
added in a single pull request:

| File | Written by | Content |
| --- | --- | --- |
| `manifest.yaml` | `ssr new-pass` | pass id, assessor agent and model, rubric commit, stack snapshot commit, projects |
| `<project>.metrics.json` | `ssr collect` | deterministic metrics from git, the GitHub API, and the file tree |
| `<project>.assessment.yaml` | AI assessor | per-criterion level, confidence, rationale, evidence, gaps, actions ([schema](../schema/assessment.schema.json)) |

Passes are append-only: a later pass supersedes an earlier one on the site but never edits it.
