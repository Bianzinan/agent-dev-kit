#!/usr/bin/env python3
"""PreToolUse hook: 拦截高危 Bash 命令。

从 stdin 读取 Claude Code 传入的 JSON 事件；退出码语义：
  0  放行
  2  阻止本次工具调用，并把 stderr 的内容反馈给模型

用 Python 而非 shell 实现：规则用一种正则方言表达、能被 test_hooks.py 直接
逐条断言，且不必处理 shell 的引号与转义陷阱。原来的 bash 版本本来也要 shell out
到 python3 解析 JSON，而 Python 3.8+ 已是本仓库的硬依赖（validate.py 需要它），
所以这不引入新的依赖。

黑名单是正则匹配，只防手滑与惯性操作，不是对抗性的安全边界。
"""

from __future__ import annotations

import json
import re
import sys

# (正则, 原因)。正则用 Python re 方言，大小写不敏感匹配。
RULES: list[tuple[str, str]] = [
    (r"\brm\s+-[a-z]*[rf][a-z]*\s+/(?!\S)", "递归删除根路径"),
    (r"\brm\s+-[a-z]*[rf][a-z]*\s+/(?:usr|etc|var|bin|boot|lib|opt|sys|proc)\b",
     "递归删除系统目录"),
    (r"\bgit\s+push\b[^\n]*--force(?![-\w])",
     "强制推送会覆盖远端历史；改用 --force-with-lease 并由人工执行"),
    (r"\bgit\s+reset\s+--hard\b", "会丢弃工作区改动；先 git stash，或确认后由人工执行"),
    (r"\bgit\s+clean\s+-[a-z]*f", "会删除未跟踪文件；先用 -n 预演确认范围"),
    (r"\bchmod\s+-R\s+777\b", "递归放开全部权限"),
    (r":\(\)\s*\{.*\};\s*:", "fork 炸弹"),
    (r"\b(?:curl|wget)\b[^|]*\|\s*(?:ba|z|fi)?sh\b",
     "管道执行远程脚本；请人工在终端确认脚本内容后再运行"),
    (r"\bdd\b[^|]*\bof=/dev/", "直接写入块设备"),
    (r"\bmkfs(?:\.[a-z0-9]+)?\s", "格式化文件系统"),
]

COMPILED = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in RULES]


def dangerous(command: str) -> str | None:
    """返回命中的原因，未命中返回 None。"""
    for regex, reason in COMPILED:
        if regex.search(command):
            return reason
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        # 读不懂的事件一律放行：钩子不应该因为自身解析失败而阻断正常工作
        return 0

    if not isinstance(event, dict):
        return 0

    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0

    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    reason = dangerous(command)
    if reason is None:
        return 0

    print(f"已阻止高危命令：{command}", file=sys.stderr)
    print(f"原因：{reason}", file=sys.stderr)
    print("如确需执行，请由用户在终端手动运行。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
