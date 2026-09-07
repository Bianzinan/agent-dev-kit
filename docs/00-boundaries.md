# 00 · 层边界

**先读这一篇。** 本仓库里同时住着两个工程，混淆它们是最容易犯的错误。

| | 脚手架层（kit） | 工程层（product） |
| --- | --- | --- |
| 它是什么 | Agent 开发基座本身 | 你用这个基座做的产品 |
| 代码 | `skills/` `agents/` `commands/` `hooks/` `scripts/` `template/` | `src/` |
| 文档 | `README.md` `docs/` | `src/README.md` `src/docs/` |
| 给 Claude 的指令 | 根 `CLAUDE.md` | `src/CLAUDE.md` |
| 校验 | `make validate` / `make test` | 你自己的 lint / test |
| 版本 | `.claude-plugin/plugin.json` | 你自己的 `package.json` / `pyproject.toml` … |
| 依赖 | 只用 Python 标准库 | 随你 |

## 一条硬规则

> **`make validate` 与 `make test` 永远不进入 `src/`。**

`scripts/validate.py` 顶部有一个 `PRODUCT_DIRS` 常量，所有检查都必须跳过它。
脚手架不该因为你产品文档里有个坏链接、你的业务脚本没有可执行位，就判校验失败——
那是越界。反过来也一样：你的 CI 不该去校验 `SKILL.md` 的 frontmatter。

新增校验项时，第一个问题永远是：**这条规则约束的是脚手架层还是工程层？**

## 两种用法，选一种

边界之所以容易糊，是因为这个仓库支持两种完全不同的用法。**先确定你是哪一种**，
另一种的文档就与你无关。

### 用法 A：作为插件安装（已有工程）

你的仓库保持原样，只是获得本基座的技能、子 agent、斜杠命令与安全钩子。

```
/plugin marketplace add Bianzinan/agent-dev-kit
/plugin install agent-dev-kit
```

- **`src/` 与你无关**——你的代码在你自己的仓库里，本仓库你根本不会 clone。
- **`docs/` 与你基本无关**——那是维护基座的文档。你只需要看
  [02 · 编写技能](02-writing-skills.md)（想自己写技能时）和
  [06 · 排障](06-troubleshooting.md)。
- 你自己项目的 `CLAUDE.md` 由你自己写，本仓库的 `CLAUDE.md` 不会进你的上下文。

这是**推荐**方式，因为边界天然清晰：两个工程物理上就是两个仓库。

### 用法 B：作为工程基座 fork（新项目）

从本仓库起步做一个新产品，业务代码写进 `src/`。

```bash
git clone https://github.com/Bianzinan/agent-dev-kit.git my-product
cd my-product && make setup
```

这种用法下两层住在同一个仓库里，所以边界必须靠约定维持：

| 你该改 | 你不该动（除非在改进基座本身） |
| --- | --- |
| `src/**` 全部 | `scripts/validate.py` `scripts/test_hooks.py` |
| `src/CLAUDE.md` 写你的工程规范 | `hooks/` `template/` |
| `skills/` 加你自己的领域技能 | `docs/01`–`docs/06` |
| 根 `README.md` 换成你产品的 | 根 `CLAUDE.md` 的脚手架层小节 |

## 文档该往哪儿放

这是「信息混在一起」最常发生的地方。判断标准只有一条：

> **这段话是在讲「怎么维护这套 Agent 基座」，还是在讲「这个产品是什么」？**

| 内容 | 位置 |
| --- | --- |
| 怎么写技能 / 子 agent / 钩子 | `docs/`（脚手架层） |
| 提交前要跑什么校验 | 根 `CLAUDE.md`（脚手架层） |
| 外部技能仓库选型 | `docs/05`（脚手架层） |
| 产品是做什么的、怎么跑起来 | `src/README.md` |
| 业务模块划分、领域概念 | `src/docs/` |
| 产品代码的编码规范、测试策略 | `src/CLAUDE.md` |

不要把产品的架构说明写进根 `README.md`，也不要把技能编写规范写进 `src/`。

## 三个无法分层的文件

有几处配置天然是全仓库级的，分不开。它们是边界的例外，改动时要留意自己在动哪一层：

| 文件 | 情况 |
| --- | --- |
| `.claude/settings.json` | 权限与钩子注册是仓库级的。工程层要加自己的 `allow` 规则时直接追加，别删脚手架层已有的条目 |
| `.gitignore` | 两层的忽略规则混在一份里，加规则时写清注释属于哪一层 |
| `Makefile` | 脚手架层已占用 `validate` / `test` / `lint` / `clean`。工程层新增目标请用 `test-product` 之类的独立名字，别覆盖 |

`Makefile` 的 `test` 目标尤其容易撞——脚手架层的 `make test` 是钩子回归测试。
要让一条命令跑两边，就新增一个聚合目标，而不是覆盖原有的。

## CLAUDE.md 为什么要分两份

Claude Code 会**始终**加载根 `CLAUDE.md`，而子目录的 `CLAUDE.md` 只在读写该目录
下的文件时才加载。这正好对应两层：

- 根 `CLAUDE.md` —— 脚手架层规范。改技能、改钩子时需要，始终在上下文里。
- `src/CLAUDE.md` —— 工程层规范。只在动业务代码时才加载，不平白占用上下文。

把工程规范塞进根 `CLAUDE.md`，代价是每一轮对话都要为它付 token，哪怕你这次
只是在改一个技能的 description。

## 术语表

文档与代码里反复出现的几个词，各自只有一个意思。写文档时用**正体词**，别用
「避免」里列的别名——同一个东西换着叫，是层边界糊掉的第一步。

**脚手架层**
Agent 开发基座本身：`skills/` `agents/` `commands/` `hooks/` `scripts/` `template/`
`docs/` 与根 `CLAUDE.md`。英文标识符用 `kit`。
避免：基座层、框架层。

**工程层**
使用者放自己产品的那一层，只有 `src/`。英文标识符用 `product`——
`PRODUCT_DIRS`、`test-product`、`Makefile.product` 都是它。
避免：产品层、业务层、应用层。

**产品**
使用者用这个基座做出来的东西。它**住在**工程层，但不等于工程层：工程层是仓库里
的位置，产品是位置里的内容。「产品代码」「业务代码」指同一件事，都在 `src/`。

**技能（skill）**
`skills/<name>/SKILL.md` 定义的一个能力单元。
避免：技能包、skill 包（那是「插件」）。

**插件（plugin）**
marketplace 里可安装的打包单位。本仓库自身是一个插件（`agent-dev-kit`），每个外部
技能集也各是一个插件。一个插件可以含多个技能。

**登记**
把技能路径写进 `marketplace.json` 的 `skills` 数组。这个数组是分发白名单：
未登记 = 开发中，不分发。
避免：注册（留给钩子——`hooks.json` / `settings.json` 里的是「注册」）、
启用（那是使用者 `/plugin install` 的动作）。

**常驻上下文成本**
技能 `description` 每一轮对话都会加载，所有已启用技能的 description 之和就是这项
成本。它决定外部技能集要不要默认关闭（见 `05`）。
避免：token 开销、上下文占用（太泛，会和技能正文的按需加载混在一起）。

### 已解决的歧义

- **工程层 / 产品 / 业务代码 / product 四个词绕着一个概念。** 已定：工程层是位置，
  产品是内容，业务代码 = 产品代码，`product` 只做标识符。
- **`kit` / `product` 只出现在英文标识符里**（常量、make 目标、文件名）。中文正文
  一律用脚手架层 / 工程层，不写「kit 层」。
- **「登记」「注册」「启用」曾混用。** 已定：技能进白名单叫登记，钩子进
  `hooks.json` / `settings.json` 叫注册，使用者装插件叫启用。

## 相关

- [01 · 快速开始](01-getting-started.md)
- [06 · 排障](06-troubleshooting.md)
