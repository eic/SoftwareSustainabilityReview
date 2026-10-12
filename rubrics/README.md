# Sustainability rubrics

Each file here is one assessment category. An assessment of one project applies every category.
The assessor's full prompt is [`_common.md`](_common.md) (the shared protocol: inputs, objectivity
rules, levels, evidence, actions, and output format) followed by each category file.

Each category file starts with YAML front matter that declares its criteria. The validator and the
site read that list, so **the front matter is the single source of truth for criterion ids**.
Adding, renaming, or removing a criterion is a rubric change. See "Changing rubrics" below.

## Scale

Every criterion is scored 0–3: **0 Absent · 1 Initial · 2 Established · 3 Sustained**. Each
category file gives concrete anchors per criterion. A level counts only when *all* of its
conditions (and those of the levels below) are met. Only public evidence counts.

## Categories

| Category | File | Criteria |
| --- | --- | --- |
| Code health & engineering practices | [`engineering.md`](engineering.md) | `eng.change-control`, `eng.ci`, `eng.testing`, `eng.static-quality`, `eng.modularity` |
| Documentation & usability | [`documentation.md`](documentation.md) | `doc.user`, `doc.developer`, `doc.contributing` |
| Community & governance | [`community.md`](community.md) | `com.responsiveness`, `com.contributors`, `com.bus-factor`, `com.governance`, `com.conduct` |
| Infrastructure & distribution | [`distribution.md`](distribution.md) | `dist.packaging`, `dist.releases`, `dist.dependencies`, `dist.reproducibility`, `dist.portability` |
| EIC ecosystem integration | [`eic-integration.md`](eic-integration.md) | `eic.reuse`, `eic.data-model`, `eic.environment`, `eic.currency` |
| Impact & long-term viability | [`viability.md`](viability.md) | `via.license`, `via.citation`, `via.adoption`, `via.support` |

## Aggregation

- **Category score** is the mean level of the category's applicable criteria. Criteria with
  `level: null` are excluded.
- **Overall score** is the unweighted mean of the category scores.
- The site always shows the per-criterion levels next to any aggregate, because the aggregates
  hide where the gaps are.

## Changing rubrics

Rubrics are human-owned. Changes go through a normal PR that a human reviews, separate from any
review pass. When a criterion's anchors change materially, the next pass re-assesses that criterion
for every project, and the pass manifest records the rubric commit, so comparisons across passes
remain interpretable.
