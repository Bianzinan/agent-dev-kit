# 02 · 编写技能

技能（Skill）是一组打包好的领域知识与操作流程，模型在识别到匹配场景时自动加载。

## 目录结构

```
skills/<skill-name>/
├── SKILL.md          # 必需
├── references/       # 可选：按需加载的详细文档
└── scripts/          # 可选：确定性执行的脚本
```

## SKILL.md 格式

```markdown
---
name: generate-changelog
description: 从 git 提交历史生成结构化变更日志。当用户要求"生成变更日志"、"整理发版说明"或准备 release notes 时使用。
---

# 标题

## 使用流程
...
```

frontmatter **只需要** `name` 和 `description` 两个字段：

- `name`：kebab-case，与目录名完全一致，全仓库唯一。
- `description`：技能被检索到的唯一依据。必须同时回答两个问题——
  **这个技能做什么**、**什么时候该用它**。

### description 写法对比

| ❌ 差 | ✅ 好 |
| --- | --- |
| `处理变更日志` | `从 git 提交历史生成结构化变更日志。当用户要求"生成变更日志"、"整理发版说明"或准备 release notes 时使用。` |
| `PDF 工具` | `提取 PDF 文本、填写表单域、合并或拆分页面。当用户提供 PDF 文件并要求读取内容或编辑时使用。` |

关键是把用户可能说出的**触发词**写进去，模型靠语义匹配决定是否加载。

## 三层结构设计

技能的核心设计原则是**渐进披露**（progressive disclosure）——按需加载，避免一次性
把所有细节塞进上下文。

| 层 | 内容 | 何时加载 |
| --- | --- | --- |
| frontmatter | name + description | 始终（用于检索） |
| SKILL.md 正文 | 主流程、常见路径 | 技能被触发时 |
| references/ | 参数表、边界情况、进阶用法 | 模型判断需要时才读 |

正文建议控制在 500 行以内。一旦开始堆砌参数表、异常分支、兼容性说明，就该拆到
`references/` 去。

## 何时写脚本

能用代码确定性完成的事，不要让模型手工推演：

| 场景 | 做法 |
| --- | --- |
| 解析结构化数据（git log、JSON、CSV） | 写脚本 |
| 格式转换、校验、计算 | 写脚本 |
| 语义判断、归类、行文润色 | 交给模型 |
| 需要结合上下文做取舍 | 交给模型 |

脚本应保持单一职责：输出结构化数据（如 JSON），把聚合与呈现交给模型。参考
`skills/example-skill/scripts/example.py`。

### 脚本路径必须写全（最容易踩的坑）

技能被触发时，工作目录是**用户的项目根目录**，不是技能所在目录。所以：

```bash
# ✅ 正确：从插件根目录写全
python3 "${CLAUDE_PLUGIN_ROOT}/skills/my-skill/scripts/run.py" --format json

# ❌ 错误：解析到用户项目自己的 scripts/，必然 file-not-found
python3 scripts/run.py --format json
```

`${CLAUDE_PLUGIN_ROOT}` 由 Claude Code 在加载插件时注入。若技能尚未以插件方式
安装、就在当前仓库内调试，该变量为空，改用相对仓库根目录的
`skills/my-skill/scripts/run.py`。

`scripts/validate.py` 会扫描每个技能的 SKILL.md 与 `references/*.md` 中的代码块，
发现裸的 `scripts/xxx.py` 写法直接判失败并给出正确路径。

## 编写检查清单

- [ ] `name` 是 kebab-case 且与目录名一致
- [ ] `description` 写清了「做什么」+「何时触发」，含典型触发词
- [ ] 正文精简，细节已下沉到 `references/`
- [ ] 确定性逻辑已脚本化，脚本只用标准库或已声明的依赖
- [ ] 调用自带脚本时写了 `${CLAUDE_PLUGIN_ROOT}/skills/<name>/scripts/...` 完整路径
- [ ] 脚本有可执行位（`chmod +x`）
- [ ] 有明确的输出约定（格式、位置、失败处理）
- [ ] `make validate` 与 `make test` 均通过

## 参考实现

`skills/example-skill/` 是一个完整可用的例子，同时演示了 `references/` 渐进加载
和 `scripts/` 确定性执行两种模式。
