---
id: documentation
title: Documentation & usability
order: 2
criteria:
  - id: doc.user
    title: User onboarding
  - id: doc.developer
    title: Developer & API documentation
  - id: doc.contributing
    title: Contribution guidelines
---

# Documentation & usability

Can a new user get the software running, and can a new developer change it, without asking the
original authors? EIC principle 4 commits to user-centered design and to keeping barriers low for
smaller teams. Principle 7 commits to training and support for new users.

## `doc.user` — User onboarding

**Question.** Are there complete installation instructions, a quick start, and working examples?

**Check.** README, documentation site (`metrics:repo.homepage`, `metrics:files.sphinx`, `mkdocs`,
and `doxygen`), and the examples directory. Also check whether the project has an
[EIC tutorial](https://eic.github.io/documentation/tutorials.html) or is covered by
[tutorial-ci](https://github.com/eic/tutorial-ci). Follow the install instructions on paper: do
they name every dependency and its minimum version?

| Level | Anchor |
| --- | --- |
| 0 | No README, or the README does not explain how to install or run the software. |
| 1 | The README has basic build and run instructions, but dependencies or versions are missing, or there is no runnable example. |
| 2 | Install instructions name all dependencies with versions and include the eic-shell or package-manager route, there is a runnable quick-start example, and the user-facing options and configuration are documented. |
| 3 | As 2, plus documentation is hosted and versioned with releases, examples or tutorials are executed in CI, and there is troubleshooting or FAQ material. |

**Typical actions.** Add an "Installation" section covering eic-shell and from-source builds with
dependency versions. Add `examples/` with a minimal run. Run the examples in CI.

## `doc.developer` — Developer & API documentation

**Question.** Is the API documented, and is there an architecture overview that explains how
the parts fit together?

**Check.** Docstrings or Doxygen comments on public interfaces (sample several public headers or
modules), generated API docs, and design or architecture pages.

| Level | Anchor |
| --- | --- |
| 0 | No developer documentation and sparse or no comments on public interfaces. |
| 1 | Some interfaces are commented, but there is no generated API reference and no architecture overview. |
| 2 | Most public interfaces are documented, API docs are generated (Doxygen, Sphinx, or similar), and an architecture overview exists. |
| 3 | As 2, plus generated docs are published automatically by CI for the default branch or releases, and the design, data flow, and algorithms are documented with references. |

**Typical actions.** Add a Doxygen configuration and a Pages deployment workflow. Write
`docs/architecture.md` with a component diagram. Document every public header.

## `doc.contributing` — Contribution guidelines

**Question.** Can an outside developer set up a development environment, run the tests, and
submit an acceptable PR by following the documentation alone?

**Check.** `metrics:community.files.contributing` (including any inherited from the organization),
`metrics:files.pr_template`, `metrics:files.issue_templates`, `metrics:files.devcontainer`, and
issues labeled `good first issue`.

| Level | Anchor |
| --- | --- |
| 0 | No contribution guidance. |
| 1 | A short note ("open a PR") without setup, test, or convention details. |
| 2 | `CONTRIBUTING` (or equivalent) describes development environment setup, building and running the tests, coding conventions, and the PR process, and issue or PR templates exist. |
| 3 | As 2, plus review expectations and how to propose larger changes are documented, newcomer issues are labeled and some are closed by newcomers, and a ready-made development environment is documented (eic-shell or devcontainer). |

**Typical actions.** Write `CONTRIBUTING.md` covering eic-shell setup, build, `ctest`, and PR
conventions. Add issue templates. Label five newcomer issues.
