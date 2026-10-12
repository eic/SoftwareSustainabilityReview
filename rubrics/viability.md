---
id: viability
title: Impact & long-term viability
order: 6
criteria:
  - id: via.license
    title: Licensing
  - id: via.citation
    title: Citation & attribution
  - id: via.adoption
    title: Adoption & downstream use
  - id: via.support
    title: Institutional backing & continuity
---

# Impact & long-term viability

Is the project legally reusable, creditable, used, and backed by people and institutions who will
still be around? EIC principle 7 says "EIC software will be open source with attribution to its
contributors". It also commits to supporting the careers of scientists who develop software.

## `via.license` — Licensing

**Question.** Is a standard open-source license applied unambiguously and compatibly with the
project's dependencies?

**Check.** `metrics:repo.license_spdx`, LICENSE files, license headers, package metadata, and
compatibility with the licenses of linked dependencies (for example GPL code linked into a library
distributed under LGPL or Apache).

| Level | Anchor |
| --- | --- |
| 0 | No license (all rights reserved), or the license is not OSI-approved. |
| 1 | An OSI-approved license is present, but it is not machine-detectable (no recognized SPDX identifier), licensing is inconsistent across files, or it is incompatible with a dependency. |
| 2 | A single, recognized OSI-approved license (SPDX identifier detected), compatible with the dependencies and stated in the package metadata. |
| 3 | As 2, plus SPDX headers in source files or REUSE compliance, recorded licenses of any third-party code, and documented contribution terms (inbound = outbound, or DCO). |

**Typical actions.** Add a `LICENSE` file with the standard text so GitHub detects the SPDX
identifier. Add `SPDX-License-Identifier` headers. Add the REUSE lint to CI.

## `via.citation` — Citation & attribution

**Question.** Can users cite the software, and are its contributors credited?

**Check.** `metrics:files.citation_cff`, `zenodo_json`, `codemeta`, and `authors`; Zenodo DOI
badges or links; and publications.

| Level | Anchor |
| --- | --- |
| 0 | No citation information. |
| 1 | The README asks users to cite a paper or gives BibTeX, but there is no machine-readable software metadata. |
| 2 | A valid `CITATION.cff` or a software DOI (Zenodo concept DOI) exists, and an author or contributor list is maintained. |
| 3 | As 2, plus a DOI for every release (Zenodo–GitHub integration), citation metadata updated with each release, all significant contributors credited, and a reference publication or software paper. |

**Typical actions.** Add `CITATION.cff`. Enable the Zenodo–GitHub integration so each release gets a
DOI. Add `.zenodo.json` with the full author list.

## `via.adoption` — Adoption & downstream use

**Question.** Is there evidence that people beyond the authors use the software, within EIC and
beyond?

**Check.** `metrics:packaging.in_eic_shell`, `metrics:eic.eic_spack_dependents`, use in EIC
repositories (benchmarks, simulation campaigns, tutorials, EICrecon or epic), and use by other
experiments. Search with `gh search code` where necessary and cite the hits. Stars and forks are
weak evidence and are not sufficient on their own.

| Level | Anchor |
| --- | --- |
| 0 | No evidence of use beyond the authors. |
| 1 | Used by a single analysis or group, or referenced only in talks or tutorials. |
| 2 | Used by several groups within EIC or ePIC: a dependency of another EIC repository, or used in benchmarks or simulation campaigns. |
| 3 | Part of the EIC production chain (simulation campaigns, reconstruction, shipped in eic-shell) or used by projects outside EIC. |

**Typical actions.** Add the project to eic-shell. Contribute a benchmark that uses it to
[physics_benchmarks](https://github.com/eic/physics_benchmarks) or
[detector_benchmarks](https://github.com/eic/detector_benchmarks). List known users in the README.

## `via.support` — Institutional backing & continuity

**Question.** Is continued maintenance backed by named institutions, roles, or funding, rather than
depending on one person's goodwill or one temporary position?

**Check.** Maintainer affiliations, funding acknowledgements, ownership by an EIC or ePIC body
(working group, computing and software structure), and documented succession. Public evidence only.

| Level | Anchor |
| --- | --- |
| 0 | No identifiable maintainers or affiliations, or no activity in 12 months. |
| 1 | Maintainers have identifiable affiliations but no stated institutional commitment, or maintenance depends on a single fixed-term position. |
| 2 | Maintenance responsibility is assigned within the EIC or ePIC structure, or funding or institutional support is acknowledged in the README or documentation. |
| 3 | As 2, plus a documented multi-institution maintenance commitment and a succession or transition plan. |

**Typical actions.** State the owning ePIC working group and the maintainers' institutions in the
README. Add a funding acknowledgement. Document what happens when a maintainer leaves.
