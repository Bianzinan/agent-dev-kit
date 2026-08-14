# Skills

每个技能是本目录下的一个子目录，目录名即技能名（kebab-case，全仓库唯一）。

```
skills/
└── <skill-name>/
    ├── SKILL.md          # 必需：frontmatter(name, description) + 主流程
    ├── references/       # 可选：按需加载的详细文档
    └── scripts/          # 可选：确定性执行的脚本
```

## 约定

- `SKILL.md` 的 frontmatter 只需 `name` 和 `description` 两个字段。
- `name` 必须与目录名完全一致，且为 kebab-case。
- `description` 要同时说明「做什么」和「何时触发」——这是模型检索技能的唯一入口。
- 正文保持简洁（建议 500 行以内），把细节、边界情况、参数表放进 `references/`。
- 能用脚本确定性完成的步骤（解析、校验、格式转换）写成 `scripts/`，不要让模型手工推演。
- **调用自带脚本必须写全路径**——技能执行时 cwd 是用户的项目根目录，不是技能目录：

  ```bash
  # ✅ 正确
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/my-skill/scripts/run.py"
  # ❌ 错误：会解析到用户项目自己的 scripts/，必然 file-not-found
  python3 scripts/run.py
  ```

  `validate.py` 会扫描 SKILL.md 与 references/ 中的代码块并拦截错误写法。

## 新增技能

```bash
python3 scripts/new_skill.py my-new-skill
python3 scripts/validate.py
```

（上面两条是仓库维护脚本，从仓库根目录执行，与技能自带脚本的路径规则无关。）

新增技能后如需随插件分发，记得在 `.claude-plugin/marketplace.json` 的 `skills` 数组中登记路径。
