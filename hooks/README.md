# Hooks

生命周期钩子脚本。

## 两套注册方式，都要登记

| 文件 | 生效范围 | 路径前缀 |
| --- | --- | --- |
| `hooks/hooks.json` | 随插件分发，安装到任意项目后生效 | `${CLAUDE_PLUGIN_ROOT}` |
| `.claude/settings.json` | 只在 agent-dev-kit 仓库内开发时生效 | `$CLAUDE_PROJECT_DIR` |

新增钩子时**两处都要注册**。只写 `settings.json` 会导致「本地有效、装到别处
静默失效」；只写 `hooks.json` 则在本仓库开发时不生效。`validate.py` 会检查两份
清单里引用的脚本确实存在，但无法替你判断该不该注册——这一步靠约定。

同时命中时（在本仓库里又安装了本插件）钩子会执行两次。当前钩子只做只读判断，
幂等无副作用；新增钩子请保持这一性质。

## 事件类型

| 事件 | 触发时机 | 典型用途 |
| --- | --- | --- |
| `PreToolUse` | 工具调用前 | 拦截高危命令、参数校验 |
| `PostToolUse` | 工具调用后 | 自动 format、自动跑 lint |
| `UserPromptSubmit` | 用户提交提示词时 | 注入上下文、敏感词检查 |
| `SessionStart` | 会话开始 | 加载项目状态 |
| `Stop` | 主循环结束 | 汇总、通知 |

## 约定

- 脚本从 stdin 读取 JSON 事件，包含 `tool_name`、`tool_input` 等字段。
- 退出码语义：`0` 放行；`2` 阻止本次操作并把 stderr 反馈给模型；其他非零码视为脚本自身错误。
- **钩子一律用 Python 写**，不要用 shell。规则用一种正则方言表达、能被
  `test_hooks.py` 逐条断言，也不必和 shell 的引号与转义陷阱搏斗。
  Python 3.8+ 已是本仓库的硬依赖，不引入新成本。
- 脚本以 `#!/usr/bin/env python3` 开头，且具备可执行位——用
  `git update-index --chmod=+x` 落到 git 索引，只在本地 `chmod` 别人 clone 后仍不可执行。
- 解析失败、字段缺失等异常一律**放行**。钩子不应该因为自身出错而阻断正常工作。
- 路径用 `${CLAUDE_PLUGIN_ROOT}` 或 `$CLAUDE_PROJECT_DIR` 前缀，保证任意 cwd 下可用。

## 当前钩子

- `pre_tool_use.py` — 匹配 `Bash` 工具，拦截递归删根、`git push --force`、
  `git reset --hard`、`git clean -f`、`chmod -R 777`、fork 炸弹、
  `curl | sh` 管道执行远程脚本、`dd of=/dev/`、`mkfs` 等高危模式。
  拦截时会把**原因和替代做法**写到 stderr 反馈给模型，而不只是报「已阻止」。

  黑名单是正则匹配，只防手滑与惯性操作，**不是**对抗性的安全边界。

## 测试

```bash
make test        # 等价于 python3 scripts/test_hooks.py
```

31 个用例双向覆盖：高危命令必须 `exit 2`，日常命令必须 `exit 0`，畸形输入必须放行。
误伤正常开发（例如把 `git push --force-with-lease`、`rm -rf ./node_modules`、
`git log --pretty=format:%h` 一并拦掉）与漏网同样算失败——加新规则时请同时补两类用例。

手工单测某条命令：

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | python3 hooks/pre_tool_use.py; echo "exit=$?"
```
