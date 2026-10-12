"""Deterministic metrics collection for one project.

Everything here is computed from public data (the git history, the file tree at the assessed
commit, and the GitHub API) with fixed rules, so two runs on the same day give the same numbers.
People are only ever counted: no names, logins, or e-mail addresses are written to the output.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import statistics
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from . import __version__
from .repo import Repo, load_yaml
from .shell import CommandError, gh_api, gh_file, gh_graphql, git, run
from .stack import load_snapshot

SHORT, LONG = 12, 24  # months

GITHUB_RE = re.compile(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$")
PR_SUBJECT_RE = re.compile(r"\(#\d+\)|^Merge pull request #\d+|See merge request !\d+", re.M)
EXTERNAL_ASSOC = {"CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE", "MANNEQUIN"}
CI_DECISIVE = {"success", "failure", "timed_out", "startup_failure"}

FILE_PATTERNS = {
    "readme": r"^readme(\.[a-z]+)?$",
    "license": r"^(license|licence|copying)([.-][\w.-]+)?$",
    "contributing": r"^(\.github/|docs/)?contributing(\.[a-z]+)?$",
    "code_of_conduct": r"^(\.github/|docs/)?code[_-]of[_-]conduct(\.[a-z]+)?$",
    "citation_cff": r"^citation\.cff$",
    "codemeta": r"^codemeta\.json$",
    "zenodo_json": r"^\.zenodo\.json$",
    "security": r"^(\.github/|docs/)?security(\.[a-z]+)?$",
    "changelog": r"^(docs/)?(changelog|changes|history|news|release[_-]?notes)(\.[a-z]+)?$",
    "governance": r"^(\.github/|docs/)?governance(\.[a-z]+)?$",
    "codeowners": r"^(\.github/|docs/)?codeowners$",
    "authors": r"^(authors|contributors|maintainers|credits)(\.[a-z]+)?$",
    "pr_template": r"^(\.github/|docs/)?pull_request_template(\.md)?$|^\.github/pull_request_template/",
    "issue_templates": r"^\.github/issue_template(/|\.md$)",
    "dependabot": r"^\.github/dependabot\.ya?ml$",
    "renovate": r"^(\.github/)?(renovate\.json5?|\.renovaterc(\.json)?)$",
    "pre_commit": r"^\.pre-commit-config\.ya?ml$",
    "clang_format": r"(^|/)\.clang-format$",
    "clang_tidy": r"(^|/)\.clang-tidy$",
    "editorconfig": r"^\.editorconfig$",
    "python_lint": r"^(\.flake8|\.pylintrc|pylintrc|ruff\.toml|\.ruff\.toml)$",
    "mypy": r"^\.?mypy\.ini$",
    "codecov": r"^(\.github/)?\.?codecov\.ya?ml$",
    "doxygen": r"(^|/)doxyfile(\.in)?$",
    "sphinx": r"^docs?/(source/)?conf\.py$",
    "mkdocs": r"^mkdocs\.ya?ml$",
    "dockerfile": r"(^|/)(dockerfile|containerfile)([.-][\w.-]+)?$",
    "apptainer_def": r"(^|/)(singularity|apptainer)[\w.-]*$",
    "spack_env": r"(^|/)spack\.(ya?ml|lock)$",
    "conda_env": r"(^|/)(environment|conda)[\w.-]*\.ya?ml$",
    "devcontainer": r"^\.devcontainer(/|\.json$)",
    "lockfile": r"(^|/)(uv\.lock|poetry\.lock|pixi\.lock|pipfile\.lock|conda-lock\.ya?ml|requirements[\w.-]*\.lock)$",
    "gitlab_ci": r"^\.gitlab-ci\.ya?ml$",
    "other_ci": r"(^|/)jenkinsfile$|^\.travis\.yml$|^\.circleci/|^azure-pipelines\.ya?ml$",
    "cmake": r"^cmakelists\.txt$",
    "pyproject": r"^pyproject\.toml$",
    "setup_py": r"^setup\.(py|cfg)$",
    "docs_dir": r"^docs?/",
    "examples_dir": r"^(examples?|tutorials?|demos?)/",
}
_FILE_RES = {k: re.compile(v, re.I) for k, v in FILE_PATTERNS.items()}

LANG_EXT = {
    "cpp": {".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".ipp", ".icc", ".tpp", ".C"},
    "c": {".c"},
    "python": {".py"},
    "fortran": {".f", ".for", ".f77", ".f90", ".f95", ".F", ".F90"},
    "julia": {".jl"},
    "rust": {".rs"},
    "javascript": {".js", ".ts", ".tsx", ".jsx"},
    "shell": {".sh", ".bash"},
    "cmake": {".cmake"},
}
CODE_LANGS = {"cpp", "c", "python", "fortran", "julia", "rust", "javascript"}
SCAN_EXTRA = {".xml", ".yaml", ".yml", ".toml", ".cfg", ".smk", ".txt", ".in"}
TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|testing|unittests?|test_?suite)/"
    r"|(^|/)(test_[\w-]+\.py|[\w-]+_test\.(py|cc|cpp|cxx)|test[\w-]*\.(cc|cpp|cxx|C)|\w+Tests?\.(cc|cpp|cxx|h|hh|hpp))$"
)
TEST_FRAMEWORKS = {
    "catch2": re.compile(r"Catch2|#include\s*[<\"]catch2?/"),
    "gtest": re.compile(r"\bGTest\b|#include\s*[<\"]gtest/"),
    "boost.test": re.compile(r"BOOST_AUTO_TEST_CASE|boost/test/"),
    "ctest": re.compile(r"\badd_test\s*\(|\benable_testing\s*\("),
    "pytest": re.compile(r"^\s*import pytest\b|\[tool\.pytest", re.M),
    "unittest": re.compile(r"^\s*import unittest\b", re.M),
}
VENDOR_DIRS = {"external", "externals", "extern", "third_party", "thirdparty", "3rdparty", "vendor", "vendored", "contrib", "deps"}
SITE_PATHS_RE = re.compile(r"(?<![\w$])(/gpfs/|/sdcc/|/w/[a-z]|/work/[a-z]|/u/home/|/home/[a-z]\w*/|/afs/|/lustre/|/eos/)")
EIC_SHELL_RE = re.compile(r"run-cvmfs-osg-eic-shell|eicweb/|ghcr\.io/eic/|\beic_(xl|ci|dev|prod|jl|tf|cuda)\b|eic-shell")


# --- helpers ---------------------------------------------------------------------------------


def parse_github(url: str) -> tuple[str, str] | None:
    m = GITHUB_RE.search(url)
    return (m.group(1), m.group(2)) if m else None


def parse_time(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def months_ago(now: dt.datetime, months: int) -> dt.datetime:
    return now - dt.timedelta(days=round(months * 30.4375))


def median(xs: list[float]) -> float | None:
    return round(statistics.median(xs), 2) if xs else None


def frac(n: int, d: int) -> float | None:
    return round(n / d, 3) if d else None


def bus_factor(counts: list[int], share: float) -> int | None:
    """Smallest number of people who together account for `share` of the total."""
    total = sum(counts)
    if not total:
        return None
    acc = 0
    for i, c in enumerate(sorted(counts, reverse=True), 1):
        acc += c
        if acc >= share * total:
            return i
    return len(counts)


def institution_domain(email: str, generic: set[str]) -> str | None:
    """Registrable domain of an e-mail address, or None for generic/personal providers."""
    if "@" not in email:
        return None
    host = email.rsplit("@", 1)[1].strip().lower().rstrip(".>")
    if not host or "noreply" in host or host in generic:
        return None
    labels = host.split(".")
    if len(labels) < 2:
        return None
    # Two-level public suffixes such as ac.uk, edu.cn, co.jp.
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in {"ac", "edu", "co", "gov", "org", "com", "net", "go", "or", "re"}:
        dom = ".".join(labels[-3:])
    else:
        dom = ".".join(labels[-2:])
    return None if dom in generic else dom


def normalize_version(tag: str) -> str:
    """Compare release tags with package versions: v01-38 -> 1.38, v1.42.0 -> 1.42.0, 2026.03.01 -> 2026.3.1."""
    t = re.sub(r"^(v|release[-_]?|version[-_]?)", "", tag.strip(), flags=re.I)
    parts = re.split(r"[.\-_]", t)
    return ".".join(str(int(p)) if p.isdigit() else p.lower() for p in parts if p)


def version_key(tag: str) -> tuple:
    """Sortable key for a release tag; non-numeric parts sort below numeric ones."""
    return tuple((1, int(p)) if p.isdigit() else (0, 0) for p in normalize_version(tag).split("."))


def is_vendored(path: str) -> bool:
    return any(seg.lower() in VENDOR_DIRS for seg in path.split("/")[:-1])


class Identities:
    """Union-find over author names and e-mails, so one person with several e-mails counts once."""

    UNUSABLE_NAMES = {"", "root", "unknown", "user", "admin", "ubuntu", "runner"}

    def __init__(self):
        self.parent: dict[str, str] = {}

    def _find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def add(self, name: str, email: str) -> None:
        keys = self._keys(name, email)
        for k in keys[1:]:
            self.parent[self._find(k)] = self._find(keys[0])
        if keys:
            self._find(keys[0])

    def _keys(self, name: str, email: str) -> list[str]:
        keys = []
        e = email.strip().lower()
        if e and "@" in e:
            # GitHub noreply addresses embed the login: 12345+login@users.noreply.github.com
            m = re.match(r"(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", e)
            keys.append(f"l:{m.group(1)}" if m else f"e:{e}")
        n = " ".join(name.lower().split())
        if n not in self.UNUSABLE_NAMES:
            keys.append(f"n:{n}")
        return keys

    def key(self, name: str, email: str) -> str:
        keys = self._keys(name, email)
        return self._find(keys[0]) if keys else "anonymous"


class BotFilter:
    def __init__(self, cfg: dict):
        self.patterns = [p.lower() for p in cfg.get("bot_patterns", [])]
        self.names = {n.lower() for n in cfg.get("bot_names", [])}

    def __call__(self, *idents: str | None, typename: str | None = None) -> bool:
        if typename == "Bot":
            return True
        for s in idents:
            if not s:
                continue
            s = s.lower()
            if s in self.names or any(p in s for p in self.patterns):
                return True
        return False


# --- checkout --------------------------------------------------------------------------------


def checkout_dir(repo: Repo, project: dict) -> Path:
    url = project["repo"]
    slug = re.sub(r"^https?://", "", url).rstrip("/").removesuffix(".git").replace("/", "__")
    return repo.cache_dir / "repos" / slug


def ensure_checkout(url: str, dest: Path) -> None:
    if (dest / ".git").is_dir():
        git(dest, "fetch", "--quiet", "--force", "--tags", "--prune", "origin")
        git(dest, "remote", "set-head", "origin", "--auto")
        git(dest, "checkout", "--quiet", "--force", "--detach", "origin/HEAD")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", "--filter=blob:none", url, str(dest)])


def ensure_shallow(url: str, dest: Path) -> None:
    if (dest / ".git").is_dir():
        git(dest, "fetch", "--quiet", "--depth", "1", "origin")
        git(dest, "reset", "--quiet", "--hard", "FETCH_HEAD")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", "--depth", "1", url, str(dest)])


# --- collector -------------------------------------------------------------------------------


class Collector:
    def __init__(self, repo: Repo, now: dt.datetime | None = None):
        self.repo = repo
        self.cfg = repo.config
        self.now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        self.is_bot = BotFilter(self.cfg["collect"])
        self.generic_domains = {d.lower() for d in self.cfg["collect"].get("generic_email_domains", [])}
        self.snapshot = load_snapshot(repo)
        comps = load_yaml(repo.root / "reference" / "eic-supported-components.yaml")["components"]
        self.components = {
            name: {**c, "re": re.compile("|".join(f"(?:{p})" for p in c["patterns"]), re.M)}
            for name, c in comps.items()
        }
        self._eic_spack: Path | None = None

    # -- entry point

    def collect(self, project: dict, pass_id: str) -> dict:
        dest = checkout_dir(self.repo, project)
        ensure_checkout(project["repo"], dest)
        sub = project.get("subdir")
        errors: list[str] = []
        out: dict = {
            "schema_version": 1,
            "project": project["id"],
            "pass": pass_id,
            "repo_url": project["repo"],
            "subdir": sub,
            "collected_at": self.now.isoformat(),
            "collector_version": __version__,
            "windows_months": {"short": SHORT, "long": LONG},
        }
        files = [f for f in git(dest, "ls-files").splitlines() if not sub or f.startswith(sub.rstrip("/") + "/")]
        rel = [f[len(sub.rstrip("/")) + 1:] if sub else f for f in files]

        sections = [
            ("git", lambda: self.git_metrics(dest, sub)),
            ("files", lambda: self.file_metrics(rel)),
            ("code", lambda: self.code_metrics(dest, files, rel)),
            ("eic", lambda: self.eic_metrics(dest, files, rel, project)),
            ("ci", lambda: self.ci_metrics(dest, rel, sub)),
        ]
        gh = parse_github(project["repo"])
        if gh:
            o, n = gh
            sections += [
                ("repo", lambda: self.repo_metrics(o, n)),
                ("community", lambda: self.community_metrics(o, n)),
                ("releases", lambda: self.release_metrics(o, n)),
                ("issues", lambda: self.issue_metrics(o, n)),
                ("prs", lambda: self.pr_metrics(o, n)),
            ]
        else:
            errors.append("github: not a GitHub repository; repo/community/releases/issues/prs not collected")
        sections.append(("packaging", lambda: self.packaging_metrics(project, out)))

        for name, fn in sections:
            try:
                out[name] = fn()
            except (CommandError, OSError, ValueError, KeyError, TypeError) as e:
                out[name] = None
                errors.append(f"{name}: {e}")
        if out.get("git"):
            unmatched = out["git"].pop("_unmatched_first_parent")
            if gh and unmatched:
                try:
                    self.resolve_pr_commits(*gh, out["git"], unmatched)
                except CommandError as e:
                    errors.append(f"git.first_parent: {e}")
        if gh and out.get("ci") is not None and out.get("repo"):
            try:
                out["ci"].update(self.ci_runs(*gh, out["repo"]["default_branch"]))
            except CommandError as e:
                errors.append(f"ci.runs: {e}")
        out["errors"] = errors
        return out

    # -- git history

    def git_metrics(self, dest: Path, sub: str | None) -> dict:
        path_args = ["--", sub] if sub else []
        t12, t24 = months_ago(self.now, SHORT), months_ago(self.now, LONG)
        log = git(dest, "log", "HEAD", "--no-merges", "--format=%an%x1f%ae%x1f%aI", *path_args)
        ids = Identities()
        rows = []
        for line in log.splitlines():
            name, email, date = line.split("\x1f")
            if self.is_bot(name, email):
                continue
            ids.add(name, email)
            rows.append((name, email, parse_time(date)))
        first_seen: dict[str, dt.datetime] = {}
        c12: Counter = Counter()
        c24: Counter = Counter()
        domains24: set[str] = set()
        for name, email, when in rows:
            k = ids.key(name, email)
            first_seen[k] = min(first_seen.get(k, when), when)
            if when >= t24:
                c24[k] += 1
                d = institution_domain(email, self.generic_domains)
                if d:
                    domains24.add(d)
                if when >= t12:
                    c12[k] += 1
        fp = [
            line.split("\x1f", 1)
            for line in git(dest, "log", "HEAD", "--first-parent", f"--since={t12.isoformat()}",
                            "--format=%H%x1f%s", *path_args).splitlines()
        ]
        unmatched = [sha for sha, subject in fp if not PR_SUBJECT_RE.search(subject)]
        tags = git(dest, "for-each-ref", "refs/tags", "--format=%(creatordate:iso-strict)").split()
        head = git(dest, "rev-parse", "HEAD").strip()
        head_date = git(dest, "log", "-1", "--format=%cI", "HEAD").strip()
        last = git(dest, "log", "-1", "--format=%cI", "HEAD", *path_args).strip()
        total24 = sum(c24.values())
        return {
            "head_sha": head,
            "head_date": head_date,
            "last_commit_date": last or None,
            "commits_total": len(rows),
            "commits_12m": sum(c12.values()),
            "commits_24m": total24,
            "authors_total": len(first_seen),
            "authors_12m": len(c12),
            "authors_24m": len(c24),
            "new_authors_12m": sum(1 for d in first_seen.values() if d >= t12),
            "bus_factor_50_24m": bus_factor(list(c24.values()), 0.5),
            "bus_factor_80_24m": bus_factor(list(c24.values()), 0.8),
            "top_author_share_24m": frac(max(c24.values()), total24) if c24 else None,
            "email_domains_24m": len(domains24),
            "first_parent_commits_12m": len(fp),
            "first_parent_pr_fraction_12m": frac(len(fp) - len(unmatched), len(fp)),
            "_unmatched_first_parent": unmatched,  # resolved against the GitHub API, then removed
            "tags_total": len(tags),
            "tags_24m": sum(1 for t in tags if parse_time(t) and parse_time(t) >= t24),
        }

    def resolve_pr_commits(self, owner: str, name: str, g: dict, unmatched: list[str], limit: int = 60) -> None:
        """Subjects miss PRs whose squash title was edited; ask GitHub which commits came from a merged PR."""
        n = g["first_parent_commits_12m"]
        # Rebase-merging projects can have thousands of such commits: check an evenly spaced sample.
        step = max(1, -(-len(unmatched) // limit))
        results = []
        for sha in unmatched[::step]:
            try:
                pulls = gh_api(f"repos/{owner}/{name}/commits/{sha}/pulls") or []
            except CommandError:
                continue  # transient API failure: leave this commit out of the sample
            results.append(any(p.get("merged_at") for p in pulls))
        if not results:
            return
        checked, via_pr = results, sum(results)
        matched = n - len(unmatched) + via_pr * len(unmatched) / len(checked)
        g["first_parent_pr_fraction_12m"] = frac(round(matched), n)
        g["first_parent_resolved_via_api"] = len(checked)
        g["first_parent_pr_fraction_estimated"] = len(checked) < len(unmatched)

    # -- file tree

    def file_metrics(self, rel: list[str]) -> dict:
        out = {}
        for key, rx in _FILE_RES.items():
            hits = [f for f in rel if rx.search(f)]
            if key in {"docs_dir", "examples_dir"}:
                out[key] = len(hits)
            else:
                out[key] = hits[:5]
        out["github_workflows"] = sorted(f for f in rel if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", f))
        return out

    def _read(self, path: Path, limit: int = 2_000_000) -> str | None:
        try:
            if path.stat().st_size > limit:
                return None
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def code_metrics(self, dest: Path, files: list[str], rel: list[str]) -> dict:
        by_lang: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0})
        sizes = []
        test_files = 0
        frameworks = set()
        cxx_std: set[str] = set()
        requires_python = None
        site_paths = []
        for f, r in zip(files, rel):
            if is_vendored(r):
                continue
            p = Path(f)
            ext = p.suffix
            lang = next((lang for lang, exts in LANG_EXT.items() if ext in exts), None)
            if p.name == "CMakeLists.txt":
                lang = "cmake"
            if lang is None and p.name != "pyproject.toml":
                continue
            text = self._read(dest / f)
            if text is None:
                continue
            if lang:
                n = text.count("\n")
                by_lang[lang]["files"] += 1
                by_lang[lang]["lines"] += n
                if lang in CODE_LANGS:
                    sizes.append((n, r))
                    if TEST_PATH_RE.search(r):
                        test_files += 1
                    m = SITE_PATHS_RE.search(text)
                    if m and len(site_paths) < 10:
                        site_paths.append(f"{r}: {m.group(1)}")
            for fw, rx in TEST_FRAMEWORKS.items():
                if fw not in frameworks and rx.search(text):
                    frameworks.add(fw)
            if lang == "cmake":
                cxx_std.update(re.findall(r"CXX_STANDARD(?:_MIN)?\s+\"?(\d+)", text))
                cxx_std.update(re.findall(r"cxx_std_(\d+)", text))
            if p.name == "pyproject.toml" and r == "pyproject.toml":
                m = re.search(r"requires-python\s*=\s*[\"']([^\"']+)", text)
                requires_python = m.group(1) if m else None
        sizes.sort(reverse=True)
        return {
            "languages": {k: v for k, v in sorted(by_lang.items(), key=lambda kv: -kv[1]["lines"])},
            "source_lines": sum(v["lines"] for k, v in by_lang.items() if k in CODE_LANGS),
            "largest_source_files": [{"path": r, "lines": n} for n, r in sizes[:5]],
            "test_files": test_files,
            "test_frameworks": sorted(frameworks),
            "cxx_standard": sorted(cxx_std, key=int),
            "requires_python": requires_python,
            "site_specific_paths": site_paths,
        }

    # -- EIC stack usage

    def eic_metrics(self, dest: Path, files: list[str], rel: list[str], project: dict) -> dict:
        own = project["repo"].lower().removesuffix(".git").rstrip("/")
        counts: Counter = Counter()
        evidence: dict[str, list[str]] = defaultdict(list)
        for f, r in zip(files, rel):
            p = Path(f)
            if is_vendored(r):
                continue  # vendored copies are reported separately, not counted as reuse
            if not (p.suffix in SCAN_EXTRA or p.name in {"CMakeLists.txt", "Snakefile"}
                    or any(p.suffix in exts for exts in LANG_EXT.values())):
                continue
            if p.suffix == ".txt" and p.name != "CMakeLists.txt":
                continue
            text = self._read(dest / f, limit=1_000_000)
            if text is None:
                continue
            text = r + "\n" + text  # lets path patterns (Snakefile) match
            for name, c in self.components.items():
                if c["re"].search(text):
                    counts[name] += 1
                    if len(evidence[name]) < 3:
                        evidence[name].append(r)
        selfname = next((n for n, c in self.components.items() if c["repo"].lower().rstrip("/") == own), None)
        detected = {
            n: {"files": counts[n], "kind": self.components[n]["kind"], "examples": evidence[n]}
            for n, _ in counts.most_common() if n != selfname
        }
        vendored = []
        for r in rel:
            parts = r.split("/")
            for i, seg in enumerate(parts[:3]):
                if seg.lower() in VENDOR_DIRS and i + 1 < len(parts) - 1:
                    d = "/".join(parts[: i + 2])
                    if d not in vendored:
                        vendored.append(d)
                    break
        submodules = []
        gm = dest / ".gitmodules"
        if gm.is_file():
            submodules = re.findall(r"^\s*url\s*=\s*(\S+)", gm.read_text(errors="replace"), re.M)
        return {
            "components_detected": detected,
            "domain_components": sorted(n for n in detected if self.components[n]["kind"] == "domain"),
            "is_component": selfname,
            "vendored_candidates": vendored[:20],
            "submodules": submodules,
        }

    # -- CI configuration (from the tree) and runs (from the API)

    def ci_metrics(self, dest: Path, rel: list[str], sub: str | None) -> dict:
        base = dest / sub if sub else dest
        wfs = [f for f in rel if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", f)]
        pr_triggered = []
        runs_on: set[str] = set()
        images: set[str] = set()
        eic_shell = False
        actions: set[str] = set()
        unpinned = 0
        for f in wfs:
            text = self._read(base / f) or ""
            try:
                doc = yaml.safe_load(text) or {}
            except yaml.YAMLError:
                doc = {}
            trig = doc.get("on", doc.get(True)) if isinstance(doc, dict) else None
            names = (
                {trig} if isinstance(trig, str) else set(trig) if isinstance(trig, (list, dict)) else set()
            )
            if names & {"pull_request", "pull_request_target", "merge_group"}:
                pr_triggered.append(f)
            runs_on.update(re.findall(r"\b((?:ubuntu|macos|windows)-[\w.-]+|self-hosted)\b", text))
            images.update(
                m.strip("'\"") for m in re.findall(r"(?:^|\s)(?:image|container):[ \t]+([^\s#]+)", text, re.M)
                if not m.endswith(":")
            )
            images.update(
                "platform-release: " + m.strip("'\"")
                for m in re.findall(r"platform-release:[ \t]*(\"[^\"\n]*\"|'[^'\n]*'|[^\s#]+)", text)
            )
            eic_shell = eic_shell or bool(EIC_SHELL_RE.search(text))
            for use in re.findall(r"uses:\s*([\w.-]+/[\w./-]+)@([\w.-]+)", text):
                actions.add(use[0])
                if not re.fullmatch(r"[0-9a-f]{40}", use[1]):
                    unpinned += 1
        other = []
        for key in ("gitlab_ci", "other_ci"):
            other += [f for f in rel if _FILE_RES[key].search(f)]
        return {
            "workflow_count": len(wfs),
            "pr_triggered_workflows": pr_triggered,
            "runs_on": sorted(runs_on),
            "container_images": sorted(images)[:20],
            "uses_eic_shell": eic_shell,
            "actions_used": sorted(actions),
            "action_refs_not_sha_pinned": unpinned,
            "other_ci": other,
        }

    def ci_runs(self, owner: str, name: str, branch: str) -> dict:
        data = gh_api(f"repos/{owner}/{name}/actions/runs?branch={branch}&event=push&per_page=100")
        runs = [r for r in (data or {}).get("workflow_runs", []) if r.get("conclusion") in CI_DECISIVE][:50]
        ok = sum(1 for r in runs if r["conclusion"] == "success")
        return {
            "default_branch_runs": len(runs),
            "default_branch_success_rate": frac(ok, len(runs)),
            "last_default_branch_run": runs[0]["created_at"] if runs else None,
        }

    # -- GitHub repository, community, releases

    def repo_metrics(self, owner: str, name: str) -> dict:
        q = """query($o:String!,$n:String!){repository(owner:$o,name:$n){
          nameWithOwner defaultBranchRef{name} isArchived isFork createdAt pushedAt
          stargazerCount forkCount homepageUrl hasIssuesEnabled hasDiscussionsEnabled
          licenseInfo{spdxId} repositoryTopics(first:20){nodes{topic{name}}}
          issues(states:OPEN){totalCount} pullRequests(states:OPEN){totalCount}}}"""
        r = gh_graphql(q, o=owner, n=name)["repository"]
        branch = r["defaultBranchRef"]["name"]
        b = gh_api(f"repos/{owner}/{name}/branches/{branch}", allow_missing=True) or {}
        rules = gh_api(f"repos/{owner}/{name}/rulesets", allow_missing=True)
        langs = gh_api(f"repos/{owner}/{name}/languages", allow_missing=True) or {}
        total = sum(langs.values()) or 1
        return {
            "full_name": r["nameWithOwner"],
            "default_branch": branch,
            "archived": r["isArchived"],
            "fork": r["isFork"],
            "created_at": r["createdAt"],
            "pushed_at": r["pushedAt"],
            "stars": r["stargazerCount"],
            "forks": r["forkCount"],
            "homepage": r["homepageUrl"] or None,
            "license_spdx": (r["licenseInfo"] or {}).get("spdxId"),
            "topics": [t["topic"]["name"] for t in r["repositoryTopics"]["nodes"]],
            "has_issues": r["hasIssuesEnabled"],
            "has_discussions": r["hasDiscussionsEnabled"],
            "open_issues": r["issues"]["totalCount"],
            "open_prs": r["pullRequests"]["totalCount"],
            "default_branch_protected": b.get("protected"),
            "rulesets": len(rules) if isinstance(rules, list) else None,
            "languages_github": {k: round(v / total, 3) for k, v in sorted(langs.items(), key=lambda kv: -kv[1])[:8]},
        }

    def community_metrics(self, owner: str, name: str) -> dict:
        prof = gh_api(f"repos/{owner}/{name}/community/profile", allow_missing=True) or {}
        files = prof.get("files") or {}
        return {
            "health_percentage": prof.get("health_percentage"),
            # Includes files inherited from the organization's .github repository.
            "files": {k: bool(v) for k, v in sorted(files.items())},
        }

    def release_metrics(self, owner: str, name: str) -> dict:
        rels = [r for r in gh_api(f"repos/{owner}/{name}/releases?per_page=100", paginate=True) if not r.get("draft")]
        t24 = months_ago(self.now, LONG)
        recent = [r for r in rels if parse_time(r.get("published_at")) and parse_time(r["published_at"]) >= t24]
        stable = [r for r in rels if not r.get("prerelease")]
        # Highest version, not most recent: projects publish backport patches of older series.
        latest = max(stable or rels, key=lambda r: (version_key(r["tag_name"]), r.get("published_at") or ""), default=None)
        newest = max(rels, key=lambda r: r.get("published_at") or "", default=None)
        authors = {r["author"]["login"] for r in recent if r.get("author") and not self.is_bot(r["author"]["login"], typename=r["author"].get("type"))}
        return {
            "count_total": len(rels),
            "count_24m": len(recent),
            "latest_tag": latest["tag_name"] if latest else None,
            "latest_date": latest["published_at"] if latest else None,
            "newest_published_tag": newest["tag_name"] if newest else None,
            "newest_published_date": newest["published_at"] if newest else None,
            "authors_24m": len(authors),
            "with_notes_fraction_24m": frac(sum(1 for r in recent if (r.get("body") or "").strip()), len(recent)),
        }

    # -- issues and PRs (GraphQL search, last 12 months)

    def _search(self, query: str, fragment: str, page_size: int = 100, max_pages: int = 10) -> tuple[list[dict], int]:
        q = f"""query($q:String!,$after:String,$n:Int!){{search(query:$q,type:ISSUE,first:$n,after:$after){{
          issueCount pageInfo{{hasNextPage endCursor}} nodes{{{fragment}}}}}}}"""
        nodes, after, count = [], None, 0
        for _ in range(max_pages):
            data = gh_graphql(q, q=query, after=after, n=page_size)["search"]
            count = data["issueCount"]
            nodes += [x for x in data["nodes"] if x]
            if not data["pageInfo"]["hasNextPage"]:
                break
            after = data["pageInfo"]["endCursor"]
        return nodes, count

    def _count(self, query: str) -> int:
        q = "query($q:String!){search(query:$q,type:ISSUE,first:1){issueCount}}"
        return gh_graphql(q, q=query)["search"]["issueCount"]

    def issue_metrics(self, owner: str, name: str) -> dict:
        since = months_ago(self.now, SHORT).date().isoformat()
        frag = """... on Issue { createdAt closedAt author{login __typename} labels{totalCount}
                  comments(first:20){nodes{createdAt author{login __typename}}} }"""
        nodes, count = self._search(f"repo:{owner}/{name} is:issue created:>={since} sort:created-desc", frag)
        responses, unanswered, labeled, closed, n = [], 0, 0, 0, 0
        for i in nodes:
            a = i.get("author") or {}
            if self.is_bot(a.get("login"), typename=a.get("__typename")):
                continue
            n += 1
            created = parse_time(i["createdAt"])
            firsts = [
                parse_time(c["createdAt"]) for c in i["comments"]["nodes"]
                if c.get("author") and c["author"].get("login") != a.get("login")
                and not self.is_bot(c["author"].get("login"), typename=c["author"].get("__typename"))
            ]
            if i.get("closedAt"):
                closed += 1
                firsts.append(parse_time(i["closedAt"]))
            if firsts:
                responses.append((min(firsts) - created).total_seconds() / 86400)
            else:
                unanswered += 1
            labeled += i["labels"]["totalCount"] > 0
        old = months_ago(self.now, 12).date().isoformat()
        return {
            "created_12m": n,
            "sampled": len(nodes) < count,
            "closed_of_created_12m": closed,
            "median_first_response_days_12m": median(responses),
            "unanswered_fraction_12m": frac(unanswered, n),
            "labeled_fraction_12m": frac(labeled, n),
            "open_total": self._count(f"repo:{owner}/{name} is:issue is:open"),
            "open_older_365d": self._count(f"repo:{owner}/{name} is:issue is:open created:<{old}"),
        }

    def pr_metrics(self, owner: str, name: str) -> dict:
        since = months_ago(self.now, SHORT).date().isoformat()
        frag = """... on PullRequest { createdAt mergedAt state authorAssociation author{login __typename}
                  mergedBy{login __typename} reviews(first:30){nodes{author{login __typename}}}
                  files(first:100){nodes{path}} }"""
        query = f"repo:{owner}/{name} is:pr created:>={since} sort:created-desc"
        try:
            nodes, count = self._search(query, frag)
        except CommandError:
            nodes, count = self._search(query, frag, page_size=40, max_pages=25)
        merged = reviewed = external = touching = n = 0
        days = []
        reviewers: Counter = Counter()
        mergers: set[str] = set()
        for p in nodes:
            a = p.get("author") or {}
            if self.is_bot(a.get("login"), typename=a.get("__typename")):
                continue
            n += 1
            if not p.get("mergedAt"):
                continue
            merged += 1
            days.append((parse_time(p["mergedAt"]) - parse_time(p["createdAt"])).total_seconds() / 86400)
            revs = {
                r["author"]["login"] for r in p["reviews"]["nodes"]
                if r.get("author") and r["author"].get("login") != a.get("login")
                and not self.is_bot(r["author"].get("login"), typename=r["author"].get("__typename"))
            }
            reviewed += bool(revs)
            reviewers.update(revs)
            mb = p.get("mergedBy") or {}
            if mb.get("login") and not self.is_bot(mb["login"], typename=mb.get("__typename")):
                mergers.add(mb["login"])
            external += p.get("authorAssociation") in EXTERNAL_ASSOC
            touching += any(TEST_PATH_RE.search(f["path"]) for f in (p.get("files") or {}).get("nodes", []))
        total_reviews = sum(reviewers.values())
        old = (self.now - dt.timedelta(days=90)).date().isoformat()
        return {
            "created_12m": n,
            "sampled": len(nodes) < count,
            "merged_12m": merged,
            "median_days_to_merge_12m": median(days),
            "reviewed_fraction_12m": frac(reviewed, merged),
            "external_fraction_12m": frac(external, merged),
            "test_touching_fraction_12m": frac(touching, merged),
            "distinct_reviewers_12m": len(reviewers),
            "top_reviewer_share_12m": frac(max(reviewers.values()), total_reviews) if reviewers else None,
            "distinct_mergers_12m": len(mergers),
            "open_total": self._count(f"repo:{owner}/{name} is:pr is:open"),
            "open_older_90d": self._count(f"repo:{owner}/{name} is:pr is:open created:<{old}"),
        }

    # -- packaging

    def _eic_spack_dir(self) -> Path:
        if self._eic_spack is None:
            st = self.cfg["stack"]
            dest = self.repo.cache_dir / "helpers" / st["eic_spack_repo"].replace("/", "__")
            ensure_shallow(f"https://github.com/{st['eic_spack_repo']}", dest)
            self._eic_spack = dest / st["eic_spack_packages_dir"]
        return self._eic_spack

    @staticmethod
    def _recipe(text: str | None, project: dict) -> dict | None:
        if text is None:
            return None
        gh = parse_github(project["repo"])
        ident = f"{gh[0]}/{gh[1]}".lower() if gh else project["repo"].lower()
        return {
            "matches_repo": ident in text.lower(),
            "versions": re.findall(r"version\(\s*[\"']([^\"']+)[\"']", text)[:5],
        }

    def packaging_metrics(self, project: dict, partial: dict) -> dict:
        gh = parse_github(project["repo"])
        pk = project.get("packages") or {}
        spack_name = pk.get("spack") or (gh[1] if gh else project["id"]).lower().replace("_", "-")
        dirname = spack_name.replace("-", "_")
        st = self.cfg["stack"]
        eic_dir = self._eic_spack_dir()
        eic_recipe = eic_dir / dirname / "package.py"
        out: dict = {
            "spack_name": spack_name,
            "eic_spack": self._recipe(eic_recipe.read_text() if eic_recipe.is_file() else None, project),
            "spack_builtin": self._recipe(
                gh_file(st["spack_builtin_repo"], f"{st['spack_builtin_packages_dir']}/{dirname}/package.py"), project
            ),
            "in_eic_shell": spack_name in self.snapshot.get("specs", []) or spack_name in self.snapshot.get("versions", {}),
            "eic_shell_version": self.snapshot.get("versions", {}).get(spack_name),
            "eic_spack_dependents": sorted(
                d.name.replace("_", "-") for d in eic_dir.iterdir()
                if (d / "package.py").is_file() and d.name != dirname
                and re.search(rf"depends_on\(\s*[\"']{re.escape(spack_name)}([@+~ \"'])", (d / "package.py").read_text())
            ),
            "conda_forge": None,
            "pypi": None,
        }
        if pk.get("conda"):
            out["conda_forge"] = gh_api(f"repos/conda-forge/{pk['conda']}-feedstock", allow_missing=True) is not None
        if pk.get("pypi"):
            try:
                with urllib.request.urlopen(f"https://pypi.org/pypi/{pk['pypi']}/json", timeout=20) as r:
                    out["pypi"] = {"latest": json.load(r)["info"]["version"]}
            except OSError:
                out["pypi"] = False
        latest = normalize_version((partial.get("releases") or {}).get("latest_tag") or "")
        packaged = {normalize_version(v) for src in ("eic_spack", "spack_builtin") for v in ((out[src] or {}).get("versions") or [])}
        out["latest_release_packaged"] = (latest in packaged) if latest else None
        return out
