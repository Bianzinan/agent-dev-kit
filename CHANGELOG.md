# 更新日志

本文件记录本项目的所有重要变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

版本号的唯一真实来源是 `.claude-plugin/plugin.json` 的 `version` 字段；
`scripts/validate.py` 会校验 HEAD 上的 tag 与它一致。

## [未发布]

## [1.1.0] - 2026-09-07

### 变更

- **codegraph 换成 [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph)**，
  替换原先的 CodeGraphContext。对照表：

  | | 旧 | 新 |
  | --- | --- | --- |
  | CLI | `cgc` | `codegraph` |
  | MCP 启动 | `cgc mcp start` | `codegraph serve --mcp` |
  | 索引位置 | `.cgc/graph.kuzu`（KuzuDB） | `.codegraph/codegraph.db`（SQLite + FTS5） |
  | 安装依赖 | Python ≥ 3.10 + uv | 无（官方包自带 Node 运行时） |

- `scripts/bootstrap.sh` 的 `install_codegraph` 改走官方安装脚本，失败回退
  `npm i -g @colbymchenry/codegraph`；不再为了装它而先装 uv 和一个独立 Python。
- `make index` 改为按 `.codegraph/` 是否存在分派：首次跑 `codegraph init -y .`，
  之后跑 `codegraph index .`——新 CLI 在未初始化的目录直接执行 `index` 会报错。
- `make clean` 与 `.gitignore` 的索引路径同步改为 `.codegraph/`。

### 说明

- 新的 MCP 服务器定义了 8 个工具，但默认只在 `tools/list` 里列出
  `codegraph_explore`——一次调用即返回相关符号的带行号源码与彼此的调用路径。
  其余 7 个（`node` / `search` / `callers` / `callees` / `impact` / `files` /
  `status`）handler 完好、可直接调用，只是不列出，以免工具过多诱导选错。
  需要全部列出时给 `.mcp.json` 加 `CODEGRAPH_MCP_TOOLS` 环境变量，详见
  `docs/01-getting-started.md`。

### 升级说明

从 1.0.0 升级需要手动清理旧工具（codegraph 是可选增强，不清理也不影响校验与技能）：

```bash
uv tool uninstall codegraphcontext   # 移除旧的 cgc
rm -rf .cgc                          # 删掉旧索引
rm -rf ~/.codegraphcontext           # 删掉旧的全局配置
make setup && make index             # 装新 CLI 并重建索引
```

## [1.0.0] - 2026-08-14

首个正式版本。

### 新增

- **脚手架骨架**：`skills/`（含 `example-skill` 完整示例）、`agents/`
  （`code-reviewer`、`test-runner`）、`commands/`（`/review`、`/ship`）、
  `template/` 新技能模板。
- **工程层 `src/`**：与脚手架层分离的业务代码目录，边界与规范见
  `docs/00-boundaries.md` 和 `src/CLAUDE.md`。`make validate` 永不进入 `src/`。
- **两层共用的测试入口**：根 `Makefile` 通过 `-include Makefile.product` 可选加载
  工程层目标；`make test` 跑完脚手架回归测试后自动调用 `test-product`，未定义则跳过。
  模板见 `Makefile.product.example`。
- **生命周期钩子**：`hooks/pre_tool_use.py` 拦截高危命令，配套
  `hooks/hooks.json`（随插件分发）与 `.claude/settings.json`（本仓库内生效）
  两套注册方式。
- **一键安装**：`make setup`（`scripts/bootstrap.sh`）幂等地安装 rtk 与
  codegraph、生成本地配置、修复脚本执行位。支持 Linux / macOS / WSL2，
  检测到原生 Windows 时直接报错并给出 WSL2 指引；rtk / cgc 缺失时降级提醒
  而非中断。
- **结构校验**：`scripts/validate.py` 覆盖目录布局、SKILL.md frontmatter、
  技能脚本全路径写法、marketplace 引用、plugin.json 一致性、tag 与版本号一致性、
  钩子注册、文档相对链接、`.gitattributes` 换行规则、脚本可执行位（读 git 索引）
  与 LF 换行。
- **回归测试**：`scripts/test_hooks.py`（31 个用例）与
  `scripts/test_release_notes.py`（13 个断言）。
- **发布流水线**：推 `v*` tag 触发 `.github/workflows/release.yml`——重跑校验与
  测试、用 `scripts/release_notes.py` 从 CHANGELOG 抽出对应小节、创建 GitHub
  Release。tag 与 `plugin.json` 的版本不符、或 CHANGELOG 缺对应小节都不会产出
  Release。
- **外部技能仓库**：以 `github` source + 40 位 sha 锁定的方式引入
  `addyosmani/agent-skills` 与 `mattpocock/skills`，不 vendoring 代码，
  均为 `defaultEnabled: false`。选型结论见 `docs/05-external-skills.md`。
- **MCP 集成**：`.mcp.json` 配置 codegraph（KuzuDB 嵌入式后端，25 个工具）、
  filesystem、github 三个服务器。
- **CI**：`.github/workflows/validate.yml` 在 ubuntu 与 macos 上跑同一套测试，
  额外用 Python 3.8 跑一遍，并每周验证一次完整安装流程。
- **文档**：`docs/` 中文文档（`00`–`06` 共七篇），覆盖层边界、上手、技能编写、
  子 agent、最佳实践、外部技能选型与排障。

### 设计决定

- 可执行逻辑一律用 Python 标准库（最低 3.8），规则可被测试逐条断言；
  仅保留 `scripts/bootstrap.sh` 一个 bash 脚本。
- `/ship` 按层分派：先判断改动落在脚手架层还是工程层，只跑该层的检查。
  以插件方式安装、仓库没有 `scripts/validate.py` 时静默跳过而非报错。
- 只承诺能验证的东西：不支持原生 Windows，因为没有对应的 CI runner，
  而钩子在其上失效是静默的。

[未发布]: https://github.com/Bianzinan/agent-dev-kit/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Bianzinan/agent-dev-kit/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Bianzinan/agent-dev-kit/releases/tag/v1.0.0
