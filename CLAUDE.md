<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
rtk uv run <cmd>        # Compact uv project command output
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->

---

# Agent 开发基座 — 项目约定

本仓库是「Claude Code 工程实践 / Agent 开发基座」脚手架，提供可复用、可分发的
skills / agents / commands / hooks / MCP 骨架。

## 适用范围（先读这段）

仓库里住着**两层**，本文件**只约束脚手架层**：

| 层 | 范围 | 规范写在哪 |
| --- | --- | --- |
| **脚手架层** | `skills/` `agents/` `commands/` `hooks/` `scripts/` `template/` `docs/` | **本文件** |
| **工程层** | `src/`——使用者的业务代码与业务文档 | `src/CLAUDE.md`（只在动 `src/` 时加载） |

硬规则：**`make validate` 与 `make test` 永不进入 `src/`**
（`scripts/validate.py` 顶部的 `PRODUCT_DIRS` 常量），反过来工程层的 CI 也不该去
校验 `SKILL.md`。新增校验项时先问：这条规则约束的是哪一层？

不要把产品的架构、技术栈、编码规范写进本文件——那些属于 `src/CLAUDE.md`。
写在这里的代价是每一轮对话都要为它付 token，哪怕本次只是在改一个技能的
description。完整说明见 `docs/00-boundaries.md`。

## 目录职责

| 目录 | 职责 |
| --- | --- |
| `src/` | **工程层**——业务代码，边界见上，规范见 `src/CLAUDE.md` |
| `skills/` | 技能，每个技能一个目录，含 `SKILL.md` |
| `agents/` | 子 agent 定义，单个 `.md` + frontmatter |
| `commands/` | 斜杠命令，单个 `.md`，支持 `$ARGUMENTS` |
| `hooks/` | 生命周期钩子脚本 + `hooks.json` 注册清单 |
| `scripts/` | 仓库维护脚本（校验、测试、脚手架生成、环境安装） |
| `template/` | 新技能模板 |
| `docs/` | 中文文档 |
| `.claude-plugin/` | `plugin.json`（插件元信息）+ `marketplace.json`（市场清单） |

`src/` 与 `scripts/` 的分界：**产品的一部分**进 `src/`（工程层），
**维护仓库或技能的工具**进 `scripts/`（脚手架层）。详见 `src/README.md`。

## 新增技能规范

1. 用脚手架生成，不要手工建目录：`python3 scripts/new_skill.py <skill-name>`
2. `SKILL.md` 的 frontmatter 只需 `name` 和 `description` 两个字段。
3. `name` 必须为 kebab-case，且与目录名完全一致，全仓库唯一。
4. `description` 必须同时写清「做什么」和「何时触发」——这是模型检索技能的唯一入口。
5. 正文保持精简；详细参数、边界情况放入 `references/`，确定性逻辑写成 `scripts/`。
6. **调用技能自带脚本必须写全路径**：

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/scripts/xxx.py"
   ```

   技能执行时 cwd 是**用户的项目根目录**，不是技能目录。写成 `scripts/xxx.py`
   会解析到项目自己的 `scripts/`，必然 file-not-found。`validate.py` 会拦截这种写法。
7. 需随插件分发时，在 `.claude-plugin/marketplace.json` 的 `skills` 数组登记路径。

## 外部技能仓库

引用第三方技能集时**不要 vendoring**（复制代码进本仓库），一律在
`marketplace.json` 里用 `github` source 引用，并且**必须用 40 位 `sha` 锁定 commit**
——只写分支名会被 `validate.py` 直接判为失败。新增的外部插件默认写
`"defaultEnabled": false`，避免平白增加常驻上下文成本。

选型结论与风险说明见 `docs/05-external-skills.md`。注意：不要在本仓库运行
`setup-matt-pocock-skills` 技能，它会改写 CLAUDE.md 并破坏上方 rtk 保护区块。

## 命名约定

- 技能目录 / agent 文件名 / 命令文件名：一律 kebab-case。
- agent 与 command 的 frontmatter `name` 必须与文件名（去掉 `.md`）一致。
- Python 脚本文件名用 snake_case（`new_skill.py`、`pre_tool_use.py`）。
- Shell 脚本以 `#!/usr/bin/env bash` 开头，并 `set -euo pipefail`。
- 所有带 shebang 的脚本需有可执行位，且必须落到 **git 索引**——只在本地 `chmod`
  别人 clone 下来依然不可执行。用 `git update-index --chmod=+x <path>` 修复。
- 文档用中文撰写；代码、配置、标识符一律用英文。

## 平台与工具链约定

支持 **Linux / macOS / WSL2**，不支持原生 Windows。CI 在 ubuntu 与 macos 上跑
同一套测试，并额外用 Python 3.8 跑一遍。

**只承诺能验证的东西。** 没有对应 CI runner 或本地复现手段的平台/功能，宁可明确
不支持，也不要提供一套没跑通过的兼容路径——尤其是钩子，它失效时是静默的。

- **新增可执行逻辑一律用 Python**，不要用 shell：规则/逻辑能被测试逐条断言，
  也不必和 shell 的引号与转义陷阱搏斗。当前只有 `scripts/bootstrap.sh` 是 bash。
- 只用 Python 标准库，不引入第三方依赖；最低版本 **3.8**（CI 会用 3.8 跑一遍）。
- 写文件时显式指定 LF：`open(path, "w", encoding="utf-8", newline="\n")`。
  注意 `Path.write_text(newline=...)` 是 3.10+ 才有的参数，不能用。
- 路径拼接用 `pathlib`，不要手写 `/` 分隔符。
- 判断脚本可执行位要读 **git 索引**，不要读文件系统——本地 `chmod` 了但没落到
  索引，别人 clone 下来依然不可执行。

## 环境准备

新克隆仓库后执行一次（幂等，可重复运行）：

```bash
make setup     # 等价于 bash scripts/bootstrap.sh
```

支持 Linux / macOS / WSL2。**不支持原生 Windows**——`bootstrap.sh` 检测到会直接
报错并给出 WSL2 指引。详见 `docs/01-getting-started.md` 的「运行环境」一节。

它会自动安装 rtk 与 codegraph、生成本地配置、修复脚本执行位并跑校验。
rtk / cgc 缺失不影响核心功能，脚本会降级提醒而非报错。

## 提交前必做

```bash
make validate  # python3 scripts/validate.py —— 结构校验
make test      # 钩子 + release notes 测试；末尾自动调用 test-product（若已定义）
```

两者都必须通过才能提交。`validate.py` 覆盖：

- 顶层目录布局完整
- SKILL.md frontmatter、name 与目录名一致性、kebab-case
- 技能文档里调用自带脚本时写了完整路径
- marketplace 引用路径存在、外部来源锁定 40 位 sha、未占用保留插件名
- plugin.json 与 marketplace 元信息一致
- HEAD 上若打了 tag，与 plugin.json 的 `version` 一致（版本号以 plugin.json 为准）
- `hooks.json` 与 `.claude/settings.json` 注册的钩子脚本真实存在
- 文档里的相对链接指向真实存在的文件
- `.gitattributes` 固定了 LF 换行规则
- agents / commands 的 frontmatter
- 带 shebang 的脚本具备可执行位（读 git 索引）且使用 LF 换行

失败时打印具体的文件、行号与修复命令。另有不影响通过的**提示**，例如技能未登记
到 marketplace。排障见 `docs/06-troubleshooting.md`。

## 发布流程

版本号的**唯一真实来源**是 `.claude-plugin/plugin.json` 的 `version`。发布一个版本：

1. 改 `plugin.json` 与 `marketplace.json` 的 `version`（两份必须一致，`validate.py` 会查）。
2. 在 `CHANGELOG.md` 顶部补一节 `## [x.y.z] - YYYY-MM-DD`——**没有这一节，
   release job 会失败**，因为 Release 正文直接由它生成。
3. `make validate && make test`，提交。
4. `git tag -a vx.y.z -m "release vx.y.z" && git push origin vx.y.z`。

推 tag 触发 `.github/workflows/release.yml`：重跑校验与测试 → 用
`scripts/release_notes.py` 从 CHANGELOG 抽出对应小节 → `gh release create`。
tag 与 `plugin.json` 的 version 对不上时校验会失败，Release 不会被创建。

不要手写 Release 正文——那等于让同一份变更说明存在两个版本。

## 钩子的两套注册方式

- `hooks/hooks.json` —— 随插件分发，安装到其他项目后自动生效，路径用
  `${CLAUDE_PLUGIN_ROOT}` 前缀。
- `.claude/settings.json` —— 只在本仓库内生效，路径用 `$CLAUDE_PROJECT_DIR` 前缀。

两份都保留是刻意的：在本仓库开发时靠 settings.json，分发出去时靠 hooks.json。
若同时命中（在本仓库里又装了本插件），钩子会执行两次，行为幂等、无副作用。
新增钩子脚本时**两处都要登记**，否则会出现「本地有效、装到别处失效」的静默差异。

## MCP 服务器

`.mcp.json` 中配置了项目级 MCP 服务器：

- **codegraph**（`cgc mcp start`）——把代码库索引成图数据库，提供跨文件的符号、
  调用关系与依赖上下文。使用 KuzuDB 嵌入式后端，无需额外启动数据库服务。
  首次使用前需建立索引：`cgc --database kuzudb --path ./.cgc/graph.kuzu index .`
  优先用它做符号查找、调用链追踪、依赖分析，而不是全仓库 grep。
- **filesystem** / **github**——标准 MCP 参考实现，github 需要设置
  `GITHUB_PERSONAL_ACCESS_TOKEN` 环境变量。

## 工具约定

- 执行 shell 命令时优先加 `rtk` 前缀以压缩输出（详见上方 RTK 说明）。
- 检索代码符号与调用关系时优先用 codegraph MCP 工具，其次才是 grep / glob。
