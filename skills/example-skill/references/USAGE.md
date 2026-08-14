# 变更日志生成 — 进阶用法

本文件是渐进加载（progressive disclosure）示例：SKILL.md 只保留主流程，细节按需读取。

## 脚本路径

下文用 `$SCRIPT` 指代脚本的绝对路径，先按运行方式取值：

```bash
# 以插件方式安装时
SCRIPT="${CLAUDE_PLUGIN_ROOT}/skills/example-skill/scripts/example.py"
# 在 agent-dev-kit 仓库内直接开发时（相对仓库根目录）
SCRIPT="skills/example-skill/scripts/example.py"
```

## 脚本参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--since` | 起始 revision（tag / sha / 分支） | 上一个 tag，缺失时回退到最近 50 条 |
| `--until` | 结束 revision | `HEAD` |
| `--format` | `json` 或 `markdown` | `json` |
| `--repo` | 仓库路径 | 当前目录 |

## 分组规则

脚本按 Conventional Commits 的 `type` 前缀分类：

- `feat` → Features
- `fix` → Fixes
- `docs` → Docs
- `refactor` / `perf` → Refactor
- `chore` / `build` / `ci` / `test` / `style` → Chore
- 无法识别的前缀 → Other

自定义映射：修改 `scripts/example.py` 中的 `TYPE_GROUPS` 字典，键为 commit type，值为分组标题。

## Breaking change

提交信息包含 `!` 标记（如 `feat!:`）或正文含 `BREAKING CHANGE:` 时，脚本会在条目上标记 `"breaking": true`。
渲染时应把这些条目单独提升到 `### ⚠ BREAKING CHANGES` 分组，置于全部分组之前。

## 多仓库聚合

对每个仓库分别执行：

```bash
python3 "$SCRIPT" --repo ../service-a --format json > /tmp/a.json
python3 "$SCRIPT" --repo ../service-b --format json > /tmp/b.json
```

再按仓库名作为二级标题合并渲染。不要在脚本内部实现聚合逻辑——保持脚本单一职责，聚合交给模型。

## 常见问题

- **浅克隆导致历史缺失**：先执行 `git fetch --unshallow`。
- **合并提交噪音**：脚本默认使用 `--no-merges`，无需额外处理。
- **非 Conventional Commits 仓库**：全部条目会落入 Other，此时建议直接让模型按语义归类，而非强行套用前缀规则。
