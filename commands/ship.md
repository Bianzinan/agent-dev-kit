---
name: ship
description: 提交前检查：先判断改动落在哪一层，跑该层对应的校验与测试，再生成提交信息
argument-hint: "[本次改动的简要说明]"
---

执行提交前的完整检查流程。本次改动说明：$ARGUMENTS

## 1. 先判断改动落在哪一层

用 `git diff --staged --name-only`（无暂存内容时用 `git diff HEAD --name-only`）
拿到改动文件，按路径归类：

| 改动路径 | 层 | 该跑的检查 |
| --- | --- | --- |
| `skills/` `agents/` `commands/` `hooks/` `scripts/` `template/` `docs/` `.claude-plugin/` 根 `CLAUDE.md` | 脚手架层 | `make validate` + `make test` |
| 其余全部——`src/`、业务配置、应用代码 | 工程层 | 项目自己的 lint / typecheck / test |

**这一步不能跳过。** `make validate` 校验的是 SKILL.md 格式、钩子注册、marketplace
清单这类脚手架自身的约定，和使用者的业务代码毫无关系。拿它去卡一次纯业务提交，
会让人误以为「这个基座要求我的产品代码符合它的目录结构」。

## 2. 按层执行检查

**改到脚手架层时**——先确认仓库根存在 `scripts/validate.py`。以插件方式安装到别人
项目里时它并不存在，此时**静默跳过，不要报错**：

```bash
make validate && make test
```

任一失败则停止，报告具体文件与行号，不要继续往下走。

**改到工程层时**——若仓库根有 `Makefile.product` 且定义了 `test-product`，直接
`make test`（它会先跑脚手架回归测试，再自动调用 `test-product`）。否则调用
`test-runner` 子 agent 探测项目自己的测试入口（`npm test` → `pytest` → `go test`
→ `cargo test`）。项目的 `CLAUDE.md` 或 `src/CLAUDE.md` 写了「提交前必做」时以那里为准。

两层都改到时，两套都跑。

## 3. 审查与提交信息

1. 调用 `code-reviewer` 子 agent 审查改动。
2. 无阻塞问题后，基于 Conventional Commits 生成提交信息草稿供用户确认。
3. 若本次同时改到两层，建议**拆成两次提交**（脚手架一次、业务代码一次）——
   混在一起会让 revert 和 code review 都变难。

未经用户明确确认，不要执行 `git commit`，也不要执行 `git push`。
