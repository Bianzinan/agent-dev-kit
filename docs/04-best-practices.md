# 04 · 最佳实践

## 上下文是稀缺资源

上下文窗口是 Agent 工程中最需要精打细算的资源。三个层面的优化：

1. **渐进披露**——技能正文只放主流程，细节下沉到 `references/`。
2. **输出压缩**——命令加 `rtk` 前缀，常见开发命令输出体积降低 60–90%。
3. **上下文隔离**——探索性、输出冗长的任务交给子 Agent，主会话只接收结论。

## 优先用结构化检索，而非全文搜索

在大型代码库里 `grep -r` 既慢又噪音大。本仓库集成了 codegraph MCP，把代码索引成图：

```bash
cgc --database kuzudb --path ./.cgc/graph.kuzu index .
```

之后可以直接查符号定义、调用链、依赖关系、死代码、圈复杂度。检索代码时的优先级：

**codegraph MCP 工具 > glob（按文件名）> grep（按内容）> 全库扫描**

## 确定性的事交给代码

模型擅长语义判断，不擅长精确计算与格式转换。凡是能写成脚本的（解析、校验、
格式化、统计），都应该写成脚本，让模型调用而不是手工推演。这既省 token，
也消除了随机性。

判断标准：**同样的输入是否必须得到同样的输出？** 是 → 写脚本。

## 用 hooks 兜底，而不是靠提示词约束

提示词层面的"请不要执行危险命令"不可靠。真正的防线应该放在 hooks：

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/hooks/pre_tool_use.py\"" }] }
    ]
  }
}
```

钩子返回 `exit 2` 即可阻断本次工具调用，并把 stderr 反馈给模型让它改正。
本仓库的 `hooks/pre_tool_use.py` 拦截了 `rm -rf /`、`git push --force`、
`git reset --hard`、`chmod -R 777`、fork 炸弹、`curl | sh` 等高危模式。

三条经验：

- **钩子要写成 Python 而不是 shell**。规则用一种正则方言表达、能被测试逐条断言，
  也不必和 shell 的引号与转义陷阱搏斗。
- **钩子自身出错要放行**。JSON 解析失败、字段缺失时返回 0，不要 fail-closed 把
  正常工作全部卡死。
- **黑名单要有回归测试，且必须测「不该拦的」**。误伤（把
  `git push --force-with-lease` 一并拦掉）和漏网一样是缺陷，而且更难被发现——
  用户只会觉得 Agent 变笨了。本仓库的 `scripts/test_hooks.py` 双向各测一半。

同样地，权限控制写在 `.claude/settings.json` 的 `permissions` 里，
把敏感文件（`.env`、`*.pem`）列入 `deny`。

## 让校验可执行、可 CI

约定如果只写在文档里，就一定会腐化。本仓库把约定固化成 `scripts/validate.py`：

- SKILL.md frontmatter 完整性
- `name` 与目录名一致且为 kebab-case
- marketplace.json 引用的路径真实存在
- agents / commands frontmatter 合法

本地提交前跑，CI 里也跑（`.github/workflows/validate.yml`）。约定必须是可执行的。

## description 决定技能是否会被用上

技能写得再好，`description` 不匹配就永远不会被加载。写的时候把自己当成检索引擎：
**用户会用什么话来描述这个需求？** 把那些词写进去。

## 团队配置与个人配置分离

| 文件 | 是否提交 | 用途 |
| --- | --- | --- |
| `.claude/settings.json` | 是 | 团队共享的权限与 hooks |
| `.claude/settings.local.json` | 否（已 gitignore） | 个人本地覆盖 |
| `.claude/settings.local.json.example` | 是 | 供他人复制的模板 |
| `.mcp.json` | 是 | 项目级 MCP 服务器；密钥用 `${ENV_VAR}` 引用，绝不硬编码 |

## 小步验证

改完就验证，不要攒一大批改动再一次性检查：

```bash
python3 scripts/validate.py
```

失败信息应该足够具体，能直接定位到文件和字段——这也是 `validate.py` 的设计目标。
