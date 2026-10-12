# Running and reviewing passes

## Running a pass

### Locally, with Claude Code

From a clone of this repository, with `gh` authenticated:

```
claude "/review-pass"
claude "/review-pass for eicrecon and epic only"
```

The [`review-pass` skill](.claude/skills/review-pass/SKILL.md) creates the branch, collects metrics,
runs one assessor subagent per project, validates and cross-calibrates the results, and opens the
PR. Other agents can follow the same file. It is written as a plain procedure.

### In GitHub Actions

Run the `review-pass` workflow (Actions → review-pass → Run workflow), optionally with a subset of
project ids. It needs the `ANTHROPIC_API_KEY` secret. A `REVIEW_PASS_TOKEN` secret (GitHub App
token or fine-grained PAT with contents and pull-requests write) is recommended, so that CI runs on
the PR it opens. A quarterly schedule is prepared in the workflow and commented out.

### By hand (the steps the skill automates)

```bash
PASS=$(date +%F)
git switch -c pass/$PASS
uv run ssr refresh-stack
uv run ssr new-pass $PASS --model <assessor-model-id> --agent <agent>
uv run ssr collect $PASS
uv run ssr brief $PASS <project>      # the prompt for each project's assessor
uv run ssr validate $PASS --strict
uv run ssr calibrate $PASS            # compare levels across projects, criterion by criterion
uv run ssr summarize $PASS            # PR description
```

## Reviewing a pass PR

The PR description lists each project's category scores and every level change since that project's
previous assessment. CI validates the files and attaches a site preview (artifact `site-preview`).
A reviewer should:

1. **Check level changes.** Each one must cite the evidence that changed (or a rubric change). A
   change without new evidence is grading drift. Ask for it to be reverted.
2. **Spot-check evidence.** Open a few cited permalinks and metrics per project. A citation that
   does not show what the rationale claims is a defect.
3. **Check the actions.** They must be concrete, aimed at the next level, and realistic for the
   project. Vague actions ("improve documentation") are defects.
4. **Check tone and privacy.** No praise, no individuals named, no e-mail addresses (the latter is
   also enforced by `ssr validate`).

Corrections can be pushed directly to the pass branch. Merge when satisfied. The site deploys from
`main`.

## Delivering feedback to projects

Each project page has an action plan, downloadable as a Markdown checklist
(`projects/<id>.feedback.md` on the site). Sharing it with the project, for example as an issue in
its repository, is a human decision and is never automated.

## Changing the project list

Edit [`projects.yaml`](projects.yaml) in a normal PR. Never change an existing `id`. New projects
are picked up by the next pass. To assess one immediately, run a pass limited to it.

## Changing the rubrics

Rubrics are human-owned and change only in PRs that contain nothing else.

- The criterion list lives in each rubric file's front matter. `ssr validate` checks that each
  declared criterion has a section, and that assessments cover exactly the declared criteria.
- After a material change to anchors, run a full pass. Assessors may change levels because of the
  rubric change and must say so. The pass manifest records the rubric commit, so earlier passes
  remain interpretable.
- Keep anchors observable: every level condition should be checkable from public data by someone
  who has never met the project's developers.
