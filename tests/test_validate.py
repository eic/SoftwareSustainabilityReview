from pathlib import Path

import yaml

from ssr.repo import Repo, scores
from ssr.validate import validate

ROOT = Path(__file__).resolve().parents[1]


def test_real_repository_is_valid():
    rep = validate(Repo(ROOT))
    assert rep.errors == []


def test_rubrics_declare_unique_criteria():
    crit = Repo(ROOT).criteria()
    ids = [c.id for c in crit]
    assert len(ids) == len(set(ids)) >= 20


def test_synthetic_pass_valid(repo):
    rep = validate(repo)
    assert rep.errors == [], rep.errors
    assert rep.warnings == [], rep.warnings


def _edit(repo, pid, fn):
    p = repo.assessment_path("2026-01-01", pid)
    a = yaml.safe_load(p.read_text())
    fn(a)
    p.write_text(yaml.safe_dump(a, sort_keys=False))


def test_missing_criterion(repo):
    _edit(repo, "alpha", lambda a: a["criteria"].pop("eng.ci"))
    assert any("missing criteria" in e for e in validate(repo).errors)


def test_level_rules(repo):
    def f(a):
        a["criteria"]["eng.ci"]["actions"] = []
        a["criteria"]["eng.testing"]["evidence"] = []
        a["criteria"]["doc.user"]["level"] = None
    _edit(repo, "alpha", f)
    errs = validate(repo).errors
    assert any("eng.ci" in e and "requires actions" in e for e in errs)
    assert any("eng.testing" in e and "requires evidence" in e for e in errs)
    assert any("doc.user" in e and "not_applicable" in e for e in errs)


def test_unpinned_permalink_warns(repo):
    _edit(repo, "alpha", lambda a: a["criteria"]["eng.ci"]["evidence"].append("https://github.com/x/y/blob/main/README.md"))
    assert any("not pinned" in w for w in validate(repo).warnings)


def test_email_rejected(repo):
    _edit(repo, "alpha", lambda a: a.update(summary="Maintained by jane@lab.gov."))
    assert any("e-mail" in e for e in validate(repo).errors)


def test_commit_mismatch(repo):
    _edit(repo, "alpha", lambda a: a.update(commit="f" * 40))
    assert any("differs from metrics" in e for e in validate(repo).errors)


def test_scores(repo):
    a = repo.assessment("2026-01-01", "alpha")
    a["criteria"]["eng.ci"]["level"] = None
    s = scores(a, repo.categories())
    assert s["overall"] == 2
    assert all(v == 2 for v in s["categories"].values())


def test_invalid_yaml_reported(repo):
    repo.assessment_path("2026-01-01", "alpha").write_text("criteria: [unclosed\n")
    assert any("invalid YAML" in e for e in validate(repo).errors)


def test_spack_spec_is_not_an_email(repo):
    _edit(repo, "alpha", lambda a: a.update(summary="eic-shell ships epic@26.10.0 and eicrecon@1.42.0."))
    assert validate(repo).errors == []
