# src — 工程层

**这里是你的产品代码。** 本仓库的其余部分（`skills/` `agents/` `commands/`
`hooks/` `scripts/` `docs/`）属于脚手架层，两者边界见
[`docs/00-boundaries.md`](../docs/00-boundaries.md)。

以插件方式使用本基座（不 fork）时，这个目录与你无关——你的代码在你自己的
仓库里。

## 这一层归你管

| 内容 | 位置 |
| --- | --- |
| 业务代码 | `src/` |
| 产品说明、怎么跑起来 | 本文件（换成你自己的） |
| 架构 / 领域文档 | `src/docs/` |
| 给 Claude 的工程规范 | [`src/CLAUDE.md`](CLAUDE.md) |
| lint / 类型检查 / 测试 | 你自己的工具链 |

脚手架的 `make validate` 与 `make test` **不会**扫描这个目录，也不会因为你这里的
代码风格或文档链接而失败。反过来，你的 CI 也不必去校验 `SKILL.md`。

## 与其他代码目录的分界

仓库里有三处放代码的地方，别混：

| 目录 | 放什么 | 谁来执行 | 随插件分发 |
| --- | --- | --- | --- |
| `src/` | 业务逻辑、模块、应用入口 | 项目自身的运行时 | 否 |
| `scripts/` | 仓库维护脚本——校验、测试、脚手架生成、环境安装 | 开发者 / CI | 否 |
| `skills/<name>/scripts/` | 单个技能的确定性执行逻辑 | 技能被触发时由模型调用 | 是 |

判断标准：**这段代码是产品的一部分，还是维护仓库/技能的工具？** 前者进 `src/`。

## 约定

- 目录内部结构由技术栈决定，本基座不强加分层规范——写进
  [`src/CLAUDE.md`](CLAUDE.md) 即可。
- 语言配置文件（`package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml`）按
  各自生态惯例放在**仓库根目录**，源码放 `src/`。这样 `test-runner` 子 agent 的
  测试命令探测能直接命中。
- 构建产物（`dist/` `build/` `__pycache__/` 等）已在 `.gitignore` 中忽略。
- 测试按生态惯例放置：JS/TS 可与源码同目录（`*.test.ts`），Python 用根目录
  `tests/`，Go 用 `*_test.go`。

## codegraph 索引

`make index` 会索引整个仓库，`src/` 有代码后即可用图谱做符号查找与调用链分析：

```bash
make index    # cgc --database kuzudb --path ./.cgc/graph.kuzu index .
```

索引建立后优先用 codegraph MCP 工具检索符号与调用关系，而不是全仓库 grep。
