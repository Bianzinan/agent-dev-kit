#!/usr/bin/env python3
"""Extract structured commit data from git history for changelog generation.

Standard library only. Outputs JSON (default) or Markdown.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date

TYPE_GROUPS = {
    "feat": "Features",
    "fix": "Fixes",
    "docs": "Docs",
    "refactor": "Refactor",
    "perf": "Refactor",
    "chore": "Chore",
    "build": "Chore",
    "ci": "Chore",
    "test": "Chore",
    "style": "Chore",
}

GROUP_ORDER = ["Features", "Fixes", "Refactor", "Docs", "Chore", "Other"]

SUBJECT_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")

SEP = "\x1e"
RECORD = "\x1f"


def run_git(repo: str, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def default_since(repo: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", repo, "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def collect(repo: str, since: str | None, until: str) -> list[dict]:
    fmt = SEP.join(["%h", "%s", "%b", "%an", "%ad"]) + RECORD
    args = ["log", "--no-merges", "--date=short", f"--pretty=format:{fmt}"]
    if since:
        args.append(f"{since}..{until}")
    else:
        args.extend([until, "-n", "50"])

    raw = run_git(repo, args)
    commits: list[dict] = []
    for chunk in raw.split(RECORD):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        parts = chunk.split(SEP)
        if len(parts) != 5:
            continue
        sha, subject, body, author, when = parts
        commits.append(parse_commit(sha, subject, body, author, when))
    return commits


def parse_commit(sha: str, subject: str, body: str, author: str, when: str) -> dict:
    match = SUBJECT_RE.match(subject.strip())
    if match:
        ctype = match.group("type")
        scope = match.group("scope") or ""
        desc = match.group("desc")
        bang = bool(match.group("bang"))
    else:
        ctype, scope, desc, bang = "", "", subject.strip(), False

    breaking = bang or "BREAKING CHANGE:" in body
    return {
        "sha": sha,
        "type": ctype,
        "scope": scope,
        "description": desc,
        "group": TYPE_GROUPS.get(ctype, "Other"),
        "breaking": breaking,
        "author": author,
        "date": when,
    }


def render_markdown(commits: list[dict], version: str) -> str:
    lines = [f"## {version} - {date.today().isoformat()}", ""]

    breaking = [c for c in commits if c["breaking"]]
    if breaking:
        lines.append("### ⚠ BREAKING CHANGES")
        lines.append("")
        lines.extend(f"- {c['description']} ({c['sha']})" for c in breaking)
        lines.append("")

    for group in GROUP_ORDER:
        entries = [c for c in commits if c["group"] == group and not c["breaking"]]
        if not entries:
            continue
        lines.append(f"### {group}")
        lines.append("")
        lines.extend(f"- {c['description']} ({c['sha']})" for c in entries)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository path")
    parser.add_argument("--since", default=None, help="start revision (default: latest tag)")
    parser.add_argument("--until", default="HEAD", help="end revision")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--version", default="Unreleased", help="version heading for markdown")
    args = parser.parse_args()

    since = args.since or default_since(args.repo)
    commits = collect(args.repo, since, args.until)

    if args.format == "json":
        json.dump({"since": since, "until": args.until, "commits": commits},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(commits, args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
