---
name: review
description: 对当前改动执行代码审查
argument-hint: "[文件路径或范围，可省略]"
---

对当前工作区的改动执行代码审查。

审查范围：$ARGUMENTS

若未指定范围，默认审查 `git diff --staged`；无暂存内容时审查 `git diff HEAD`。

请调用 `code-reviewer` 子 agent 完成审查，并按 Blocking / Warning / Info 分级汇总结果。
