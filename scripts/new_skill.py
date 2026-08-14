#!/usr/bin/env python3
"""从 template/SKILL.md 生成新技能骨架。

用法: python3 scripts/new_skill.py <skill-name>

纯标准库，在 Windows / macOS / Linux 上行为一致。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

USAGE_TEMPLATE = """# {name} — 进阶用法

在此记录详细参数、边界情况与常见问题。SKILL.md 只保留主流程，
细节放在这里按需加载（progressive disclosure）。

## 脚本路径

技能执行时的工作目录是**用户的项目根目录**，不是技能目录。调用自带脚本时
必须写全路径：

```bash
python3 "${{CLAUDE_PLUGIN_ROOT}}/skills/{name}/scripts/xxx.py"
```

## 参数说明

待补充。

## 常见问题

待补充。
"""


def write_lf(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def die(message: str) -> None:
    print(f"错误: {message}", file=sys.stderr)
    raise SystemExit(1)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("用法: python3 scripts/new_skill.py <skill-name>", file=sys.stderr)
        print("示例: python3 scripts/new_skill.py generate-changelog", file=sys.stderr)
        return 1

    name = argv[0]
    if not KEBAB_RE.match(name):
        die(f"技能名 '{name}' 不符合 kebab-case 规范"
            "（只允许小写字母、数字和单个连字符）")

    skill_dir = ROOT / "skills" / name
    if skill_dir.exists():
        die(f"技能目录已存在: skills/{name}")

    template = ROOT / "template" / "SKILL.md"
    if not template.is_file():
        die("模板文件不存在: template/SKILL.md")

    text = template.read_text(encoding="utf-8")
    # 替换 frontmatter 的 name，以及正文示例里的技能路径占位符
    text = re.sub(r"^name: skill-name$", f"name: {name}", text, count=1, flags=re.M)
    text = text.replace("skills/skill-name/", f"skills/{name}/")

    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "scripts").mkdir(parents=True)

    # 显式用 LF 写入：Windows 上默认换行是 CRLF，会让生成的技能一提交就
    # 违反仓库的换行约定（见 .gitattributes 与 validate.py 的换行检查）。
    # 不用 Path.write_text(newline=...)，那个参数 Python 3.10 才有。
    write_lf(skill_dir / "SKILL.md", text)
    write_lf(skill_dir / "references" / "USAGE.md", USAGE_TEMPLATE.format(name=name))
    write_lf(skill_dir / "scripts" / ".gitkeep", "")

    print(f"✓ 已创建技能骨架: skills/{name}")
    print()
    print("后续步骤:")
    print(f"  1. 编辑 skills/{name}/SKILL.md，填写 description（做什么 + 何时触发）")
    print("  2. 补充 references/USAGE.md 的细节内容")
    print("  3. 如需确定性执行逻辑，在 scripts/ 下添加脚本")
    print("     调用时写全路径: ${CLAUDE_PLUGIN_ROOT}/skills/" + name + "/scripts/...")
    print("  4. 如需随插件分发，在 .claude-plugin/marketplace.json 登记路径")
    print("  5. 运行 python3 scripts/validate.py 校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
