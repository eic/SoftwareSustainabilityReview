---
name: review-pass
description: Run a sustainability review pass. Collect metrics for the projects in projects.yaml, assess each project against the rubrics, validate the results, and open a pull request. Use when asked to run, start, or refresh a review pass, to (re)assess one or more projects, or to update the published assessments.
---

# Run a sustainability review pass

A pass produces `passes/<pass-id>/` (one manifest, plus a `metrics.json` and an
`assessment.yaml` per project) and delivers it as **one pull request**. Humans review and merge
the PR. Merging publishes the site.

Run every command from the repository root. `ssr` is this repository's CLI. Run it as
`uv run ssr ...`.

## Ground rules

- A pass PR adds `passes/<pass-id>/` and may refresh `reference/eic-stack-snapshot.yaml`.
  **Nothing else.** Never edit `rubrics/`, `projects.yaml`, `ssr/`, or earlier passes in a pass
  PR. If a rubric looks wrong, finish the pass and mention the problem in the PR description.
- Read-only toward the assessed projects. Do not open issues, comment, or push anywhere except
  this repository's pass branch. Whether and how feedback reaches a project is a human decision.
- Assessments follow `rubrics/_common.md`: public evidence only, literal anchors, no praise,
  no individuals named.

## Steps

1. **Preflight.** `gh auth status` succeeds, `git status` is clean, and you are on an up-to-date
   `main`. Settle on:
   - `PASS`: today's date `YYYY-MM-DD`. If `passes/$PASS` exists, append `-2`, `-3`, and so on.
   - Scope: all projects, unless the request names a subset. Use their ids from `projects.yaml`.
   - `MODEL`: your own exact model id (for example `claude-opus-5-5`), and `AGENT` (for example
     `claude-code`).

2. **Branch.** `git switch -c pass/$PASS`

3. **Refresh the stack snapshot.** `uv run ssr refresh-stack`

4. **Create the manifest.**
   `uv run ssr new-pass $PASS --model $MODEL --agent $AGENT [--project <id> ...]`

5. **Collect metrics.** `uv run ssr collect $PASS` (add `--project <id>` to retry one project).
   Section errors such as `prs: ...` are recorded in the metrics file and are acceptable. A
   project that `FAILED` entirely: retry it once. If it still fails, remove it from `projects:` in
   the manifest, record why in `notes:`, and delete any partial files for it.

6. **Assess each project.** For each project id, get its self-contained brief:

   ```bash
   uv run ssr brief $PASS <id>
   ```

   Give each brief verbatim to its own subagent (Agent tool, `general-purpose`), with up to 4
   running at once. Each subagent writes `passes/$PASS/<id>.assessment.yaml` and validates it. If
   subagents are not available, follow the briefs yourself, one project at a time, starting a fresh
   reading of the rubrics for each.

7. **Validate.** `uv run ssr validate $PASS --strict`. Fix every error and warning. Return the
   file to its subagent with the validator output, or fix purely mechanical problems such as YAML
   syntax or unpinned permalinks yourself.

8. **Calibrate across projects.** `uv run ssr calibrate $PASS`. For each criterion, read the
   levels and rationales side by side:
   - Two projects with equivalent evidence but different levels: re-check both against the anchors
     and correct the wrong one.
   - A level change against the previous pass whose rationale does not name the changed evidence:
     correct it.
   - A level above 0 with no evidence, or praise and adjectives in a rationale: rewrite it.
   Re-run step 7 after any change.

9. **Build the site.** `uv run ssr build-site --out _site` must succeed. `_site/` is not committed.

10. **Commit and open the PR.**

    ```bash
    git add passes/$PASS reference/eic-stack-snapshot.yaml
    git commit -m "Review pass $PASS"
    git push -u origin pass/$PASS
    uv run ssr summarize $PASS > /tmp/pass-$PASS.md
    gh pr create --title "Review pass $PASS" --body-file /tmp/pass-$PASS.md
    ```

    Add any notes (projects that could not be collected, rubric problems you noticed) to the PR
    description under a `### Notes` heading. Report the PR URL.

## Re-assessing after a rubric change

When a merged PR changed a rubric, run a pass over all projects, as above. Objectivity rule 4
allows level changes caused by the rubric change. The rationale must say "rubric change".
