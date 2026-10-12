---
id: community
title: Community & governance
order: 3
criteria:
  - id: com.responsiveness
    title: Issue & PR responsiveness
  - id: com.contributors
    title: Contributor base
  - id: com.bus-factor
    title: Knowledge concentration (bus factor)
  - id: com.governance
    title: Governance & roadmap
  - id: com.conduct
    title: Code of conduct & user support
---

# Community & governance

Would the project survive the departure of its main developer, and does it respond to its users?
EIC principle 7 requires that "mission critical software components are not dependent on the
expertise of a single developer, but managed and maintained by a core group". Principle 1
commits to a diverse workforce and an inclusive environment.

The contributor metrics count commit authors and reviewers after excluding bots. The collector
stores only aggregate counts, never names or e-mail addresses, and these assessments must do the
same. Do not name individuals. Refer to roles ("the top author") instead.

## `com.responsiveness` — Issue & PR responsiveness

**Question.** Do users and contributors get timely responses, and is the issue tracker
organized?

**Check.** `metrics:issues.*` and `metrics:prs.*`, especially
`issues.median_first_response_days_12m`, `issues.unanswered_fraction_12m`,
`issues.open_older_365d`, `issues.labeled_fraction_12m`, and `prs.median_days_to_merge_12m`. When
fewer than 5 issues were opened in 12 months, judge from what exists and set `confidence: low`.

| Level | Anchor |
| --- | --- |
| 0 | Issues are disabled with no documented alternative, the majority of issues opened in 12 months received no response, or there were no commits in 12 months while issues are open. |
| 1 | Median first response is longer than 14 days, or more than half of open issues are older than one year. |
| 2 | Median first response is 7 days or less, the majority of new issues are labeled or otherwise triaged, and contributor PRs receive reviews. |
| 3 | Median first response is 2 days or less, fewer than 25% of open issues are older than one year, and the triage process is documented (labels, milestones, or project board). |

**Typical actions.** Adopt a label scheme and triage new issues weekly. Close or label stale issues
older than one year. Document the triage rota.

## `com.contributors` — Contributor base

**Question.** How many people actively develop the project, from how many institutions, and does
it attract contributors from outside the core group?

**Check.** `metrics:git.authors_12m`, `git.authors_24m`, `git.new_authors_12m`,
`git.email_domains_24m` (distinct institutional e-mail domains, a proxy for institutions), and
`prs.external_fraction_12m`. Institutional affiliation can also be documented in the README,
AUTHORS, or CODEOWNERS.

| Level | Anchor |
| --- | --- |
| 0 | At most one active author in 24 months, or no commits in 24 months. |
| 1 | 2 or 3 active authors in 24 months, or all contributions come from a single institution or group. |
| 2 | At least 4 active authors in 24 months from at least 2 institutions, and external PRs have been merged. |
| 3 | At least 10 active authors in 24 months from at least 3 institutions, new authors in the last 12 months, and at least 20% of merged PRs from contributors outside the maintainer group. |

**Typical actions.** Present the project at an ePIC software meeting and recruit a co-developer from
another institution. Label newcomer issues. Merge or close external PRs promptly.

## `com.bus-factor` — Knowledge concentration (bus factor)

**Question.** Is knowledge of the code, review, and releases spread across several people?

**Check.** `metrics:git.bus_factor_50_24m` (the smallest number of authors who together wrote 50%
of non-bot commits in 24 months), `git.top_author_share_24m`, `prs.distinct_reviewers_12m`,
`prs.top_reviewer_share_12m`, `prs.distinct_mergers_12m`, `releases.authors_24m`, and
`files.codeowners`.

| Level | Anchor |
| --- | --- |
| 0 | One person wrote at least 80% of commits in 24 months and nobody else reviews or merges. |
| 1 | One person wrote at least 50% of commits, but others review or merge changes. |
| 2 | Bus factor (50%) of at least 2, at least 2 people review and merge, and a maintainer list or CODEOWNERS names at least 2 people. |
| 3 | Bus factor (50%) of at least 3, every major component has at least 2 named owners, maintainers span at least 2 institutions, and releases were made by at least 2 different people in 24 months (or the release procedure is documented and automated). |

**Typical actions.** Add `CODEOWNERS` with two owners per directory. Document the release procedure
in `RELEASING.md` and have a second maintainer cut the next release. Rotate reviews.

## `com.governance` — Governance & roadmap

**Question.** Is it publicly visible who decides, how decisions are made, how one becomes a
maintainer, and where the project is heading?

**Check.** GOVERNANCE, README, CONTRIBUTING, milestones, project boards, roadmap documents, links to
public meeting notes, and documented ownership within the ePIC software organization (working
group or computing structures).

| Level | Anchor |
| --- | --- |
| 0 | No documented governance and no visible decision-making. |
| 1 | Maintainers can be identified (README or CODEOWNERS), but there is no documented decision process or maintainer path. |
| 2 | Governance is documented (who decides, how to become a reviewer or maintainer) and decisions are made publicly (issues, discussions, or linked meeting notes). |
| 3 | As 2, plus a public roadmap or milestones that are kept up to date, ownership mapped to the EIC or ePIC organization, and a succession process. |

**Typical actions.** Add `GOVERNANCE.md` naming the maintainers, the decision process, and the path
to maintainership. Keep GitHub milestones for the next two releases. Link meeting minutes.

## `com.conduct` — Code of conduct & user support

**Question.** Does a code of conduct with a reporting route apply, and do users have a documented
place to get help?

**Check.** `metrics:community.files.code_of_conduct` (including any inherited from the
organization), and links to support channels (GitHub Discussions, Mattermost, mailing lists,
help desks) and to training material.

| Level | Anchor |
| --- | --- |
| 0 | No code of conduct and no documented support channel. |
| 1 | Either a code of conduct or a support channel is documented, but not both, or the code of conduct has no reporting contact. |
| 2 | A code of conduct with a reporting contact applies (repository, organization, or a linked collaboration code), and a support channel is documented. |
| 3 | As 2, plus an enforcement procedure is documented and the support channel is visibly active (questions answered in the last 6 months), or training or tutorial sessions are provided. |

**Typical actions.** Add `CODE_OF_CONDUCT.md` (Contributor Covenant) with a reporting contact, or
link the collaboration code. Add a "Getting help" section that links the support channel.
