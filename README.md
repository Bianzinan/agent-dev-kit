# agent-dev-kit

[![validate](https://github.com/Bianzinan/agent-dev-kit/actions/workflows/validate.yml/badge.svg)](https://github.com/Bianzinan/agent-dev-kit/actions/workflows/validate.yml)
[![release](https://github.com/Bianzinan/agent-dev-kit/actions/workflows/release.yml/badge.svg)](https://github.com/Bianzinan/agent-dev-kit/actions/workflows/release.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Claude Code 工程实践 / Agent 开发基座脚手架**

把散落在各个项目里的 Agent 配置——技能、子 agent、斜杠命令、安全钩子、MCP 服务器
——收敛成一个标准骨架，并用可执行的校验脚本保证约定不腐化。可以整包装进任意项目，
也可以直接 fork 成新工程的起点。

## 能力一览

| 能力 | 内容 | 目录 |
| --- | --- | --- |
| 📦 插件市场 | 本仓库即市场，一条命令装到任意项目 | `.claude-plugin/` |
| 🧠 技能 | `example-skill`——演示渐进披露 + 确定性脚本两种模式 | `skills/` |
| 🤖 子 Agent | `code-reviewer`、`test-runner` | `agents/` |
| ⌨️ 斜杠命令 | `/review`、`/ship` | `commands/` |
| 🛡️ 安全钩子 | 拦截高危 shell 命令，31 个回归用例，随插件分发 | `hooks/` |
| 🔌 MCP | codegraph 代码图谱 + filesystem + github | `.mcp.json` |
| ✅ 结构校验 | 本地与 CI 共用一份 `validate.py`，60+ 项检查 | `scripts/` |
| 🚀 发布流水线 | 打 tag 自动校验、抽 CHANGELOG、建 GitHub Release | `.github/workflows/` |
| 📁 工程代码位 | `src/` 放业务代码，与 Agent 配置彻底分离 | `src/` |

## 快速开始

### 用法 A · 作为插件安装（已有工程，推荐）

在 Claude Code 里执行：

```
/plugin marketplace add Bianzinan/agent-dev-kit
/plugin install agent-dev-kit
```

装完 `skills/`、`agents/`、`commands/` 立即可用，`hooks/hooks.json` 注册的安全钩子
同时生效。两个工程物理隔离，不存在文档与规范混在一起的问题。

### 用法 B · 作为工程基座 fork（新项目）

```bash
git clone https://github.com/Bianzinan/agent-dev-kit.git my-product
cd my-product
make setup            # 幂等：装工具链 + 生成本地配置 + 修可执行位 + 跑校验
```

你的业务代码放 `src/`。这种用法下务必先读 [00 · 层边界](docs/00-boundaries.md)。

## 命令速查

```bash
make help                      # 列出全部命令
```

| 命令 | 作用 | 等价调用 |
| --- | --- | --- |
| `make setup` | 一键安装工具链并初始化（幂等） | `bash scripts/bootstrap.sh` |
| `make check` | 只检查环境，不安装、不写文件 | `bash scripts/bootstrap.sh --check` |
| `make validate` | 校验仓库结构（**提交前必跑**） | `python3 scripts/validate.py` |
| `make test` | 脚手架回归测试 + 工程层 `test-product`（定义了才跑） | `python3 scripts/test_hooks.py`<br>`python3 scripts/test_release_notes.py` |
| `make new-skill NAME=x` | 从模板生成新技能 | `python3 scripts/new_skill.py x` |
| `make index` | 建立 codegraph 代码图谱索引 | `cgc --database kuzudb --path ./.cgc/graph.kuzu index .` |
| `make lint` | shellcheck + Python 语法检查 | 见 `Makefile` |
| `make clean` | 清理 `.cgc/` 与 `__pycache__/` | — |

安装脚本的常用变体：

```bash
bash scripts/bootstrap.sh --skip-rtk         # 跳过某个可选工具
bash scripts/bootstrap.sh --skip-codegraph
bash scripts/bootstrap.sh --index            # 安装后顺便建索引
```

rtk 与 codegraph 都是**可选增强**，安装失败不影响校验与技能功能，脚本只提醒不中断。

## 常见任务

### 新增一个技能

```bash
make new-skill NAME=my-skill
$EDITOR skills/my-skill/SKILL.md      # 重点写 description：做什么 + 何时触发
make validate
```

技能里调用自带脚本必须写全路径，否则会解析到用户项目自己的 `scripts/`：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/my-skill/scripts/run.py"
```

需要随插件分发时，在 `.claude-plugin/marketplace.json` 的 `skills` 数组登记路径。
详见 [02 · 编写技能](docs/02-writing-skills.md)。

### 新增一个子 Agent

```bash
cat > agents/my-agent.md <<'EOF'
---
name: my-agent
description: 一句话说明做什么、何时该被调用。
tools: Read, Grep, Glob, Bash
model: inherit
---

系统提示词正文。
EOF
make validate                          # 校验 frontmatter 与文件名一致性
```

`name` 必须与文件名（去掉 `.md`）一致，且为 kebab-case。斜杠命令同理，放 `commands/`，
正文里用 `$ARGUMENTS` 接收参数。

### 新增一个钩子

```bash
$EDITOR hooks/my_hook.py
chmod +x hooks/my_hook.py
git update-index --chmod=+x hooks/my_hook.py   # 可执行位必须落到 git 索引
```

**两处都要登记**，否则会出现「本地有效、装到别处失效」的静默差异：

| 文件 | 生效范围 | 路径前缀 |
| --- | --- | --- |
| `hooks/hooks.json` | 随插件分发到其他项目 | `${CLAUDE_PLUGIN_ROOT}` |
| `.claude/settings.json` | 只在本仓库内 | `$CLAUDE_PROJECT_DIR` |

再到 `scripts/test_hooks.py` 补上「该拦」和「不该拦」两类用例——黑名单误伤和漏网
一样是缺陷。

### 引入外部技能仓库

不要 vendoring（复制代码进本仓库），在 `marketplace.json` 里用 `github` source 引用，
并且**必须锁定 40 位 sha**：

```bash
git ls-remote https://github.com/owner/repo refs/heads/main    # 取当前 sha
```

```jsonc
{
  "name": "their-skills",
  "description": "……。可选安装。",
  "source": { "source": "github", "repo": "owner/repo", "sha": "<40 位 sha>" },
  "defaultEnabled": false          // 默认关闭，避免平白增加常驻上下文成本
}
```

只写分支名会被 `validate.py` 直接判失败。选型标准见
[05 · 集成外部技能仓库](docs/05-external-skills.md)。

### 发布一个版本

版本号的唯一真实来源是 `.claude-plugin/plugin.json` 的 `version`。

```bash
# 1. 改 plugin.json 与 marketplace.json 的 version（两份必须一致）
# 2. CHANGELOG.md 顶部补一节 `## [x.y.z] - YYYY-MM-DD`
make validate && make test
git commit -am "chore: bump to x.y.z"
git tag -a vx.y.z -m "release vx.y.z"
git push origin main && git push origin vx.y.z
```

推 tag 触发 [release workflow](.github/workflows/release.yml)：重跑校验与测试 →
用 `scripts/release_notes.py` 从 CHANGELOG 抽出对应小节 → 创建 GitHub Release。
两道闸门会拦住不一致的发布——tag 与 `version` 不符、或 CHANGELOG 缺对应小节，
都不会产出 Release。

## 目录结构

```
agent-dev-kit/
├── .claude-plugin/     # plugin.json（插件元信息）+ marketplace.json（市场清单）
├── .claude/            # settings.json 团队共享配置（权限 + hooks 注册）
├── skills/             # 技能，一技能一目录，含 SKILL.md
├── agents/             # 子 agent 定义，单个 .md + frontmatter
├── commands/           # 斜杠命令，单个 .md，支持 $ARGUMENTS
├── hooks/              # 钩子脚本 + hooks.json 注册清单
├── scripts/            # 仓库维护脚本：校验 / 测试 / 脚手架 / 安装 / release notes
├── template/           # 新技能模板
├── docs/               # 中文文档（脚手架层）
├── src/                # 工程层——你的业务代码，规范见 src/CLAUDE.md
├── .mcp.json           # 项目级 MCP 服务器配置
├── .gitattributes      # 固定 LF，避免 shebang 被 CRLF 破坏
├── Makefile            # 命令入口（脚手架层）
├── Makefile.product.example  # 工程层 make 目标模板，复制为 Makefile.product
├── CLAUDE.md           # 给 Claude 的项目级指令（只约束脚手架层）
└── CHANGELOG.md
```

### 两层边界

仓库里住着**两层**，文档与校验各归各的：

| | 脚手架层 | 工程层 |
| --- | --- | --- |
| 代码 | `skills/` `agents/` `commands/` `hooks/` `scripts/` `template/` | `src/` |
| 规范 | `CLAUDE.md`、`docs/` | `src/CLAUDE.md`（只在动 `src/` 时加载） |
| 校验 | `make validate` / `make test` | 你自己的 lint / test，挂到 `Makefile.product` |

硬规则：**`make validate` 与 `make test` 永不进入 `src/`**。脚手架不会因为你产品
文档里有个坏链接就判失败。

工程层的 make 目标写在 **`Makefile.product`**（`cp Makefile.product.example Makefile.product`），
根 `Makefile` 属于脚手架层、升级时会被覆盖。其中 `test-product` 是约定名——`make test`
跑完脚手架测试后会自动调用它，**没定义就跳过**：

```bash
make test     # 脚手架 31+13 个用例 → 再跑 test-product（若已定义）
```

完整说明见 [00 · 层边界](docs/00-boundaries.md)。

## 内置能力

| 类型 | 名称 | 说明 |
| --- | --- | --- |
| 技能 | `example-skill` | 从 git 历史生成结构化变更日志 |
| 子 Agent | `code-reviewer` | 审查改动，按 Blocking / Warning / Info 分级，只报高置信度问题 |
| 子 Agent | `test-runner` | 自动探测测试命令并运行，通过时一行摘要，失败时完整诊断 |
| 命令 | `/review [范围]` | 对当前改动执行代码审查 |
| 命令 | `/ship [说明]` | 提交前完整检查：**先判断改动落在哪一层**，跑该层的校验与测试 → 审查 → 生成提交信息 |
| MCP | `codegraph` | 代码图谱索引，符号查找 / 调用链 / 死代码 / 圈复杂度等 [25 个工具](https://github.com/Shashankss1205/CodeGraphContext/blob/main/docs/MCP_TOOLS.md) |
| MCP | `filesystem` | 标准文件系统访问 |
| MCP | `github` | GitHub 集成，需设置 `GITHUB_PERSONAL_ACCESS_TOKEN` |

## 运行环境

支持 **Linux / macOS / WSL2**，**不支持原生 Windows**——`bootstrap.sh` 检测到会直接
报错并给出 WSL2 指引。这是刻意的：没有 Windows 机器可做验证，而钩子在 Windows 上
失效是**静默**的，用户会以为有防护。

必需依赖只有三个：**git**、**Python ≥ 3.8**（仅标准库，无需 pip 装包）、**Claude Code**。
Bash / Node.js / make / rtk / cgc 均为可选。完整依赖表、WSL2 安装步骤与手动安装
工具链见 [01 · 快速开始](docs/01-getting-started.md)。

## 校验与测试

> **先分清是谁的提交。** `make validate` 校验的是**脚手架层**——SKILL.md 格式、
> 钩子注册、marketplace 清单。它与你的业务代码无关，也**永远不会进入 `src/`**。
> 用它去卡一次纯业务提交是层混淆，不是质量把关。

| 你在提交什么 | 该跑什么 |
| --- | --- |
| 业务代码（`src/`，或用法 A 下你自己仓库里的代码） | `make test`（会调用你的 `test-product`）+ 你自己的 lint / typecheck |
| 技能、子 agent、命令、钩子、脚手架脚本 | `make validate && make test` |
| 两者都动了 | 两套都跑，并建议拆成两次提交 |

`make test` 是**两层共用的入口**：先跑脚手架回归测试，再调用 `Makefile.product` 里的
`test-product`（没定义就跳过）。`make validate` 则纯属脚手架层。

`/ship` 命令会自动做这个判断：先看改动落在哪一层，再决定跑哪套检查；以插件方式
安装、仓库里根本没有 `scripts/validate.py` 时，它会静默跳过脚手架校验而不是报错。

### 脚手架层的检查

```bash
make validate && make test     # CI 跑的是同一份脚本，本地过了 CI 就会过
```

`validate.py` 覆盖目录布局、SKILL.md frontmatter 与命名一致性、技能脚本全路径写法、
marketplace 引用与外部 sha 锁定、plugin.json 版本一致性、钩子注册、文档相对链接、
LF 换行、脚本可执行位（读 **git 索引**——那才是别人克隆后拿到的模式）。失败时打印
具体文件、行号与修复命令；另有不影响通过的**提示**，例如技能存在但未登记到 marketplace。

`make test` 的脚手架部分对钩子跑 31 个用例，两个方向都覆盖：高危命令必须拦、日常命令
（`git push --force-with-lease`、`rm -rf ./node_modules` 等）必须放行，另含畸形输入
用例确保解析失败时放行而非阻断。

完整校验项清单见 [CLAUDE.md](CLAUDE.md)，失败对照表见 [06 · 排障](docs/06-troubleshooting.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [00 · 层边界](docs/00-boundaries.md) | 脚手架层与工程层怎么分，**建议先读** |
| [01 · 快速开始](docs/01-getting-started.md) | 安装、依赖、WSL2、手动装工具链 |
| [02 · 编写技能](docs/02-writing-skills.md) | SKILL.md 格式、三层结构设计、何时该写脚本 |
| [03 · 子 Agent](docs/03-subagents.md) | 定义格式、何时该拆子 agent、与斜杠命令配合 |
| [04 · 最佳实践](docs/04-best-practices.md) | 上下文成本、结构化检索、用钩子兜底而非提示词 |
| [05 · 集成外部技能仓库](docs/05-external-skills.md) | 选型结论、引用而非复制的理由、升级方式 |
| [06 · 排障](docs/06-troubleshooting.md) | 技能不触发、钩子失效、校验失败对照 |

版本变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## 贡献约定

**这一节只针对给本仓库（脚手架层）提代码。** 在自己项目里写业务代码不受这些约束
——那些规范写进你自己的 `src/CLAUDE.md`。

提交前跑通 `make validate && make test`。几条硬约定：

- 新增可执行逻辑用 **Python 标准库**（最低 3.8），不要用 shell、不要引第三方依赖。
- 只承诺**能验证**的东西——没有 CI runner 或本地复现手段的平台/功能，宁可明确
  不支持，也不提供没跑通过的兼容路径。
- 技能调用自带脚本必须写全 `${CLAUDE_PLUGIN_ROOT}/skills/<name>/...` 路径。
- 新增钩子要在 `hooks/hooks.json` 与 `.claude/settings.json` **两处**登记，并补测试用例。

完整约定见 [CLAUDE.md](CLAUDE.md)。

## License

[Apache-2.0](LICENSE)
