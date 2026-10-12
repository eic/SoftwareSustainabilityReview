# EIC Software Sustainability Review

Objective, comparable assessments of the sustainability of software used in the Electron-Ion Collider
(EIC) community, measured against the EIC-supported software stack. Each assessment ends in a
concrete action plan for the project.

**Site:** https://eic.github.io/SoftwareSustainabilityReview/

## What is assessed

The projects listed in [`projects.yaml`](projects.yaml) are scored against 26 criteria in six
categories ([`rubrics/`](rubrics)):

| Category | Criteria |
| --- | --- |
| Code health & engineering practices | change control & review, CI, testing, static analysis, architecture & standards |
| Documentation & usability | user onboarding, developer/API docs, contribution guidelines |
| Community & governance | responsiveness, contributor base, bus factor, governance & roadmap, code of conduct & support |
| Infrastructure & distribution | packaging, releases, dependencies & supply chain, reproducibility, portability |
| EIC ecosystem integration | reuse of EIC-supported components, data formats, eic-shell compatibility, currency with the stack |
| Impact & long-term viability | licensing, citation, adoption, institutional backing |

Every criterion uses the same scale: **0 Absent · 1 Initial · 2 Established · 3 Sustained**. Each
level has concrete, observable anchors. The rubrics build on the
[EIC Statement of Software Principles](https://eic.github.io/activities/principles.html). They
define the EIC-supported stack as what eic-shell ships ([`reference/`](reference)).

The assessments are deliberately free of praise. Each one states the level, the evidence, the gap
to the next level, and the smallest actions that close it. The actions are prioritized and point to
existing EIC resources (eic-shell CI actions, eic-spack, EDM4eic, epic-capybara) wherever they fit.

## How it works

```
projects.yaml ──► ssr collect ──► passes/<id>/<project>.metrics.json     (deterministic, from git + GitHub API)
rubrics/      ──► AI assessor ──► passes/<id>/<project>.assessment.yaml  (levels, evidence, gaps, actions)
                  ssr validate     schema, completeness, evidence and privacy checks
                  pull request ──► human review ──► merge ──► GitHub Pages
```

- **Metrics** (`ssr collect`) are computed with fixed rules from public data: commit and author
  activity, bus factor, review coverage, issue response times, CI success rate, releases,
  packaging in eic-spack, Spack, and eic-shell, use of EIC-supported components, vendored code,
  and the presence of community files. People are counted, never named.
- **Assessments** are written by an AI agent following [`rubrics/_common.md`](rubrics/_common.md),
  with the metrics as ground truth and the project checkout as evidence. Levels follow the anchors
  literally. Only public evidence counts.
- **A review pass** is one directory, `passes/<YYYY-MM-DD>/`, delivered as one pull request. The
  [`review-pass` skill](.claude/skills/review-pass/SKILL.md) drives it end to end. Passes can run
  locally with Claude Code (or another agent, see [`AGENTS.md`](AGENTS.md)), or in CI through the
  [`review-pass`](.github/workflows/review-pass.yml) workflow.
- **History** is kept: every pass stays in the repository, and project pages show how each criterion
  changed between passes.

See [REVIEWING.md](REVIEWING.md) for running a pass, reviewing a pass PR, and changing the rubrics or the
project list.

## Tooling

```bash
uv run ssr --help
uv run ssr validate             # check projects.yaml, rubrics, and all passes
uv run ssr build-site --out _site
uv run --extra test pytest
```

Requires Python ≥ 3.10, [uv](https://docs.astral.sh/uv/), `git`, and an authenticated
[`gh`](https://cli.github.com/).

## License

Apache-2.0. See [LICENSE](LICENSE).
