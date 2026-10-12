"""Loading the review repository's own data: config, projects, rubrics, passes."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PASS_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(-\d+)?$")
PROJECT_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def find_root(start: Path | None = None) -> Path:
    """The review repository root: the nearest ancestor holding projects.yaml and rubrics/."""
    env = os.environ.get("SSR_ROOT")
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / "projects.yaml").is_file() and (d / "rubrics").is_dir():
            return d
    raise SystemExit("ssr: not inside a review repository (no projects.yaml + rubrics/ found)")


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps dates as strings (pass ids such as 2026-10-12 are identifiers)."""


_Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Criterion:
    id: str
    title: str
    category: str


@dataclass
class Category:
    id: str
    title: str
    order: int
    file: str
    body: str
    criteria: list[Criterion] = field(default_factory=list)


@dataclass
class Repo:
    root: Path

    @property
    def config(self) -> dict:
        return load_yaml(self.root / "config.yaml")

    @property
    def projects(self) -> list[dict]:
        return load_yaml(self.root / "projects.yaml")["projects"]

    def project(self, pid: str) -> dict:
        for p in self.projects:
            if p["id"] == pid:
                return p
        raise SystemExit(f"ssr: unknown project id {pid!r}")

    @property
    def cache_dir(self) -> Path:
        return Path(os.path.expanduser(self.config["collect"]["cache_dir"]))

    def categories(self) -> list[Category]:
        cats = []
        for path in sorted((self.root / "rubrics").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            m = FRONT_MATTER_RE.match(text)
            if not m:
                continue  # README.md, _common.md
            meta = yaml.safe_load(m.group(1))
            cat = Category(
                id=meta["id"],
                title=meta["title"],
                order=int(meta["order"]),
                file=path.name,
                body=text[m.end():],
            )
            cat.criteria = [Criterion(c["id"], c["title"], cat.id) for c in meta["criteria"]]
            cats.append(cat)
        return sorted(cats, key=lambda c: c.order)

    def criteria(self) -> list[Criterion]:
        return [c for cat in self.categories() for c in cat.criteria]

    # --- passes -------------------------------------------------------------------------

    @property
    def passes_dir(self) -> Path:
        return self.root / "passes"

    def pass_ids(self) -> list[str]:
        if not self.passes_dir.is_dir():
            return []
        return sorted(d.name for d in self.passes_dir.iterdir() if d.is_dir() and PASS_ID_RE.match(d.name))

    def manifest(self, pass_id: str) -> dict:
        path = self.passes_dir / pass_id / "manifest.yaml"
        return load_yaml(path) if path.is_file() else {}

    def assessment_path(self, pass_id: str, pid: str) -> Path:
        return self.passes_dir / pass_id / f"{pid}.assessment.yaml"

    def metrics_path(self, pass_id: str, pid: str) -> Path:
        return self.passes_dir / pass_id / f"{pid}.metrics.json"

    def assessment(self, pass_id: str, pid: str) -> dict | None:
        p = self.assessment_path(pass_id, pid)
        return load_yaml(p) if p.is_file() else None

    def metrics(self, pass_id: str, pid: str) -> dict | None:
        p = self.metrics_path(pass_id, pid)
        return load_json(p) if p.is_file() else None

    def history(self, pid: str) -> list[tuple[str, dict]]:
        """All (pass_id, assessment) for a project, oldest first."""
        out = []
        for pass_id in self.pass_ids():
            a = self.assessment(pass_id, pid)
            if a is not None:
                out.append((pass_id, a))
        return out

    def previous_pass_with(self, pid: str, before: str) -> str | None:
        """The latest pass before `before` that assessed `pid`."""
        prev = [p for p, _ in self.history(pid) if p < before]
        return prev[-1] if prev else None


def scores(assessment: dict, categories: list[Category]) -> dict:
    """Category means (applicable criteria only) and the overall mean of category means."""
    crit = assessment.get("criteria", {})
    out: dict = {"categories": {}}
    cat_means = []
    for cat in categories:
        levels = [crit[c.id]["level"] for c in cat.criteria if c.id in crit and crit[c.id].get("level") is not None]
        mean = sum(levels) / len(levels) if levels else None
        out["categories"][cat.id] = mean
        if mean is not None:
            cat_means.append(mean)
    out["overall"] = sum(cat_means) / len(cat_means) if cat_means else None
    return out
