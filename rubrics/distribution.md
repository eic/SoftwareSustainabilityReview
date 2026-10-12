---
id: distribution
title: Infrastructure & distribution
order: 4
criteria:
  - id: dist.packaging
    title: Packaging & installability
  - id: dist.releases
    title: Releases & versioning
  - id: dist.dependencies
    title: Dependency management & supply chain
  - id: dist.reproducibility
    title: Reproducibility & environments
  - id: dist.portability
    title: Portability & heterogeneous computing
---

# Infrastructure & distribution

Can users install a known version, reproduce a result, and run on the systems they have? EIC
principle 3 commits to running "on as many systems as possible", including HTC and HPC.
Principle 4 says EIC software "will run on the systems used by the community, easily", and
principle 6 commits to reproducible software.

## `dist.packaging` — Packaging & installability

**Question.** Can the software be installed through a standard package manager used in the
domain, and is it part of the EIC software environment?

**Check.** `metrics:packaging.*`: `eic_spack`, `spack_builtin`, `in_eic_shell`,
`eic_shell_version`, `conda_forge`, and `pypi`. Compare `metrics:releases.latest_tag` with the
packaged versions.

| Level | Anchor |
| --- | --- |
| 0 | Only manual, undocumented build steps. |
| 1 | A standard from-source build (CMake, pip) is documented, but there is no package recipe. |
| 2 | A recipe exists in a domain package manager (eic-spack, Spack, conda-forge, or PyPI) and provides the latest release. |
| 3 | As 2, plus the software ships in the EIC software environment (eic-shell) or in upstream Spack, and recipes are updated within about one eic-shell release cycle of each project release. |

**Typical actions.** Add a recipe to [eic-spack](https://github.com/eic/eic-spack) (and later to
upstream Spack). Request inclusion in [eic/containers](https://github.com/eic/containers). Publish
wheels to PyPI from a release workflow.

## `dist.releases` — Releases & versioning

**Question.** Are there regular, versioned releases with notes that tell users what changed?

**Check.** `metrics:releases.*` and `metrics:git.tags_24m`, `metrics:files.changelog`, and the text
of recent releases.

| Level | Anchor |
| --- | --- |
| 0 | No tags or releases; users consume the default branch. |
| 1 | Occasional tags or releases (fewer than 2 in 24 months), no documented version scheme, or no release notes. |
| 2 | At least 2 releases per year over the last 24 months, a documented version scheme (SemVer or CalVer), and release notes for each release. |
| 3 | As 2, plus a changelog that flags breaking changes and gives migration notes, a deprecation policy, and an automated release process (release workflow). |

**Typical actions.** Adopt SemVer and state it in the README. Tag a release at least every six
months with generated release notes. Add a release workflow and a `CHANGELOG.md`.

## `dist.dependencies` — Dependency management & supply chain

**Question.** Are dependencies declared with versions, kept minimal and current, and is the
supply chain monitored?

**Check.** Build metadata (CMake `find_package(... VERSION)`, `pyproject.toml`, `requirements*.txt`,
lockfiles, Spack recipes), `metrics:eic.vendored_candidates`, `metrics:files.dependabot`,
`renovate`, and `security`, and whether workflow `uses:` lines are pinned.

| Level | Anchor |
| --- | --- |
| 0 | Dependencies are undocumented, or external code is vendored without version or provenance. |
| 1 | Dependencies are listed in the docs or build files without version constraints. |
| 2 | All dependencies are declared in build metadata with minimum versions (or locked where appropriate), the dependency set contains only what is used, and no unmaintained vendored code remains. |
| 3 | As 2, plus automated update monitoring (Dependabot or Renovate) for language dependencies and GitHub Actions, actions pinned to versions or SHAs, a vulnerability reporting route (`SECURITY.md`), and CI that tests at both the minimum and the latest supported dependency versions. |

**Typical actions.** Add `VERSION` arguments to every `find_package`. Add `.github/dependabot.yml`
for `github-actions`. Replace vendored copies with the eic-shell or Spack packages.

## `dist.reproducibility` — Reproducibility & environments

**Question.** Can someone else recreate the exact software environment and reproduce a result?

**Check.** `metrics:files.dockerfile`, `apptainer_def`, `spack_env`, `conda_env`, `devcontainer`,
and lockfiles, plus documentation of the eic-shell version used, random-seed handling, and
provenance metadata in outputs.

| Level | Anchor |
| --- | --- |
| 0 | No environment specification; results depend on an undocumented local setup. |
| 1 | The environment is described in prose (versions listed) but not in machine-readable form. |
| 2 | A machine-readable environment exists (eic-shell version, container image, Spack environment, lockfile, or conda environment), running in it is documented, and random seeds and configuration are recorded for outputs. |
| 3 | As 2, plus the environment is versioned alongside releases (tagged images or pinned eic-shell versions), CI runs in that same environment, and outputs carry provenance metadata (software versions and configuration). |

**Typical actions.** Document the eic-shell version used for each release. Write software versions
and configuration into output metadata. Run CI in the same pinned container.

## `dist.portability` — Portability & heterogeneous computing

**Question.** Does the software build and run on the range of systems the EIC community uses,
without site-specific assumptions?

**Check.** `metrics:ci.runs_on` and `metrics:ci.container_images`, build matrices, hard-coded
site paths (`/gpfs`, `/sdcc`, `/w/`, `/work/`, `/u/`, user home directories), and documentation
of HTC, HPC, or accelerator use. For pure Python projects, read "platforms" as supported Python
versions and operating systems.

| Level | Anchor |
| --- | --- |
| 0 | Works only at one site (hard-coded site paths or site-specific services with no fallback). |
| 1 | Builds on a single OS and compiler (for example Linux with GCC); other platforms are untested. |
| 2 | Builds and tests on at least two of these, as relevant to the language: GCC and Clang, x86_64 and aarch64, Linux and macOS, or several Python versions. No site-specific assumptions. |
| 3 | As 2, plus CI covers a second architecture or OS (aarch64 or macOS), the software runs unmodified on distributed HTC or HPC resources (for example OSG or batch farms), and accelerator support is provided where it is beneficial, or it is documented why it is not. |

**Typical actions.** Add a Clang job and an `ubuntu-24.04-arm` job to the CI matrix. Replace
site paths with configurable options. Document batch or OSG usage.
