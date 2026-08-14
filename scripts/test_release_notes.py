#!/usr/bin/env python3
"""Regression tests for scripts/release_notes.py.

Release notes are generated in CI, where a wrong result is only noticed after
the Release is already public. Every parsing rule is asserted here instead.

Standard library only. Python 3.8+.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import release_notes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SAMPLE = """# 更新日志

前言段落，不属于任何版本。

## [未发布]

## [0.3.0] - 2026-08-14

### 新增

- 甲
- 乙

## [0.2.0] - 2026-08-01

### 变更

- 丙

## [0.1.0] - 2026-07-20

### 新增

- 丁

[未发布]: https://example.com/compare/v0.3.0...HEAD
[0.3.0]: https://example.com/releases/tag/v0.3.0
""".splitlines()

failures: list[str] = []
passed = 0


def check(label: str, actual: object, expected: object) -> None:
    global passed
    if actual == expected:
        passed += 1
    else:
        failures.append(f"{label}\n    期望: {expected!r}\n    实际: {actual!r}")


def check_exits(label: str, version: str, lines: list[str]) -> None:
    """断言该版本会让脚本以非零状态退出（SystemExit 带非空消息）。"""
    global passed
    try:
        release_notes.extract(lines, version)
    except SystemExit as exc:
        if exc.code and str(exc.code).startswith("错误"):
            passed += 1
        else:
            failures.append(f"{label}\n    退出了，但没有给出可读的错误信息: {exc.code!r}")
        return
    failures.append(f"{label}\n    期望退出，实际正常返回")


def main() -> int:
    global passed
    print("测试 scripts/release_notes.py ...\n")

    # 版本号规范化：带不带 v 前缀都指向同一节
    check("normalize 去掉 v 前缀", release_notes.normalize("v0.3.0"), "0.3.0")
    check("normalize 保留裸版本号", release_notes.normalize("0.3.0"), "0.3.0")
    check("normalize 去空白", release_notes.normalize("  v1.2.3 "), "1.2.3")

    # 版本列举：跳过「未发布」这类占位小节
    check(
        "list_versions 跳过未发布",
        release_notes.list_versions(SAMPLE),
        ["0.3.0", "0.2.0", "0.1.0"],
    )

    # 正文提取：不含标题行，止于下一个 ## 标题
    check(
        "extract 取到本节正文且不越界",
        release_notes.extract(SAMPLE, "0.3.0"),
        "### 新增\n\n- 甲\n- 乙",
    )
    check(
        "extract 接受 v 前缀",
        release_notes.extract(SAMPLE, "v0.3.0"),
        "### 新增\n\n- 甲\n- 乙",
    )
    check(
        "extract 中间小节不吞掉后面的内容",
        release_notes.extract(SAMPLE, "0.2.0"),
        "### 变更\n\n- 丙",
    )
    # 最后一节后面跟着链接引用行，它们不该出现在 release notes 里
    check(
        "extract 过滤底部链接引用",
        release_notes.extract(SAMPLE, "0.1.0"),
        "### 新增\n\n- 丁",
    )

    # 失败路径：宁可让 CI 红，也不要发布一个空的或错版本的 release
    check_exits("找不到的版本应报错退出", "9.9.9", SAMPLE)
    check_exits("空小节应报错退出", "0.4.0", "## [0.4.0] - 2026-09-01\n\n## [0.3.0]".splitlines())
    # 「未发布」小节永远是空的，即使被当成版本号传进来也不会产出空 notes
    check_exits("未发布小节应报错退出", "未发布", SAMPLE)

    # 真实的 CHANGELOG 里已发布的每一节都必须能被提取。
    # 还没发过版时只有「未发布」一节，versions 为空是合法状态，不算失败。
    real = release_notes.read_changelog(ROOT / "CHANGELOG.md")
    passed += 1
    for version in release_notes.list_versions(real):
        try:
            release_notes.extract(real, version)
            passed += 1
        except SystemExit as exc:
            failures.append(f"真实 CHANGELOG.md 的 {version} 小节无法提取: {exc.code}")

    if failures:
        print(f"✗ 测试失败，{len(failures)} 项：\n")
        for item in failures:
            print(f"  - {item}")
        print()
        return 1

    print(f"✓ release_notes 测试通过（{passed} 个断言）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
