# 01 · 快速开始

## 一键安装（推荐）

```bash
git clone https://github.com/Bianzinan/agent-dev-kit.git agent-dev-kit
cd agent-dev-kit
make setup
```

等价于 `bash scripts/bootstrap.sh`。脚本会自动：

1. 检查 git、Python 3 等基础依赖
2. 按当前系统选择合适方式安装 rtk 与 codegraph（已安装则跳过）
3. 从 `.example` 生成 `.claude/settings.local.json`
4. 修复 clone 后可能丢失的脚本执行位
5. 运行仓库结构校验

脚本是**幂等**的，可以反复执行。

### 参数

| 参数 | 说明 |
| --- | --- |
| （无） | 安装全部，缺什么装什么 |
| `--check` | 只检查环境，不安装、不写任何文件 |
| `--skip-rtk` | 跳过 rtk |
| `--skip-codegraph` | 跳过 codegraph |
| `--index` | 安装后立即建立代码图谱索引 |
| `--help` | 查看用法 |

### 可选依赖的降级行为

rtk 与 codegraph 都是**可选增强**。若网络受限或平台不支持导致安装失败，
脚本只会打印提醒并继续，最终仍以 `exit 0` 结束——仓库校验、技能、子 agent、
斜杠命令都不受影响。

## 运行环境

支持 **Linux / macOS / WSL2**。

| 平台 | 支持程度 | 说明 |
| --- | --- | --- |
| Linux（x86_64 / arm64） | ✅ 支持 | CI 覆盖（ubuntu-latest） |
| macOS（Apple Silicon / Intel） | ✅ 支持 | CI 覆盖（macos-latest） |
| Windows + WSL2 | ✅ 支持 | Windows 用户走这条路；WSL 内即 Linux，同上 |
| Windows 原生（PowerShell / cmd） | ❌ 不支持 | `bootstrap.sh` 会直接报错并给出 WSL2 指引 |

**为什么不支持原生 Windows**：这个项目没有 Windows 机器可做验证。安全钩子在
Windows 上失效是**静默**的——用户以为有防护，实际没有——所以与其提供一套没跑
通过的兼容路径，不如把边界划清楚。WSL2 是官方方案，装起来只有一条命令。

CI 在 ubuntu 与 macos 两个 runner 上跑同一套 `validate.py` + `test_hooks.py` +
脚手架冒烟测试，并额外用 Python 3.8 跑一遍，保证声明的最低版本真实有效。

### 依赖

| 依赖 | 版本 | 必需 | 用途 |
| --- | --- | --- | --- |
| Claude Code | 最新版 | 是 | 运行时 |
| git | 任意 | 是 | 版本控制；`validate.py` 也靠它读取文件模式 |
| Python | ≥ 3.8 | 是 | 校验 / 钩子 / 测试 / 脚手架（仅标准库，无需 pip 装包） |
| Bash | ≥ 3.2 | 是 | `scripts/bootstrap.sh`（兼容 macOS 自带 3.2） |
| Node.js | ≥ 18 | 否 | filesystem / github 两个 MCP 服务器用 `npx` 拉起 |
| make | 任意 | 否 | 命令快捷入口，等价脚本调用见 `Makefile` |
| rtk | ≥ 0.45 | 否 | CLI 输出压缩 |
| cgc | ≥ 0.5 | 否 | codegraph MCP 服务器（自身需要 Python ≥ 3.10） |

### Windows 用户：装 WSL2

```powershell
# PowerShell（管理员），Windows 10 2004+ / Windows 11
wsl --install -d Ubuntu
```

重启后打开 Ubuntu 终端，把仓库克隆到 **WSL 的 Linux 文件系统**：

```bash
cd ~ && git clone https://github.com/Bianzinan/agent-dev-kit.git
cd agent-dev-kit && make setup
```

**不要克隆到 `/mnt/c/...`**。放在 Windows 挂载盘下会同时踩两个坑：跨文件系统 IO
明显变慢；Windows 侧的 git 与编辑器会破坏脚本的可执行位与 LF 换行符，导致钩子
静默失效。`bootstrap.sh` 检测到仓库位于 `/mnt/` 下会给出警告。

Claude Code、Node.js 也要装在 WSL 内，而不是 Windows 侧。

### 换行符与可执行位

这两样东西被破坏时，失败模式都是「钩子静默不生效」，所以仓库里都做了固化与校验：

- **换行符**由 `.gitattributes` 固定为 LF。若被写成 CRLF，shebang 会变成
  `#!/usr/bin/env python3\r`，执行时报 `bad interpreter`。`validate.py` 有兜底检查。
- **可执行位**以 **git 索引**为准而不是本地文件系统——本地 `chmod` 了但没落到
  索引，别人 clone 下来依然不可执行。校验提示缺可执行位时用
  `git update-index --chmod=+x <path>` 修复。

## 常用命令

```bash
make help       # 查看全部命令
make setup      # 一键安装 + 初始化
make check      # 只检查环境
make validate   # 校验仓库结构（提交前必跑）
make test       # 脚手架回归测试 + 工程层 test-product（定义了才跑）
make new-skill NAME=my-skill
make index      # 建立 codegraph 索引
make lint       # shellcheck 所有脚本
make clean      # 清理本地索引缓存
```

## 放你的工程代码

本仓库是脚手架，业务代码写进 `src/`：

- `src/` —— 产品代码
- `scripts/` —— 仓库维护脚本（校验、测试、脚手架）
- `skills/<name>/scripts/` —— 单个技能的确定性执行逻辑

语言配置文件（`package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml`）按各自
生态惯例放在**仓库根目录**，这样 `test-runner` 子 agent 的测试命令探测能直接命中。

`src/` 属于**工程层**，脚手架的 `make validate` 不会扫描它；工程层的规范写在
[src/CLAUDE.md](../src/CLAUDE.md) 而不是根 `CLAUDE.md`。

工程层自己的 make 目标写进 `Makefile.product`（根 `Makefile` 属于脚手架层，升级时
会被覆盖）：

```bash
cp Makefile.product.example Makefile.product
$EDITOR Makefile.product        # 填 test-product / lint-product 等目标
make test                       # 脚手架测试跑完后自动调用 test-product
```

`test-product` 是约定名，`make test` 会自动调用它——**没定义就跳过**，不会报错。
详见 [00 · 层边界](00-boundaries.md) 与 [src/README.md](../src/README.md)。

## 安装到 Claude Code

本仓库本身就是一个插件市场（marketplace）。在 Claude Code 中执行：

```
/plugin marketplace add Bianzinan/agent-dev-kit
/plugin install agent-dev-kit
```

安装后 `skills/`、`agents/`、`commands/` 中的内容会自动可用。

## 手动安装工具链

`make setup` 已自动处理，以下内容供排障参考。

### rtk（Rust Token Killer）

CLI 输出压缩代理，在命令前加 `rtk` 前缀即可把输出体积压缩 60–90%。

```bash
# macOS
brew install rtk-ai/tap/rtk

# Linux / 其他
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/develop/install.sh | bash

rtk init --agent claude    # 向 CLAUDE.md 注入使用说明
rtk gain                   # 查看累计节省的 token
```

### codegraph（CodeGraphContext）

把代码库索引成图数据库，向 Agent 提供符号、调用关系与依赖上下文。

```bash
# 需要 Python >= 3.10，用 uv 隔离安装可避免污染系统环境
uv tool install --python 3.12 codegraphcontext
```

安装后得到 `cgc` 命令。本仓库使用 KuzuDB 嵌入式后端，**无需**额外启动 Neo4j：

```bash
# 建立索引（首次使用前执行）
make index
# 等价于 cgc --database kuzudb --path ./.cgc/graph.kuzu index .

# 查看索引统计
cgc --database kuzudb --path ./.cgc/graph.kuzu stats
```

MCP 服务器已在 `.mcp.json` 中注册，Claude Code 启动时会自动拉起，提供 25 个工具
（符号查找、调用链分析、死代码检测、圈复杂度计算、Cypher 查询等）。

### PATH 问题

若装完提示 `command not found`，把用户级 bin 目录加入 PATH：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

写入 `~/.zshrc` 或 `~/.bashrc` 可持久生效。

## 本地校验

提交前必须跑通：

```bash
make validate   # 结构校验
make test       # 钩子回归测试
```

两者都输出 `✓` 才可提交。CI 跑的是同一份脚本，本地过了 CI 就会过。

## 新增一个技能

```bash
make new-skill NAME=my-skill
# 编辑 skills/my-skill/SKILL.md
make validate
```

## 下一步

- [00 · 层边界](00-boundaries.md) —— 脚手架层与工程层怎么分
- [02 · 编写技能](02-writing-skills.md)
- [03 · 子 Agent](03-subagents.md)
- [04 · 最佳实践](04-best-practices.md)
- [06 · 排障](06-troubleshooting.md)
