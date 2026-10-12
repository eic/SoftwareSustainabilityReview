---
id: engineering
title: Code health & engineering practices
order: 1
criteria:
  - id: eng.change-control
    title: Change control & code review
  - id: eng.ci
    title: Continuous integration
  - id: eng.testing
    title: Testing
  - id: eng.static-quality
    title: Static analysis & consistency
  - id: eng.modularity
    title: Architecture & language standards
---

# Code health & engineering practices

Does the project's engineering process keep the code correct and changeable as people come and
go? EIC principle 8 commits the stack to being production-ready throughout development and to
using metrics to evaluate software quality. Principle 3 asks for a modular design that is robust
against changes in the computing environment.

## `eng.change-control` — Change control & code review

**Question.** Do changes reach the default branch through reviewed pull requests in a public
repository?

**Check.** `metrics:git.first_parent_pr_fraction_12m` (the share of default-branch first-parent
commits that came from a merged PR, by commit subject or the GitHub commit-to-PR API),
`metrics:prs.reviewed_fraction_12m`, `metrics:repo.default_branch_protected`,
`metrics:repo.rulesets`, and `metrics:files.codeowners`. Also check whether the public repository
is where development happens, rather than a mirror of a private repository.

| Level | Anchor |
| --- | --- |
| 0 | No public version control, or the public repository is a mirror or snapshot without the real change history. |
| 1 | Public history, but most changes are pushed straight to the default branch, or fewer than 50% of merged PRs are reviewed by someone other than the author. |
| 2 | At least 80% of default-branch changes in the last 12 months arrive through PRs, and at least 50% of merged PRs have a review from someone other than the author. |
| 3 | Nearly all changes arrive through PRs, at least 90% of merged PRs are reviewed by someone other than the author, review is enforced (branch protection, rulesets, or CODEOWNERS), and the review expectations are documented (PR template or guidelines). |

**Typical actions.** Enable branch protection or a ruleset that requires one approving review.
Add `CODEOWNERS`. Add `.github/pull_request_template.md`.

## `eng.ci` — Continuous integration

**Question.** Is every change built and tested automatically, and is the default branch kept
green?

**Check.** `metrics:ci.*` (workflows, triggers, success rate on the default branch). Read the
workflow files to see what is built and whether tests run. This criterion judges *automation*.
Which platforms are covered belongs to `dist.portability`, and running in eic-shell belongs to
`eic.environment`.

| Level | Anchor |
| --- | --- |
| 0 | No automated builds. |
| 1 | CI exists but does not run on every PR, does not run tests, or succeeds on fewer than 50% of recent default-branch runs. |
| 2 | CI builds and runs the test suite on every PR and on the default branch, with at least 80% of recent default-branch runs succeeding. |
| 3 | As 2, plus CI covers every configuration the project declares as supported, passing CI is required before merge, CI includes at least one integration or downstream check (for example a full workflow on sample data, or building a dependent), and at least 90% of default-branch runs succeed. |

**Typical actions.** Add a `pull_request`-triggered workflow that builds and runs `ctest` or
`pytest`. Mark CI as a required status check. Add a job that runs an end-to-end example.

## `eng.testing` — Testing

**Question.** Are there automated unit, integration, and regression tests, and are new changes
tested?

**Check.** `metrics:code.test_files`, `metrics:code.test_frameworks`,
`metrics:prs.test_touching_fraction_12m`, and `metrics:files.codecov`. Read the test directory to
see what it actually covers. For physics software, regression means comparing outputs with
reference results or physics benchmarks.

| Level | Anchor |
| --- | --- |
| 0 | No automated tests. |
| 1 | Some tests exist (smoke tests, examples run as tests) but cover a minority of components, or the tests are not run in CI. |
| 2 | Unit tests cover the majority of modules or algorithms and run in CI on every PR, and there is at least one integration or end-to-end test. |
| 3 | As 2, plus regression tests against reference outputs (benchmarks, numerical references, or file comparisons), test coverage measured and published, and at least 40% of merged PRs in the last 12 months touch test files. |

**Typical actions.** Add Catch2 or pytest unit tests for the core algorithms. Add a regression job
that compares output files with a reference using [epic-capybara](https://github.com/eic/epic-capybara).
Publish coverage with Codecov.

## `eng.static-quality` — Static analysis & consistency

**Question.** Are formatting, linting, and static analysis automated and enforced?

**Check.** `metrics:files.clang_format`, `clang_tidy`, `pre_commit`, `python_lint`, `mypy`, and
`editorconfig`. Look for warning flags and sanitizer jobs in the workflows and build files.

| Level | Anchor |
| --- | --- |
| 0 | No formatter, linter, or static analysis configured. |
| 1 | A formatter or linter is configured but not enforced in CI or pre-commit, or covers only part of the code. |
| 2 | A formatter and at least one linter or static analyzer are enforced on every PR (CI or pre-commit.ci), and compiler warnings are enabled. |
| 3 | As 2, plus deeper analysis runs routinely (clang-tidy, cppcheck, IWYU, sanitizers, or strict type checking), warnings fail CI or are tracked to zero, and there are no blanket suppressions. |

**Typical actions.** Add `.pre-commit-config.yaml` with clang-format or ruff and enable
pre-commit.ci. Add a clang-tidy job on changed files. Add an ASan/UBSan build to CI.

## `eng.modularity` — Architecture & language standards

**Question.** Is the code organized into components with clear interfaces, built with standard
tooling, and written to current language standards?

**Check.** `metrics:code.cxx_standard`, `metrics:code.requires_python`,
`metrics:code.largest_source_files`, and the build system files. Look for hard-coded paths,
configuration compiled into the source, global state, and install or export targets.

| Level | Anchor |
| --- | --- |
| 0 | Loose scripts or macros with no build or packaging system, hard-coded absolute paths, or configuration edited in source. |
| 1 | A build system exists, but the code is largely monolithic (very large files, global state), the language standard is outdated (C++ before C++17, Python 2, interpreted ROOT macros as the main code path) or unspecified, or configuration is partly hard-coded. |
| 2 | Code is organized into components with clear interfaces, uses a current language standard (C++17 or later, Python 3.9 or later), keeps configuration outside the code, and builds and installs through standard tooling (CMake install targets, `pyproject.toml`). |
| 3 | As 2, plus components can be reused independently (exported CMake package config, installable plugins, or a Python package API), the public API is separated from internals, and the architecture is documented. |

**Typical actions.** Set `CMAKE_CXX_STANDARD 20` and add `install(EXPORT ...)`. Move constants into
configuration files or parameters. Split files over 2000 lines along component boundaries.
