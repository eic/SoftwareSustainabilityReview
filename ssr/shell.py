"""Thin wrappers around the `gh` and `git` CLIs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


class CommandError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise CommandError(f"{' '.join(cmd[:4])}...: {proc.stderr.strip()[:500]}")
    return proc.stdout


def git(repo: Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args])


def gh_api(path: str, paginate: bool = False, allow_missing: bool = False):
    """GET a REST endpoint. With paginate, list pages are concatenated into one list."""
    cmd = ["gh", "api", "-H", "Accept: application/vnd.github+json", path]
    if paginate:
        cmd[2:2] = ["--paginate", "--slurp"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        if allow_missing and ("404" in proc.stderr or "Not Found" in proc.stderr or "403" in proc.stderr):
            return None
        raise CommandError(f"gh api {path}: {proc.stderr.strip()[:500]}")
    data = json.loads(proc.stdout) if proc.stdout.strip() else None
    if paginate and isinstance(data, list):
        flat = []
        for page in data:
            if isinstance(page, list):
                flat.extend(page)
            elif isinstance(page, dict):
                # Endpoints such as actions/runs wrap their list in an object.
                lists = [v for v in page.values() if isinstance(v, list)]
                flat.extend(lists[0] if lists else [page])
        return flat
    return data


def gh_graphql(query: str, **variables) -> dict:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        if v is None:
            continue
        flag = "-F" if isinstance(v, (int, bool)) else "-f"
        cmd += [flag, f"{k}={str(v).lower() if isinstance(v, bool) else v}"]
    out = run(cmd)
    data = json.loads(out)
    if data.get("errors"):
        raise CommandError(f"graphql: {data['errors'][0].get('message')}")
    return data["data"]


def gh_file(repo: str, path: str, ref: str | None = None) -> str | None:
    """Raw content of a file in a GitHub repository, or None if it does not exist."""
    q = f"repos/{repo}/contents/{path}" + (f"?ref={ref}" if ref else "")
    proc = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw", q], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    return proc.stdout
