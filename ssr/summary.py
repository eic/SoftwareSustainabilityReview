"""Markdown summary of a pass compared with each project's previous assessment (PR body)."""

from __future__ import annotations

from .repo import Repo, scores


def fmt(x: float | None) -> str:
    return "–" if x is None else f"{x:.2f}"


def delta(new: float | None, old: float | None) -> str:
    if new is None or old is None:
        return ""
    d = new - old
    return "" if abs(d) < 0.005 else f" ({d:+.2f})"


def summarize(repo: Repo, pass_id: str) -> str:
    cats = repo.categories()
    man = repo.manifest(pass_id)
    site = repo.config["site"]
    lines = [
        f"## Review pass `{pass_id}`",
        "",
        f"Assessor: `{(man.get('assessor') or {}).get('agent', '?')}` / `{(man.get('assessor') or {}).get('model', '?')}` · "
        f"rubrics at `{(man.get('rubrics_commit') or '?')[:12]}` · "
        f"stack snapshot `{(man.get('stack_snapshot') or '?')[:12]}`",
        "",
        "Scores are mean levels on the 0–3 scale; parentheses show the change from the project's previous assessment.",
        "",
        "| Project | Overall | " + " | ".join(c.title.split(" & ")[0].split(" ")[0] for c in cats) + " | Level changes |",
        "| --- | --- | " + " | ".join("---" for _ in cats) + " | --- |",
    ]
    changes_detail = []
    for pid in man.get("projects") or []:
        a = repo.assessment(pass_id, pid)
        if a is None:
            continue
        s = scores(a, cats)
        prev_id = repo.previous_pass_with(pid, pass_id)
        prev = repo.assessment(prev_id, pid) if prev_id else None
        ps = scores(prev, cats) if prev else {"overall": None, "categories": {}}
        changed = []
        if prev:
            for cid, c in a["criteria"].items():
                old = (prev["criteria"].get(cid) or {}).get("level", "new")
                if old != c["level"]:
                    changed.append(f"`{cid}` {old if old is not None else 'n/a'} → {c['level'] if c['level'] is not None else 'n/a'}")
        lines.append(
            f"| [{pid}]({site['url'].rstrip('/')}/projects/{pid}.html) | {fmt(s['overall'])}{delta(s['overall'], ps['overall'])} | "
            + " | ".join(fmt(s["categories"][c.id]) + delta(s["categories"][c.id], ps["categories"].get(c.id)) for c in cats)
            + f" | {len(changed) if prev else 'first assessment'} |"
        )
        if changed:
            changes_detail.append(f"- **{pid}** (vs `{prev_id}`): " + ", ".join(changed))
    if changes_detail:
        lines += ["", "### Level changes", "", *changes_detail]
    lines += [
        "",
        "### Reviewing this PR",
        "",
        "- Spot-check level changes against the cited evidence: every change must name what changed.",
        "- `ssr validate` has passed in CI; the site preview builds from this branch.",
    ]
    return "\n".join(lines) + "\n"
