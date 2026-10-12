"""Render the static GitHub Pages site from the passes in the repository."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from markdown_it import MarkdownIt
from markupsafe import Markup, escape

from .repo import Repo, scores
from .summary import summarize

LEVEL_NAMES = {0: "Absent", 1: "Initial", 2: "Established", 3: "Sustained", None: "Not applicable"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
EFFORT_ORDER = {"S": 0, "M": 1, "L": 2}
GH_BLOB_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+/(?:blob|tree)/[0-9a-f]{7,40}/(.+)$")

# Metrics shown on project pages: (section, key, label).
KEY_METRICS = [
    ("git", "commits_12m", "Commits, 12 months"),
    ("git", "authors_12m", "Active authors, 12 months"),
    ("git", "authors_24m", "Active authors, 24 months"),
    ("git", "new_authors_12m", "New authors, 12 months"),
    ("git", "bus_factor_50_24m", "Bus factor (50% of commits, 24 months)"),
    ("git", "top_author_share_24m", "Top author share of commits, 24 months"),
    ("git", "email_domains_24m", "Institutional e-mail domains, 24 months"),
    ("git", "first_parent_pr_fraction_12m", "Default-branch changes via PR, 12 months"),
    ("prs", "merged_12m", "PRs merged, 12 months"),
    ("prs", "reviewed_fraction_12m", "Merged PRs reviewed by non-author"),
    ("prs", "median_days_to_merge_12m", "Median days to merge"),
    ("prs", "test_touching_fraction_12m", "Merged PRs touching tests"),
    ("prs", "distinct_reviewers_12m", "Distinct reviewers, 12 months"),
    ("issues", "created_12m", "Issues opened, 12 months"),
    ("issues", "median_first_response_days_12m", "Median days to first response"),
    ("issues", "unanswered_fraction_12m", "Issues without response"),
    ("issues", "open_older_365d", "Open issues older than 1 year"),
    ("releases", "count_24m", "Releases, 24 months"),
    ("releases", "latest_tag", "Latest release"),
    ("ci", "default_branch_success_rate", "Default-branch CI success rate"),
    ("ci", "uses_eic_shell", "CI runs in eic-shell"),
    ("repo", "license_spdx", "License (SPDX)"),
    ("packaging", "in_eic_shell", "Ships in eic-shell"),
    ("packaging", "eic_shell_version", "eic-shell version"),
    ("code", "source_lines", "Source lines (excluding vendored)"),
    ("code", "test_files", "Test files"),
]


def _md() -> MarkdownIt:
    return MarkdownIt("commonmark", {"linkify": False, "html": False}).enable("table")


def evidence_html(ev: str) -> Markup:
    if ev.startswith("metrics:"):
        return Markup(f'<code class="metric">{escape(ev[len("metrics:"):])}</code>')
    url, _, note = ev.partition(" ")
    m = GH_BLOB_RE.match(url)
    label = m.group(1) if m else re.sub(r"^https?://(www\.)?", "", url)
    note = note.lstrip(" —-–:")
    out = f'<a href="{escape(url)}">{escape(label)}</a>'
    if note:
        out += f' <span class="muted">— {escape(note)}</span>'
    return Markup(out)


def fmt_metric(v) -> str:
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.0%}" if 0 <= v <= 1 else f"{v:.1f}"
    return str(v)


def level_class(level) -> str:
    return "lvl-na" if level is None else f"lvl-{level}"


def score_class(mean) -> str:
    return "lvl-na" if mean is None else f"lvl-{min(3, max(0, int(round(mean))))}"


def feedback_markdown(project: dict, a: dict, cats, pass_id: str, site_url: str) -> str:
    """An issue-ready action plan the project can paste into its own tracker."""
    lines = [
        f"# Sustainability action plan: {project['name']}",
        "",
        f"From the EIC Software Sustainability Review, pass `{pass_id}`, assessed at commit "
        f"`{a['commit'][:12]}`. Full assessment: {site_url.rstrip('/')}/projects/{project['id']}.html",
        "",
        "Levels: 0 Absent · 1 Initial · 2 Established · 3 Sustained. Each item names the step to the next level.",
        "",
    ]
    for prio in ("high", "medium", "low"):
        items = [
            (crit.id, act)
            for cat in cats for crit in cat.criteria if crit.id in a["criteria"]
            for act in a["criteria"][crit.id]["actions"] if act["priority"] == prio
        ]
        if not items:
            continue
        lines += [f"## {prio.capitalize()} priority", ""]
        for cid, act in sorted(items, key=lambda t: EFFORT_ORDER[t[1]["effort"]]):
            lvl = a["criteria"][cid]["level"]
            lines.append(f"- [ ] {act['action']} *(`{cid}`, now level {lvl}, effort {act['effort']})*")
        lines.append("")
    return "\n".join(lines)


def build(repo: Repo, out: str | Path) -> Path:
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / "projects").mkdir(parents=True)
    (out / "passes").mkdir()
    (out / "data").mkdir()

    env = Environment(loader=PackageLoader("ssr", "templates"), autoescape=select_autoescape(["html"]))
    md = _md()
    env.filters["md_inline"] = lambda s: Markup(md.renderInline(s or ""))
    env.filters["evidence"] = evidence_html
    env.filters["metric"] = fmt_metric
    env.filters["lvlclass"] = level_class
    env.filters["scoreclass"] = score_class
    env.filters["score"] = lambda x: "–" if x is None else f"{x:.1f}"
    env.globals["LEVEL_NAMES"] = LEVEL_NAMES

    cfg = repo.config["site"]
    cats = repo.categories()
    criteria = {c.id: c for c in repo.criteria()}
    projects = {p["id"]: p for p in repo.projects}
    common = dict(site=cfg, categories=cats, criteria=criteria)

    # Latest assessment per project.
    rows = []
    for pid, p in projects.items():
        hist = repo.history(pid)
        if not hist:
            rows.append({"project": p, "assessment": None, "scores": None, "pass": None, "history": []})
            continue
        pass_id, a = hist[-1]
        rows.append({
            "project": p,
            "assessment": a,
            "scores": scores(a, cats),
            "pass": pass_id,
            "metrics": repo.metrics(pass_id, pid) or {},
            "history": hist,
        })
    assessed = [r for r in rows if r["assessment"]]
    assessed.sort(key=lambda r: -(r["scores"]["overall"] or 0))
    unassessed = [r for r in rows if not r["assessment"]]

    def write(rel: str, template: str, root: str, **ctx) -> None:
        html = env.get_template(template).render(root=root, page=rel, **common, **ctx)
        (out / rel).write_text(html, encoding="utf-8")

    write("index.html", "index.html", "", rows=assessed, unassessed=unassessed,
          domains=sorted({p["domain"] for p in projects.values()}), pass_ids=repo.pass_ids())

    for r in assessed:
        p, a = r["project"], r["assessment"]
        actions = sorted(
            ({**act, "criterion": cid, "level": c["level"]}
             for cid, c in a["criteria"].items() for act in c["actions"]),
            key=lambda x: (PRIORITY_ORDER[x["priority"]], EFFORT_ORDER[x["effort"]], x["criterion"]),
        )
        metrics = r["metrics"]
        key_metrics = [(label, (metrics.get(sec) or {}).get(key), f"{sec}.{key}") for sec, key, label in KEY_METRICS]
        fb = feedback_markdown(p, a, cats, r["pass"], cfg["url"])
        (out / "projects" / f"{p['id']}.feedback.md").write_text(fb, encoding="utf-8")
        write(f"projects/{p['id']}.html", "project.html", "../", r=r, a=a, p=p, actions=actions,
              key_metrics=key_metrics, feedback=fb, history=r["history"],
              metrics_errors=metrics.get("errors") or [])

    # Rubrics page: method + every category with anchors per criterion.
    common_md = (repo.root / "rubrics" / "_common.md").read_text(encoding="utf-8")
    rubric_html = []
    for cat in cats:
        html = md.render(cat.body)
        html = re.sub(r"<h2><code>([\w.-]+)</code>", r'<h2 id="\1"><code>\1</code>', html)
        rubric_html.append((cat, Markup(html)))
    write("rubrics.html", "rubrics.html", "", common_html=Markup(md.render(common_md)), rubric_html=rubric_html)

    passes = []
    for pass_id in reversed(repo.pass_ids()):
        man = repo.manifest(pass_id)
        passes.append({"id": pass_id, "manifest": man})
        write(f"passes/{pass_id}.html", "pass.html", "../", pass_id=pass_id, manifest=man,
              summary_html=Markup(md.render(summarize(repo, pass_id))))
    write("passes.html", "passes.html", "", passes=passes)

    data = {
        "site": cfg,
        "scale": {str(k): v for k, v in LEVEL_NAMES.items() if k is not None},
        "categories": [{"id": c.id, "title": c.title, "criteria": [x.id for x in c.criteria]} for c in cats],
        "projects": [
            {
                "id": r["project"]["id"], "name": r["project"]["name"], "repo": r["project"]["repo"],
                "domain": r["project"]["domain"], "role": r["project"]["role"],
                "pass": r["pass"], "commit": r["assessment"]["commit"],
                "overall": r["scores"]["overall"], "categories": r["scores"]["categories"],
                "levels": {cid: c["level"] for cid, c in r["assessment"]["criteria"].items()},
            }
            for r in assessed
        ],
    }
    (out / "data" / "latest.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")

    static = Path(__file__).parent / "static"
    for f in static.iterdir():
        shutil.copy(f, out / f.name)
    (out / ".nojekyll").write_text("")
    return out
