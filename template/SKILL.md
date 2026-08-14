---
name: skill-name
description: 用一句话说明这个技能做什么，以及在什么情况下应该被触发（列出典型用户诉求关键词）。
---

# 技能标题

一句话概述这个技能解决的问题。

## 使用流程

1. 第一步：明确输入与前置条件。
2. 第二步：执行确定性操作，优先调用本技能 `scripts/` 下的脚本：

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/skill-name/scripts/xxx.py" --arg value
   ```

   路径**必须**从插件根目录写全。技能执行时的工作目录是用户的项目根目录，
   直接写 `scripts/xxx.py` 会解析到项目自己的 `scripts/`，必然找不到文件。
3. 第三步：产出结果并说明写入位置。

## 输出约定

- 描述产物格式、命名、存放位置。
- 描述失败时如何反馈。

## 深入参考

需要处理边界情况时，阅读 [references/USAGE.md](references/USAGE.md)。
