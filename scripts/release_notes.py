#!/usr/bin/env python3
"""Extract one version's section from CHANGELOG.md.

Used by .github/workflows/release.yml to turn the changelog entry into GitHub
Release notes, so the release text and the repository's changelog can never
drift apart — there is only one place to write them.

Standard library only. Python 3.8+.

Usage:
    python3 scripts/release_notes.py v0.3.0
    python3 scripts/release_notes.py 0.3.0 --output release-notes.md
    python3 scripts/release_notes.py --list
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"

# 形如 `## [0.3.0] - 2026-08-14`，日期可选。`## [未发布]` 也会被这条匹配到，
# 但它不是一个版本号，由 normalize() 之后的精确比较排除。
HEADING_RE = re.compile(r"^##\s+\[([^\]]+)\]")
# CHANGELOG 底部的链接引用行（`[0.3.0]: https://...`），不属于正文
LINK_REF_RE = re.compile(r"^\[[^\]]+\]:\s+\S+")


def normalize(version: str) -> str:
    """`v0.3.0` 与 `0.3.0` 视为同一个版本。"""
    version = version.strip()
    return version[1:] if version[:1].lower() == "v" else version


def read_changelog(path: Path) -> list[str]:
    if not path.is_file():
        sys.exit(f"错误: {path} 不存在")
    return path.read_text(encoding="utf-8").splitlines()


def list_versions(lines: list[str]) -> list[str]:
    """按 CHANGELOG 中出现的顺序返回所有版本号（跳过「未发布」）。"""
    out: list[str] = []
    for line in lines:
        match = HEADING_RE.match(line)
        if not match:
            continue
        name = match.group(1).strip()
        # 只保留看起来像版本号的条目，排除「未发布 / Unreleased」这类占位小节
        if re.match(r"^v?\d", name):
            out.append(normalize(name))
    return out


def extract(lines: list[str], version: str) -> str:
    """取出该版本小节的正文（不含标题行），到下一个 `## ` 标题为止。"""
    wanted = normalize(version)

    start = None
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match and normalize(match.group(1)) == wanted:
            start = index + 1
            break

    if start is None:
        known = ", ".join(list_versions(lines)) or "（无）"
        sys.exit(
            f"错误: CHANGELOG.md 里找不到版本 '{version}' 的小节。\n"
            f"       已有版本: {known}\n"
            f"       请先补一节 '## [{normalize(version)}] - YYYY-MM-DD' 再发布。"
        )

    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if LINK_REF_RE.match(line):
            continue
        body.append(line)

    text = "\n".join(body).strip()
    if not text:
        sys.exit(f"错误: CHANGELOG.md 中版本 '{version}' 的小节是空的，拒绝发布空的 release notes")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="从 CHANGELOG.md 提取指定版本的变更说明")
    parser.add_argument("version", nargs="?", help="版本号，如 v0.3.0 或 0.3.0")
    parser.add_argument("--output", "-o", help="写入文件而不是打印到 stdout")
    parser.add_argument("--list", action="store_true", help="列出 CHANGELOG 中的所有版本")
    parser.add_argument(
        "--changelog", default=str(CHANGELOG), help="CHANGELOG 路径（默认为仓库根目录）"
    )
    args = parser.parse_args()

    lines = read_changelog(Path(args.changelog))

    if args.list:
        for version in list_versions(lines):
            print(version)
        return 0

    if not args.version:
        parser.error("需要版本号参数（或使用 --list）")

    notes = extract(lines, args.version)

    if args.output:
        # 显式 LF：release notes 会被原样贴到 GitHub Release 正文
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(notes + "\n")
        print(f"✓ 已写入 {args.output}（{len(notes.splitlines())} 行）")
    else:
        print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
