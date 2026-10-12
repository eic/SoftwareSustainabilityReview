"""Consistency checks for projects.yaml, rubrics, and pass contents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import jsonschema

from .repo import PASS_ID_RE, PROJECT_ID_RE, Repo, load_json, load_yaml

DOMAINS = {"simulation", "reconstruction", "geometry", "data-model", "generator", "analysis", "infrastructure", "tooling"}
ROLES = {"core", "community"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
BLOB_RE = re.compile(r"https://github\.com/[^/]+/[^/]+/(blob|tree)/([^/]+)/")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def check_projects(repo: Repo, rep: Report) -> None:
    seen = set()
    for i, p in enumerate(repo.projects):
        where = f"projects.yaml[{i}]"
        pid = p.get("id", "")
        if not PROJECT_ID_RE.match(pid):
            rep.error(where, f"id {pid!r} is not kebab-case")
        if pid in seen:
            rep.error(where, f"duplicate id {pid!r}")
        seen.add(pid)
        for k in ("name", "repo", "domain", "role"):
            if not p.get(k):
                rep.error(where, f"missing {k}")
        if p.get("domain") and p["domain"] not in DOMAINS:
            rep.error(where, f"domain {p['domain']!r} not in {sorted(DOMAINS)}")
        if p.get("role") and p["role"] not in ROLES:
            rep.error(where, f"role {p['role']!r} not in {sorted(ROLES)}")
        if p.get("repo") and not re.match(r"^https://", p["repo"]):
            rep.error(where, "repo must be an https URL")
        unknown = set(p) - {"id", "name", "repo", "domain", "role", "packages", "subdir", "notes"}
        if unknown:
            rep.error(where, f"unknown fields {sorted(unknown)}")


def check_rubrics(repo: Repo, rep: Report) -> None:
    ids = set()
    cats = repo.categories()
    if not cats:
        rep.error("rubrics/", "no rubric files with front matter")
    for cat in cats:
        if not cat.criteria:
            rep.error(f"rubrics/{cat.file}", "declares no criteria")
        for c in cat.criteria:
            if c.id in ids:
                rep.error(f"rubrics/{cat.file}", f"duplicate criterion id {c.id}")
            ids.add(c.id)
            if f"`{c.id}`" not in cat.body:
                rep.error(f"rubrics/{cat.file}", f"criterion {c.id} has no section in the body")


def check_assessment(repo: Repo, pass_id: str, pid: str, rep: Report, schema: dict, criteria_ids: list[str]) -> None:
    where = f"passes/{pass_id}/{pid}.assessment.yaml"
    a = repo.assessment(pass_id, pid)
    try:
        jsonschema.validate(a, schema)
    except jsonschema.ValidationError as e:
        loc = "/".join(str(x) for x in e.absolute_path)
        rep.error(where, f"schema: {loc}: {e.message}")
        return
    if a["project"] != pid:
        rep.error(where, f"project {a['project']!r} does not match file name")
    if a["pass"] != pass_id:
        rep.error(where, f"pass {a['pass']!r} does not match directory")
    m = repo.metrics(pass_id, pid)
    if m is None:
        rep.error(where, "no matching metrics.json")
    elif (m.get("git") or {}).get("head_sha") and m["git"]["head_sha"] != a["commit"]:
        rep.error(where, f"commit {a['commit'][:12]} differs from metrics git.head_sha {m['git']['head_sha'][:12]}")

    crit = a["criteria"]
    missing = [c for c in criteria_ids if c not in crit]
    extra = [c for c in crit if c not in criteria_ids]
    if missing:
        rep.error(where, f"missing criteria {missing}")
    if extra:
        rep.error(where, f"unknown criteria {extra}")
    for cid, c in crit.items():
        w = f"{where} {cid}"
        lvl = c["level"]
        if lvl is None:
            if not c.get("not_applicable"):
                rep.error(w, "level null requires not_applicable")
            continue
        if c.get("not_applicable"):
            rep.error(w, "not_applicable set but level is not null")
        if lvl > 0 and not c["evidence"]:
            rep.error(w, f"level {lvl} requires evidence")
        if lvl < 3 and not c["gaps"]:
            rep.error(w, f"level {lvl} requires gaps for the next level")
        if lvl < 3 and not c["actions"]:
            rep.error(w, f"level {lvl} requires actions")
        for ev in c["evidence"]:
            if not (ev.startswith("http") or ev.startswith("metrics:")):
                rep.error(w, f"evidence must be a URL or metrics:<key>: {ev[:60]!r}")
            b = BLOB_RE.match(ev)
            if b and not re.fullmatch(r"[0-9a-f]{40}", b.group(2)):
                rep.warn(w, f"permalink not pinned to a commit: {ev[:100]}")

    text = repo.assessment_path(pass_id, pid).read_text()
    for email in EMAIL_RE.findall(text):
        if not email.endswith("anthropic.com"):
            rep.error(where, "contains an e-mail address; assessments must not identify individuals")
            break


def check_pass(repo: Repo, pass_id: str, rep: Report) -> None:
    where = f"passes/{pass_id}"
    if not PASS_ID_RE.match(pass_id):
        rep.error(where, "pass id must be YYYY-MM-DD or YYYY-MM-DD-N")
    d = repo.passes_dir / pass_id
    man = repo.manifest(pass_id)
    if not man:
        rep.error(where, "missing manifest.yaml")
    elif man.get("pass") != pass_id:
        rep.error(f"{where}/manifest.yaml", "pass does not match directory")
    known = {p["id"] for p in repo.projects}
    schema = load_json(repo.root / "schema" / "assessment.schema.json")
    criteria_ids = [c.id for c in repo.criteria()]
    assessed = sorted(f.name.removesuffix(".assessment.yaml") for f in d.glob("*.assessment.yaml"))
    measured = sorted(f.name.removesuffix(".metrics.json") for f in d.glob("*.metrics.json"))
    for pid in sorted(set(assessed) | set(measured)):
        if pid not in known:
            rep.error(where, f"{pid} is not in projects.yaml")
    for pid in measured:
        if pid not in assessed:
            rep.warn(where, f"{pid} has metrics but no assessment")
    for pid in assessed:
        if pid in known:
            check_assessment(repo, pass_id, pid, rep, schema, criteria_ids)
    if man and sorted(man.get("projects") or []) != assessed:
        rep.warn(f"{where}/manifest.yaml", "projects list differs from the assessments present")


def validate(repo: Repo, passes: list[str] | None = None) -> Report:
    rep = Report()
    check_projects(repo, rep)
    check_rubrics(repo, rep)
    load_yaml(repo.root / "reference" / "eic-supported-components.yaml")
    for pass_id in passes if passes is not None else repo.pass_ids():
        check_pass(repo, pass_id, rep)
    return rep
