---
name: example-skill
description: 从 git 提交历史生成结构化的项目变更日志（CHANGELOG）。当用户要求"生成变更日志"、"整理发版说明"、"总结最近的提交"或准备 release notes 时使用。
---

# 生成变更日志

从 git 历史提取提交记录，按 Conventional Commits 类型分组，输出 Markdown 变更日志。

## 使用流程

1. 确认范围：用户未指定时，默认取上一个 tag 到 HEAD；无 tag 则取最近 50 条提交。
2. 运行脚本获取结构化数据（确定性执行，不要手工解析 git log）：

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/example-skill/scripts/example.py" \
     --since <tag-or-rev> --format json
   ```

   `${CLAUDE_PLUGIN_ROOT}` 由 Claude Code 在加载插件时注入，指向插件根目录。
   若在 agent-dev-kit 仓库内直接开发（未以插件方式安装，该变量为空），
   改用相对仓库根目录的路径 `skills/example-skill/scripts/example.py`。
   **不要**写成 `scripts/example.py`——那会解析到仓库自己的 `scripts/` 目录。

3. 将脚本输出按 `Features / Fixes / Docs / Refactor / Chore / Other` 分组渲染为 Markdown。
4. 把结果写入 `CHANGELOG.md` 顶部，保留历史内容。

## 输出约定

- 标题格式 `## <version> - <YYYY-MM-DD>`。
- 每条目格式 `- <描述> (<短 sha>)`，去掉 `type(scope):` 前缀。
- 无变更的分组直接省略，不要输出空标题。

## 深入参考

需要自定义分组规则、处理 breaking change 标记或多仓库聚合时，阅读 [references/USAGE.md](references/USAGE.md)。
