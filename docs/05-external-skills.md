# 05 · 集成外部技能仓库

本基座默认只启用自带的骨架技能。社区已有若干高质量技能集，本文说明
**我们选了哪些、为什么、以及怎么装**。

## 结论速览

| 仓库 | 技能数 | 常驻上下文成本 | 是否纳入 |
| --- | --- | --- | --- |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 24 | ~1.9k tokens | ✅ 已登记（默认关闭） |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 25 | ~1.9k tokens | ✅ 已登记（默认关闭） |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 284 | ~25.8k tokens | ❌ 不登记 |

三者均为 MIT、均活跃维护、无 `curl | bash` 安装、无遥测。

## 为什么关心「常驻上下文成本」

技能的 `description` 是 **always-loaded** 的：模型每一轮都要看到全部技能描述才能
决定调用哪个。所以技能数量不是越多越好——描述会一直占用上下文，并稀释检索信噪比。

Claude 5 系列上下文窗口更大，但这**不等于描述免费**。284 条描述带来的检索噪声
问题，不会因为窗口变大而消失。

## 为什么不集成 ECC

不是质量问题，是**类型不匹配**。ECC 的 284 个技能里大量是框架专用的
（`django-tdd`、`laravel-tdd`、`quarkus-tdd`、`perl-security`……）。任何单个用户
只会用到其中几个，却要为全部 284 条描述付 ~26k tokens——是另两者的 13 倍。

其它顾虑：

- `hooks.json` 约 41KB，钩子是内联压缩的 Node.js 引导字符串，难以逐行审计。
- `ito-compute` MCP 依赖尚未发布的私有包。
- 含 ECC Pro 付费项（OSS 部分免费）。
- 定位上它是**替代性的完整框架**，与本基座定位直接竞争，而非可组合的组件。

如果你确实需要它，自行安装即可，不必改本仓库：

```bash
/plugin marketplace add affaan-m/ECC
```

## 为什么用「引用」而不是「复制」

我们**不把外部代码 vendoring 进本仓库**，而是在 `marketplace.json` 里用
`github` source 引用，并用 `sha` 锁定到具体 commit：

```json
{
  "name": "addy-agent-skills",
  "source": {
    "source": "github",
    "repo": "addyosmani/agent-skills",
    "sha": "be42637c5af93fdc8526b68ec2f2651b930f316c"
  },
  "defaultEnabled": false
}
```

好处：

- 不把数 MB 的外部代码拖进本仓库，保持「骨架」定位。
- `sha` 锁定 → 可复现，上游改动不会静默流入你的环境。
- 需要升级时改一行 sha，diff 清晰可审查。

`scripts/validate.py` 会**强制**外部 source 必须带合法的 40 位 sha；只写分支名
（`ref`）会直接校验失败。这是有意为之的供应链约束。

## 如何启用

两个外部插件都是 `defaultEnabled: false`，默认不加载，装了本基座也不会平白
多出 49 个技能。需要时显式启用：

```bash
# 先添加本仓库为 marketplace
/plugin marketplace add /path/to/agent-dev-kit

# 按需启用
/plugin install addy-agent-skills@agent-dev-kit
/plugin install mattpocock-skills@agent-dev-kit
```

## 已验证的风险点

- **命名冲突：零**。三个外部仓库两两交集为 0，与本仓库的 `example-skill`、
  `code-reviewer`、`test-runner`、`review`、`ship` 也无冲突。
- **保留名**：`agent-skills`、`anthropic-agent-skills`、`claude-code-plugins`
  被 Anthropic 保留，第三方 marketplace 使用会被判定为不可信来源。我们用的是
  `addy-agent-skills`，未撞名；`validate.py` 也会拦截保留名。
- ⚠️ **不要在本仓库运行 `setup-matt-pocock-skills` 技能**。它会主动改写目标仓库的
  `CLAUDE.md` / `AGENTS.md`，而本仓库的 `CLAUDE.md` 含 rtk 生成的受保护区块
  （`<!-- rtk-instructions v2 -->`），会被破坏。

## 升级外部依赖

```bash
# 查看上游最新 commit
curl -s https://api.github.com/repos/addyosmani/agent-skills/commits?per_page=1 \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["sha"])'
```

把新 sha 填进 `marketplace.json`，然后跑 `make validate` 确认通过再提交。
