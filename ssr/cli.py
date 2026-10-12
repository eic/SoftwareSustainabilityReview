"""`ssr` command-line interface."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

from . import __version__
from .repo import PASS_ID_RE, Repo, find_root
from .shell import run


def _repo() -> Repo:
    return Repo(find_root())


def _git_head(repo: Repo) -> str | None:
    try:
        return run(["git", "-C", str(repo.root), "rev-parse", "HEAD"]).strip()
    except Exception:
        return None


def cmd_new_pass(args) -> int:
    repo = _repo()
    pass_id = args.pass_id or dt.date.today().isoformat()
    if not PASS_ID_RE.match(pass_id):
        sys.exit("pass id must be YYYY-MM-DD or YYYY-MM-DD-N")
    d = repo.passes_dir / pass_id
    if d.exists():
        sys.exit(f"passes/{pass_id} already exists; use a suffix such as {pass_id}-2")
    ids = args.project or [p["id"] for p in repo.projects]
    for pid in ids:
        repo.project(pid)
    from .stack import load_snapshot

    snap = load_snapshot(repo)
    manifest = {
        "pass": pass_id,
        "started": dt.date.today().isoformat(),
        "rubrics_commit": _git_head(repo),
        "collector_version": __version__,
        "stack_snapshot": (snap.get("source") or {}).get("commit"),
        "assessor": {"agent": args.agent, "model": args.model},
        "projects": sorted(ids),
        "notes": args.notes or "",
    }
    d.mkdir(parents=True)
    (d / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print(f"created passes/{pass_id}/manifest.yaml for {len(ids)} projects")
    return 0


def cmd_refresh_stack(args) -> int:
    from .stack import write_snapshot

    write_snapshot(_repo())
    return 0


def cmd_collect(args) -> int:
    from .collect import Collector

    repo = _repo()
    man = repo.manifest(args.pass_id)
    if not man:
        sys.exit(f"passes/{args.pass_id}/manifest.yaml not found; run `ssr new-pass` first")
    ids = args.project or man["projects"]
    col = Collector(repo)
    col._eic_spack_dir()  # clone once before the threads start

    def one(pid: str) -> tuple[str, list[str]]:
        m = col.collect(repo.project(pid), args.pass_id)
        repo.metrics_path(args.pass_id, pid).write_text(json.dumps(m, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return pid, m["errors"]

    failed = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(one, pid): pid for pid in ids}
        for f in as_completed(futs):
            pid = futs[f]
            try:
                _, errs = f.result()
                print(f"{pid}: ok" + (f" ({len(errs)} section errors: {'; '.join(errs)})" if errs else ""))
            except Exception as e:  # report and continue with the other projects
                failed += 1
                print(f"{pid}: FAILED: {e}", file=sys.stderr)
    return 1 if failed else 0


def cmd_path(args) -> int:
    from .collect import checkout_dir

    repo = _repo()
    print(checkout_dir(repo, repo.project(args.project)))
    return 0


BRIEF = """\
You are assessing the sustainability of the project `{pid}` ({name}, {repo}) for review pass `{pass_id}`.

Follow the protocol in `rubrics/_common.md` exactly, then apply every rubric file listed below. Work in the review
repository at `{root}`.

Inputs:
- Rubrics: `rubrics/_common.md`, then {rubric_files}.
- Metrics (runner-verified ground truth): `passes/{pass_id}/{pid}.metrics.json`.
- Checkout of the project at commit `{sha}`: `{checkout}`. It is read-only: do not modify, build, or run anything in it.
- EIC stack reference: `reference/eic-supported-components.yaml` and `reference/eic-stack-snapshot.yaml`.
- Previous assessment: {previous}
- Public GitHub data through `gh` (read-only: `gh api`, `gh search`, `gh issue list`, `gh pr list`, `gh release list`).
  Never create, comment on, or edit anything on GitHub. Code search (`gh search code`) is rate-limited to about
  10 requests per minute, shared with any assessors running in parallel: on a rate-limit error, wait 60 seconds
  and retry rather than skipping the search.
{notes}
Output: write `passes/{pass_id}/{pid}.assessment.yaml` with `commit: {sha}`, `pass: {pass_id}`, and
`assessor: {{agent: {agent}, model: {model}}}`. Then run `uv run ssr validate {pass_id}` and fix every error and
warning that concerns your file. Do not edit any other file.

Reply with one line: the project id and its level per criterion, in rubric order.
"""


def cmd_brief(args) -> int:
    from .collect import checkout_dir

    repo = _repo()
    p = repo.project(args.project)
    man = repo.manifest(args.pass_id)
    m = repo.metrics(args.pass_id, args.project)
    if not m:
        sys.exit(f"no metrics for {args.project} in pass {args.pass_id}; run `ssr collect` first")
    prev = repo.previous_pass_with(args.project, args.pass_id)
    print(BRIEF.format(
        pid=p["id"], name=p["name"], repo=p["repo"], pass_id=args.pass_id, root=repo.root,
        rubric_files=", ".join(f"`rubrics/{c.file}`" for c in repo.categories()),
        sha=(m.get("git") or {}).get("head_sha"), checkout=checkout_dir(repo, p),
        previous=f"`passes/{prev}/{p['id']}.assessment.yaml` (apply objectivity rule 4)" if prev else "none (first assessment).",
        notes=f"- Assessor notes from projects.yaml: {p['notes']}\n" if p.get("notes") else "",
        agent=(man.get("assessor") or {}).get("agent"), model=(man.get("assessor") or {}).get("model"),
    ))
    return 0


def cmd_calibrate(args) -> int:
    """Per criterion, every project's level and rationale side by side, to spot inconsistent grading."""
    repo = _repo()
    man = repo.manifest(args.pass_id)
    assessments = {pid: repo.assessment(args.pass_id, pid) for pid in man.get("projects") or []}
    assessments = {k: v for k, v in assessments.items() if v}
    for c in repo.criteria():
        if args.criterion and c.id not in args.criterion:
            continue
        print(f"\n## {c.id} — {c.title}")
        rows = sorted(assessments.items(), key=lambda kv: (kv[1]["criteria"].get(c.id, {}).get("level") is None,
                                                          kv[1]["criteria"].get(c.id, {}).get("level") or 0))
        for pid, a in rows:
            x = a["criteria"].get(c.id) or {}
            lvl = "–" if x.get("level") is None else x["level"]
            print(f"  {lvl}  {pid:<20} {' '.join((x.get('rationale') or '').split())[:160]}")
    return 0


def cmd_validate(args) -> int:
    from .validate import validate

    rep = validate(_repo(), [args.pass_id] if args.pass_id else None)
    for w in rep.warnings:
        print(f"warning: {w}")
    for e in rep.errors:
        print(f"error: {e}")
    bad = rep.errors or (args.strict and rep.warnings)
    print(f"{len(rep.errors)} errors, {len(rep.warnings)} warnings")
    return 1 if bad else 0


def cmd_summarize(args) -> int:
    from .summary import summarize

    sys.stdout.write(summarize(_repo(), args.pass_id))
    return 0


def cmd_build_site(args) -> int:
    from .site import build

    out = build(_repo(), args.out)
    print(f"site written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ssr", description="EIC Software Sustainability Review tooling")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new-pass", help="create passes/<id>/manifest.yaml")
    p.add_argument("pass_id", nargs="?", help="default: today (YYYY-MM-DD)")
    p.add_argument("--project", action="append", help="limit to these project ids (repeatable)")
    p.add_argument("--agent", default="claude-code")
    p.add_argument("--model", required=True, help="exact model id of the assessor")
    p.add_argument("--notes")
    p.set_defaults(fn=cmd_new_pass)

    p = sub.add_parser("refresh-stack", help="regenerate reference/eic-stack-snapshot.yaml from eic/containers")
    p.set_defaults(fn=cmd_refresh_stack)

    p = sub.add_parser("collect", help="collect metrics for a pass")
    p.add_argument("pass_id")
    p.add_argument("--project", action="append", help="limit to these project ids (repeatable)")
    p.add_argument("-j", "--jobs", type=int, default=4)
    p.set_defaults(fn=cmd_collect)

    p = sub.add_parser("path", help="print the local checkout path of a project")
    p.add_argument("project")
    p.set_defaults(fn=cmd_path)

    p = sub.add_parser("brief", help="print the assessor prompt for one project in a pass")
    p.add_argument("pass_id")
    p.add_argument("project")
    p.set_defaults(fn=cmd_brief)

    p = sub.add_parser("calibrate", help="per-criterion levels across projects, to check consistency")
    p.add_argument("pass_id")
    p.add_argument("--criterion", action="append", help="limit to these criterion ids (repeatable)")
    p.set_defaults(fn=cmd_calibrate)

    p = sub.add_parser("validate", help="check projects, rubrics, and passes")
    p.add_argument("pass_id", nargs="?", help="only this pass (default: all)")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("summarize", help="markdown summary of a pass (for the PR body)")
    p.add_argument("pass_id")
    p.set_defaults(fn=cmd_summarize)

    p = sub.add_parser("build-site", help="render the GitHub Pages site")
    p.add_argument("--out", default="_site")
    p.set_defaults(fn=cmd_build_site)

    args = ap.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
