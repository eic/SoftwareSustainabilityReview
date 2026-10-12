import json

import yaml

from ssr.site import build
from ssr.summary import summarize
from tests.conftest import make_assessment


def test_build_site(repo, tmp_path):
    out = build(repo, tmp_path / "_site")
    for f in ("index.html", "rubrics.html", "passes.html", "style.css", "app.js",
              "projects/alpha.html", "projects/alpha.feedback.md", "passes/2026-01-01.html", "data/latest.json"):
        assert (out / f).is_file(), f
    index = (out / "index.html").read_text()
    assert "projects/alpha.html" in index and "projects/beta.html" in index
    rubrics = (out / "rubrics.html").read_text()
    assert 'id="eng.ci"' in rubrics
    data = json.loads((out / "data" / "latest.json").read_text())
    assert [p["id"] for p in data["projects"]] == ["alpha", "beta"]  # sorted by overall score
    fb = (out / "projects" / "alpha.feedback.md").read_text()
    assert "- [ ] Do the next thing for eng.ci." in fb


def test_summary_reports_level_changes(repo):
    second = "2026-06-01"
    d = repo.passes_dir / second
    d.mkdir()
    a = make_assessment(repo, "alpha", second, 2)
    a["criteria"]["eng.ci"].update(level=3, gaps=[], actions=[])
    (d / "alpha.assessment.yaml").write_text(yaml.safe_dump(a, sort_keys=False))
    (d / "manifest.yaml").write_text(yaml.safe_dump({"pass": second, "projects": ["alpha"], "assessor": {"agent": "t", "model": "m"}}))
    md = summarize(repo, second)
    assert "`eng.ci` 2 → 3" in md
    assert "(+0.20)" in md  # engineering: mean of 5 criteria rises by 0.2
