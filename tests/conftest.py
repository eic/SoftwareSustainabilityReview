import json
import shutil
from pathlib import Path

import pytest
import yaml

from ssr.repo import Repo

ROOT = Path(__file__).resolve().parents[1]
SHA = "0123456789abcdef0123456789abcdef01234567"


def make_assessment(repo: Repo, pid: str, pass_id: str, level: int = 2) -> dict:
    crit = {}
    for c in repo.criteria():
        crit[c.id] = {
            "level": level,
            "confidence": "high",
            "rationale": f"Synthetic rationale for {c.id}.",
            "evidence": [f"https://github.com/example/{pid}/blob/{SHA}/README.md#L1-L5", "metrics:git.authors_12m = 3"],
            "gaps": [] if level == 3 else ["A synthetic gap."],
            "actions": [] if level == 3 else [{"action": f"Do the next thing for {c.id}.", "priority": "medium", "effort": "S"}],
        }
    return {
        "schema_version": 1,
        "project": pid,
        "pass": pass_id,
        "commit": SHA,
        "assessor": {"agent": "test", "model": "test-model"},
        "summary": "Synthetic summary.",
        "criteria": crit,
    }


@pytest.fixture
def repo(tmp_path) -> Repo:
    """A copy of the review repository with two synthetic projects and one synthetic pass."""
    for d in ("rubrics", "schema", "reference"):
        shutil.copytree(ROOT / d, tmp_path / d)
    shutil.copy(ROOT / "config.yaml", tmp_path / "config.yaml")
    projects = [
        {"id": "alpha", "name": "Alpha", "repo": "https://github.com/example/alpha", "domain": "reconstruction", "role": "core"},
        {"id": "beta", "name": "Beta", "repo": "https://github.com/example/beta", "domain": "analysis", "role": "community"},
    ]
    (tmp_path / "projects.yaml").write_text(yaml.safe_dump({"projects": projects}))
    r = Repo(tmp_path)
    pass_id = "2026-01-01"
    d = tmp_path / "passes" / pass_id
    d.mkdir(parents=True)
    (d / "manifest.yaml").write_text(yaml.safe_dump({
        "pass": pass_id, "assessor": {"agent": "test", "model": "test-model"},
        "rubrics_commit": SHA, "stack_snapshot": SHA, "projects": ["alpha", "beta"],
    }))
    for pid, lvl in (("alpha", 2), ("beta", 1)):
        (d / f"{pid}.assessment.yaml").write_text(yaml.safe_dump(make_assessment(r, pid, pass_id, lvl), sort_keys=False))
        (d / f"{pid}.metrics.json").write_text(json.dumps({"project": pid, "git": {"head_sha": SHA}, "errors": []}))
    return r
