#!/usr/bin/env python3
"""Validate the agent-dev-kit **scaffold layer**.

Scope: everything except src/. See docs/00-boundaries.md — src/ belongs to the
product built on top of this kit and is validated by that project's own
toolchain, not by this script.

Standard library only — frontmatter is parsed with a minimal hand-written parser
so that no PyYAML dependency is required.

Checks:
  1. every skills/*/SKILL.md exists and has name + description in frontmatter
  2. skill name matches its directory name and is kebab-case
  3. skill docs never invoke their own scripts via a bare `scripts/...` path
     (that resolves against the user's project root, not the skill directory)
  4. every skill path referenced from .claude-plugin/marketplace.json exists
  5. plugin sources are well-formed: local paths exist, external sources are
     pinned to a 40-char sha, and no Anthropic-reserved plugin name is used
  6. .claude-plugin/plugin.json is present and agrees with the marketplace entry
  7. hooks/hooks.json and .claude/settings.json point at hook scripts that exist
  8. agents/*.md and commands/*.md have valid frontmatter
  9. relative links in markdown docs resolve to real files
 10. .gitattributes pins line endings to LF
 11. every shebang script under hooks/ scripts/ skills/*/scripts/ is executable
     (read from the git index — that mode is what other clones actually get)
 12. those scripts use LF line endings, so shebangs stay valid
 13. the declared top-level directory layout is intact

Also emits non-fatal notices, e.g. skills that exist but are not registered in
the marketplace manifest.

Exits 1 with a clear report when anything fails.
"""

from __future__ import annotations

import json
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# ---------------------------------------------------------------------------
# 层边界（见 docs/00-boundaries.md）
#
# 本仓库有两层：
#   脚手架层 —— skills/ agents/ commands/ hooks/ scripts/ template/ docs/
#   工程层   —— src/，使用者的业务代码与业务文档
#
# validate.py 属于脚手架层，**只校验脚手架层**。工程层的代码风格、文档链接、
# 测试策略由使用者自己的工具链负责——脚手架不该因为用户产品文档里有个坏链接
# 就判失败，那是越界。任何新增检查都必须跳过 PRODUCT_DIRS。
# ---------------------------------------------------------------------------
PRODUCT_DIRS = {"src"}

errors: list[str] = []
notices: list[str] = []
checks = 0


def fail(message: str) -> None:
    errors.append(message)


def notice(message: str) -> None:
    """提示但不失败——用于「可能是疏忽，但也可能是有意为之」的情况。"""
    notices.append(message)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Minimal YAML frontmatter parser: flat `key: value` pairs only."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"{rel(path)}: 无法读取文件 ({exc})")
        return None

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        fail(f"{rel(path)}: 缺少 YAML frontmatter（首行必须是 '---'）")
        return None

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        fail(f"{rel(path)}: frontmatter 未闭合（缺少结束的 '---'）")
        return None

    data: dict[str, str] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] in (" ", "\t") and current_key:
            data[current_key] = f"{data[current_key]} {raw.strip()}".strip()
            continue
        if ":" not in raw:
            fail(f"{rel(path)}: frontmatter 行无法解析（缺少 ':'）-> {raw!r}")
            continue
        key, _, value = raw.partition(":")
        current_key = key.strip()
        data[current_key] = value.strip().strip("'\"")
    return data


def require_fields(path: Path, data: dict[str, str], fields: tuple[str, ...]) -> None:
    for field in fields:
        if not data.get(field):
            fail(f"{rel(path)}: frontmatter 缺少必需字段 '{field}' 或其值为空")


FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
# 匹配「裸的」scripts/xxx.ext 引用：前面不是 / 或 } 等路径字符，说明没有写全前缀。
BARE_SCRIPT_RE = re.compile(r"(?<![\w/${}.\-])scripts/[\w./\-]+\.(?:py|sh|js|mjs|ts|rb|pl)")
# 仓库自身的维护脚本，技能文档里提到它们是合法的
REPO_SCRIPTS = {
    "scripts/validate.py",
    "scripts/bootstrap.sh",
    "scripts/new_skill.py",
    "scripts/test_hooks.py",
}


def code_block_lines(text: str) -> list[tuple[int, str]]:
    """Return (1-based line number, line) for lines inside fenced code blocks."""
    out: list[tuple[int, str]] = []
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside:
            out.append((number, line))
    return out


def check_skill_script_paths(skill_dir: Path) -> None:
    """技能文档里调用自带脚本时必须写全路径。

    技能执行时的 cwd 是用户的项目根目录，而不是技能目录。写成 `scripts/foo.py`
    会解析到项目自己的 scripts/，导致 file-not-found —— 这是最容易被复制传播的坑，
    所以在校验里挡住。
    """
    global checks
    for doc in sorted(skill_dir.rglob("*.md")):
        checks += 1
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError as exc:
            fail(f"{rel(doc)}: 无法读取文件 ({exc})")
            continue

        for number, line in code_block_lines(text):
            for match in BARE_SCRIPT_RE.finditer(line):
                found = match.group(0)
                if found in REPO_SCRIPTS:
                    continue
                fail(
                    f"{rel(doc)}:{number}: 技能脚本路径不完整 '{found}'。"
                    "技能执行时 cwd 是用户项目根目录，请写成 "
                    f"'${{CLAUDE_PLUGIN_ROOT}}/skills/{skill_dir.name}/{found}'"
                )


def check_skills() -> None:
    global checks
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        fail("skills/ 目录不存在")
        return

    dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    if not dirs:
        fail("skills/ 下没有任何技能目录")

    for skill_dir in dirs:
        checks += 1
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            fail(f"{rel(skill_dir)}: 缺少 SKILL.md")
            continue

        data = parse_frontmatter(skill_md)
        if data is None:
            continue
        require_fields(skill_md, data, ("name", "description"))

        name = data.get("name", "")
        if name and name != skill_dir.name:
            fail(f"{rel(skill_md)}: name '{name}' 与目录名 '{skill_dir.name}' 不一致")
        if name and not KEBAB_RE.match(name):
            fail(f"{rel(skill_md)}: name '{name}' 不符合 kebab-case 规范")

        check_skill_script_paths(skill_dir)


RESERVED_PLUGIN_NAMES = {
    "agent-skills",
    "anthropic-agent-skills",
    "claude-code-plugins",
}
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
REMOTE_SOURCE_TYPES = {"github", "url", "npm", "git-subdir", "archive", "command"}


def check_plugin_source(label: str, source: object, name: object) -> str:
    """Validate a plugin `source`. Returns 'local', 'remote' or 'invalid'."""
    global checks
    checks += 1

    if isinstance(name, str) and name in RESERVED_PLUGIN_NAMES:
        fail(
            f"{label} 使用了 Anthropic 保留插件名 '{name}'，"
            "会被判定为不可信来源而拒绝加载"
        )

    if isinstance(source, str):
        if not source.startswith("./"):
            fail(f"{label} 本地 source 必须以 './' 开头，当前为: {source}")
            return "invalid"
        if not (ROOT / source).is_dir():
            fail(f"{label} 本地 source 路径不存在: {source}")
        return "local"

    if not isinstance(source, dict):
        fail(f"{label} 的 source 必须是字符串路径或对象")
        return "invalid"

    kind = source.get("source")
    if kind not in REMOTE_SOURCE_TYPES:
        fail(
            f"{label} 未知的 source 类型 '{kind}'，"
            f"应为以下之一: {', '.join(sorted(REMOTE_SOURCE_TYPES))}"
        )
        return "invalid"

    required = {"github": "repo", "url": "url", "npm": "package"}.get(kind)
    if required and not source.get(required):
        fail(f"{label} source 类型 '{kind}' 缺少必填字段 '{required}'")

    if kind == "github":
        repo = source.get("repo", "")
        if isinstance(repo, str) and repo and len(repo.split("/")) != 2:
            fail(f"{label} 'repo' 必须是 owner/repo 格式，当前为: {repo}")

    # 外部来源必须锁定到具体 commit，否则上游任何改动都会静默流入本地环境
    if kind in ("github", "url", "git-subdir"):
        sha = source.get("sha")
        if not sha:
            fail(
                f"{label} 外部 source 必须提供 40 位 'sha' 以锁定 commit"
                "（仅用 ref/分支无法复现且存在供应链风险）"
            )
        elif not (isinstance(sha, str) and SHA_RE.match(sha)):
            fail(f"{label} 'sha' 必须是 40 位小写十六进制字符串，当前为: {sha}")

    return "remote"


def check_marketplace() -> None:
    global checks
    manifest = ROOT / ".claude-plugin" / "marketplace.json"
    checks += 1
    if not manifest.is_file():
        fail(".claude-plugin/marketplace.json 不存在")
        return

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{rel(manifest)}: JSON 解析失败 ({exc})")
        return

    for field in ("name", "owner", "plugins"):
        if field not in data:
            fail(f"{rel(manifest)}: 缺少顶层字段 '{field}'")

    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        fail(f"{rel(manifest)}: 'plugins' 必须是非空数组")
        return

    for index, plugin in enumerate(plugins):
        label = f"{rel(manifest)}: plugins[{index}]"
        if not isinstance(plugin, dict):
            fail(f"{label} 必须是对象")
            continue
        for field in ("name", "source"):
            if not plugin.get(field):
                fail(f"{label} 缺少字段 '{field}'")

        kind = check_plugin_source(label, plugin.get("source"), plugin.get("name"))

        skills = plugin.get("skills", []) or []
        if skills and kind == "remote":
            fail(
                f"{label} 使用外部 source，不应再声明本地 'skills' 路径"
                "（外部插件的技能由其自身仓库提供）"
            )
            skills = []

        for skill_path in skills:
            checks += 1
            target = (ROOT / skill_path).resolve()
            if not target.is_dir():
                fail(f"{label} 引用的技能路径不存在: {skill_path}")
            elif not (target / "SKILL.md").is_file():
                fail(f"{label} 引用的技能缺少 SKILL.md: {skill_path}")


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        fail(f"{rel(path)} 不存在")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{rel(path)}: JSON 解析失败 ({exc})")
        return None
    if not isinstance(data, dict):
        fail(f"{rel(path)}: 顶层必须是对象")
        return None
    return data


def check_plugin_manifest() -> None:
    """插件自身的清单，缺失时以插件方式安装会丢掉元信息。"""
    global checks
    checks += 1
    manifest = ROOT / ".claude-plugin" / "plugin.json"
    data = load_json(manifest)
    if data is None:
        return

    for field in ("name", "description", "version"):
        if not data.get(field):
            fail(f"{rel(manifest)}: 缺少字段 '{field}' 或其值为空")

    name = data.get("name", "")
    if name and not KEBAB_RE.match(name):
        fail(f"{rel(manifest)}: name '{name}' 不符合 kebab-case 规范")

    # 与 marketplace 中的本地插件条目对齐，避免两份元信息各说各话
    market = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    if not market:
        return
    local = [
        p
        for p in market.get("plugins", [])
        if isinstance(p, dict) and isinstance(p.get("source"), str)
    ]
    for plugin in local:
        if plugin.get("name") != name:
            continue
        if plugin.get("description") != data.get("description"):
            fail(
                "plugin.json 与 marketplace.json 的 description 不一致"
                f"（插件 '{name}'）"
            )
        return
    fail(
        f"marketplace.json 中没有与 plugin.json 同名的本地插件条目 '{name}'"
    )


HOOK_PATH_RE = re.compile(
    r"\$\{?(?:CLAUDE_PLUGIN_ROOT|CLAUDE_PROJECT_DIR)\}?/([^\s\"']+)"
)


def hook_command_path(command: str) -> Path | None:
    """把钩子命令里的变量引用还原成仓库内的真实路径。

    命令形如 `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/pre_tool_use.py"`，
    路径不一定在开头，所以在整条命令里搜索变量引用。
    """
    match = HOOK_PATH_RE.search(command)
    if match is None:
        return None
    return ROOT / match.group(1)


def iter_hook_commands(data: dict) -> list[str]:
    commands: list[str] = []
    for matchers in (data.get("hooks") or {}).values():
        if not isinstance(matchers, list):
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict):
                continue
            for hook in matcher.get("hooks") or []:
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    commands.append(hook["command"])
    return commands


def check_hooks() -> None:
    """hooks.json 让钩子能随插件分发；settings.json 只在本仓库内生效。"""
    global checks

    for relative, required in ((Path("hooks/hooks.json"), True),
                               (Path(".claude/settings.json"), True)):
        checks += 1
        path = ROOT / relative
        if not path.is_file():
            if required:
                fail(f"{relative} 不存在")
            continue

        data = load_json(path)
        if data is None:
            continue

        commands = iter_hook_commands(data)
        if not commands:
            fail(f"{relative}: 未注册任何钩子命令")

        for command in commands:
            checks += 1
            target = hook_command_path(command)
            if target is None:
                fail(
                    f"{relative}: 钩子命令必须用 ${{CLAUDE_PLUGIN_ROOT}} 或 "
                    f"${{CLAUDE_PROJECT_DIR}} 引用脚本路径，保证任意 cwd 下可用"
                    f" -> {command}"
                )
            elif not target.is_file():
                fail(f"{relative}: 钩子脚本不存在 -> {command}")


def git_index_modes() -> dict[str, int] | None:
    """读取 git 索引里记录的文件模式。

    以索引为准而不是文件系统：真正决定别人克隆后拿到什么的是提交进去的模式。
    本地 chmod 了但没落到索引，别人 clone 下来依然是不可执行的——而钩子
    不可执行是静默失效，最难被发现。
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-s", "-z"],
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None

    modes: dict[str, int] = {}
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) < 3 or not path:
            continue
        try:
            modes[path] = int(parts[0], 8)
        except ValueError:
            continue
    return modes


IGNORED_DIRS = {"__pycache__", ".venv", "venv", "node_modules", ".git"}


def script_paths() -> list[Path]:
    roots = [ROOT / "hooks", ROOT / "scripts"]
    roots.extend(sorted((ROOT / "skills").glob("*/scripts")))
    found: list[Path] = []
    for directory in roots:
        if not directory.is_dir():
            continue
        found.extend(
            sorted(
                p
                for p in directory.rglob("*")
                if p.is_file() and not IGNORED_DIRS.intersection(p.parts)
            )
        )
    return found


def has_shebang(path: Path) -> bool | None:
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"#!"
    except OSError as exc:
        fail(f"{rel(path)}: 无法读取文件 ({exc})")
        return None


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# template/ 里的链接指向「技能生成之后」才存在的文件，天然无法在原地解析。
# src/ 属于工程层，不在脚手架校验范围内（见文件顶部的层边界说明）。
LINK_SKIP_DIRS = {"template", ".git", "node_modules", "__pycache__"} | PRODUCT_DIRS


def check_doc_links() -> None:
    """**脚手架层**文档里的相对链接必须指向真实存在的文件。

    文件改名后忘记更新引用是文档腐化最常见的形式，而且没人会主动去点每个链接。
    """
    global checks
    for doc in sorted(ROOT.rglob("*.md")):
        if LINK_SKIP_DIRS.intersection(doc.relative_to(ROOT).parts):
            continue
        checks += 1
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK_RE.findall(line):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                path = target.split("#")[0].strip()
                if not path:
                    continue
                if not (doc.parent / path).exists():
                    fail(f"{rel(doc)}:{number}: 链接指向的文件不存在 -> {target}")


def check_skill_registration() -> None:
    """技能存在但未在 marketplace 登记时提示（不失败）。

    登记与否是有意选择——本地实验性技能可以不登记。但「写完忘了登记，
    分发出去缺技能」也很常见，所以这里提示一下。
    """
    skills_dir = ROOT / "skills"
    manifest = ROOT / ".claude-plugin" / "marketplace.json"
    if not skills_dir.is_dir() or not manifest.is_file():
        return

    data = load_json(manifest)
    if not data:
        return

    registered = set()
    for plugin in data.get("plugins", []):
        if not isinstance(plugin, dict):
            continue
        for path in plugin.get("skills") or []:
            if isinstance(path, str):
                registered.add(path.rstrip("/").split("/")[-1])

    present = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    for name in sorted(present - registered):
        notice(
            f"技能 '{name}' 未登记到 marketplace.json 的 skills 数组，"
            "不会随插件分发（若是有意为之可忽略）"
        )


def check_gitattributes() -> None:
    """换行规则必须固定在 .gitattributes 里，而不是靠每个人的 git 配置。"""
    global checks
    checks += 1

    attributes = ROOT / ".gitattributes"
    if not attributes.is_file():
        fail(".gitattributes 不存在（需要它固定换行符为 LF）")
        return

    text = attributes.read_text(encoding="utf-8")
    for rule in (r"^\*\s+text=auto\s+eol=lf", r"^\*\.sh\s+text\s+eol=lf",
                 r"^\*\.py\s+text\s+eol=lf"):
        checks += 1
        if not re.search(rule, text, re.M):
            fail(f".gitattributes 缺少换行规则: {rule.strip('^')}")


def check_executables() -> None:
    """带 shebang 的脚本必须有可执行位，否则 clone 后钩子会静默失效。"""
    global checks
    index_modes = git_index_modes()

    for path in script_paths():
        if not has_shebang(path):
            continue

        checks += 1
        key = rel(path).replace("\\", "/")
        if index_modes is not None and key in index_modes:
            if not index_modes[key] & 0o111:
                fail(
                    f"{key}: 带 shebang 但 git 中记录为不可执行"
                    f"（修复: git update-index --chmod=+x {key}）"
                )
            continue

        # 尚未纳入 git 的新文件：回退到文件系统权限位
        if not path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            fail(
                f"{key}: 带 shebang 但缺少可执行权限（修复: chmod +x {key}）"
            )


def git_head_tags() -> list[str]:
    """HEAD 上的 tag 列表。不在 git 仓库里、或 git 不可用时返回空列表。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "tag", "--points-at", "HEAD"],
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_version_tag() -> None:
    """HEAD 上若打了 tag，它必须与 plugin.json 的 version 一致。

    版本号的唯一真实来源是 plugin.json。tag 与它分裂时两边都不会报错——
    按 tag 发布的人和按 marketplace 安装的人看到的版本号却不一样，只能靠
    这里拦。HEAD 上没有 tag 是日常开发的常态，直接跳过。
    """
    global checks

    manifest = ROOT / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return  # 缺失由 check_plugin_manifest 报告，不重复计数
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return  # 同上
    if not isinstance(data, dict):
        return
    version = data.get("version")
    if not version:
        return

    tags = git_head_tags()
    if not tags:
        return

    checks += 1
    accepted = {str(version), f"v{version}"}
    if not accepted & set(tags):
        listed = ", ".join(sorted(tags))
        fail(
            f"HEAD 上的 tag（{listed}）与 {rel(manifest)} 的 version "
            f"'{version}' 不一致。要么改清单版本号，要么重打 tag："
            f"git tag -d <tag> && git tag -a v{version} -m 'release v{version}'"
        )


def check_line_endings() -> None:
    """脚本必须用 LF。

    CRLF 会让 shebang 变成 '#!/usr/bin/env bash\\r'，报 'bad interpreter'。
    .gitattributes 已强制 LF，这里做兜底校验（例如有人用编辑器另存为 CRLF）。
    """
    global checks
    for path in script_paths():
        # 只关心带 shebang 的可执行脚本；无 shebang 或读取失败都跳过
        if not has_shebang(path):
            continue
        checks += 1
        try:
            if b"\r\n" in path.read_bytes():
                fail(
                    f"{rel(path)}: 含 CRLF 换行，会导致 'bad interpreter' 错误。"
                    "请转换为 LF（见根目录 .gitattributes）"
                )
        except OSError as exc:
            fail(f"{rel(path)}: 无法读取文件 ({exc})")


def check_layout() -> None:
    """目录约定见 CLAUDE.md，缺目录说明结构被改动过。"""
    global checks
    for dirname in ("skills", "agents", "commands", "hooks", "scripts",
                    "template", "docs", "src"):
        checks += 1
        if not (ROOT / dirname).is_dir():
            fail(f"{dirname}/ 目录不存在（见 CLAUDE.md 的目录职责表）")


def check_markdown_dir(dirname: str, fields: tuple[str, ...]) -> None:
    global checks
    directory = ROOT / dirname
    if not directory.is_dir():
        fail(f"{dirname}/ 目录不存在")
        return

    files = sorted(p for p in directory.glob("*.md") if p.name != "README.md")
    if not files:
        fail(f"{dirname}/ 下没有任何定义文件")

    for path in files:
        checks += 1
        data = parse_frontmatter(path)
        if data is None:
            continue
        require_fields(path, data, fields)

        name = data.get("name", "")
        if name and name != path.stem:
            fail(f"{rel(path)}: name '{name}' 与文件名 '{path.stem}' 不一致")
        if name and not KEBAB_RE.match(name):
            fail(f"{rel(path)}: name '{name}' 不符合 kebab-case 规范")


def main() -> int:
    print("校验 agent-dev-kit 仓库结构...\n")

    check_layout()
    check_skills()
    check_marketplace()
    check_plugin_manifest()
    check_version_tag()
    check_hooks()
    check_skill_registration()
    check_doc_links()
    check_gitattributes()
    check_markdown_dir("agents", ("name", "description"))
    check_markdown_dir("commands", ("name", "description"))
    check_executables()
    check_line_endings()

    if errors:
        print(f"✗ 校验失败，发现 {len(errors)} 个问题：\n")
        for error in errors:
            print(f"  - {error}")
        print()
        return 1

    print(f"✓ 全部通过（共执行 {checks} 项检查）")
    if notices:
        print(f"\n提示（不影响校验通过，共 {len(notices)} 条）：")
        for item in notices:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
