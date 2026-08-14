# 06 · 排障

按「症状 → 原因 → 处理」组织。本基座里绝大多数故障都是**静默**的——不报错，
只是某个东西不生效——所以先看这一节的自检清单。

## 先跑这三条

```bash
make validate   # 结构约定是否被破坏
make test       # 安全钩子是否仍按预期拦截 / 放行
make check      # 环境依赖是否齐备（只读，不修改任何文件）
```

`validate.py` 的报错都带文件、行号与修复命令，多数问题看提示即可解决。

---

## 技能相关

### 技能不被触发

模型是靠 `description` 做语义匹配的，`SKILL.md` 正文写得再好也不影响检索。

- `description` 是否同时写清了**做什么**和**何时触发**？只写「处理变更日志」
  这种没有触发词的描述基本不会被命中。
- 是否把用户可能说出的**原话**写进去了？参考
  [02 · 编写技能](02-writing-skills.md) 的写法对比表。
- 技能是否真的被加载？以插件方式安装的技能需要 `/plugin install` 且插件已启用；
  外部技能集默认 `defaultEnabled: false`，需显式启用。

### 技能里的脚本报 file-not-found

最常见的坑。技能执行时的工作目录是**用户的项目根目录**，不是技能目录：

```bash
# ❌ 解析到用户项目自己的 scripts/
python3 scripts/gen.py
# ✅
python3 "${CLAUDE_PLUGIN_ROOT}/skills/my-skill/scripts/gen.py"
```

`make validate` 会扫描技能文档的代码块并拦截错误写法。在本仓库内直接调试
（未以插件方式安装）时 `${CLAUDE_PLUGIN_ROOT}` 为空，改用相对仓库根目录的
`skills/my-skill/scripts/gen.py`。

### 新技能没有随插件分发

`make validate` 会在末尾以「提示」列出未登记的技能。需要分发就把路径加进
`.claude-plugin/marketplace.json` 的 `skills` 数组。

---

## 钩子相关

### 高危命令没有被拦截

钩子失效是静默的——**看不到任何报错，只是防护没生效**。逐项排查：

1. **钩子本身是否还正确**：`make test`。31 个用例双向覆盖，通过说明规则逻辑没问题，
   那问题就在注册或环境。
2. **注册在哪一份清单里**。两份都要登记，缺一会出现「本地有效、装到别处失效」：

   | 文件 | 生效范围 |
   | --- | --- |
   | `hooks/hooks.json` | 随插件分发，安装到其他项目后生效 |
   | `.claude/settings.json` | 只在本仓库内开发时生效 |

3. **可执行位是否落到了 git 索引**。只在本地 `chmod` 是不够的，别人 clone
   下来仍不可执行：

   ```bash
   git ls-files -s hooks/            # 应为 100755
   git update-index --chmod=+x hooks/pre_tool_use.py
   ```

4. **换行符是否被改成了 CRLF**。shebang 会变成 `#!/usr/bin/env python3\r`，
   报 `bad interpreter`。`make validate` 有对应检查项。

单独测一条命令：

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' \
  | python3 hooks/pre_tool_use.py; echo "exit=$?"   # 期望 2
```

### 正常命令被误拦

黑名单是正则匹配，误伤和漏网同样算缺陷。请**同时**做两件事：

1. 在 `hooks/pre_tool_use.py` 的 `RULES` 里收紧对应正则。
2. 在 `scripts/test_hooks.py` 的 `CASES` 里加一条 `ALLOW` 用例，锁住这个行为。

只改正则不加用例，下次改规则时同样的误伤会回来。

### 钩子执行了两次

在本仓库里又安装了本插件时，`settings.json` 与 `hooks.json` 会同时命中。
当前钩子只做只读判断，幂等无副作用，可以忽略。自己新增钩子时请保持这一性质。

---

## 环境与工具链

### 原生 Windows 下跑不起来

不支持。请改用 WSL2，见 [01 · 快速开始](01-getting-started.md) 的「运行环境」。

### 在 WSL 里一切都很慢 / 权限位丢失

仓库大概率克隆在 `/mnt/c/...` 下。移到 WSL 的 Linux 文件系统：

```bash
cd ~ && git clone <repo-url> agent-dev-kit
```

`bootstrap.sh` 检测到 `/mnt/` 路径会给出警告。

### `rtk` / `cgc` 提示 command not found

两者都是**可选增强**，缺失不影响校验与技能。要修就把用户级 bin 加进 PATH：

```bash
export PATH="$HOME/.local/bin:$PATH"    # 写进 ~/.zshrc 或 ~/.bashrc 持久生效
```

### `make setup` 装 codegraph 失败

`codegraphcontext` 要求 Python ≥ 3.10，而本仓库自身只要求 3.8。脚本会先尝试用
`uv` 装一个独立的 3.12，失败则回退 pip。都失败也只是降级提醒，可以先跳过：

```bash
bash scripts/bootstrap.sh --skip-codegraph
```

### codegraph MCP 连不上 / 查不到符号

先确认索引建过——MCP 服务器起来了不代表有数据：

```bash
make index
cgc --database kuzudb --path ./.cgc/graph.kuzu stats
```

`src/` 为空时索引里自然没有业务代码符号。

### github MCP 报鉴权失败

需要环境变量 `GITHUB_PERSONAL_ACCESS_TOKEN`。它在 `.mcp.json` 里以
`${GITHUB_PERSONAL_ACCESS_TOKEN}` 引用，不要把 token 直接写进文件——`.env`
与 `*.pem` 已在 `.claude/settings.json` 的 `deny` 列表里。

---

## 校验失败对照

| 报错关键词 | 处理 |
| --- | --- |
| `缺少 SKILL.md` | 用 `make new-skill NAME=...` 生成，别手工建目录 |
| `name '...' 与目录名 '...' 不一致` | 改 frontmatter 或改目录名，二者必须相同 |
| `技能脚本路径不完整` | 按提示改成 `${CLAUDE_PLUGIN_ROOT}/skills/<name>/...` |
| `外部 source 必须提供 40 位 'sha'` | 外部插件必须锁 commit，不能只写分支名 |
| `plugin.json 与 marketplace.json 的 description 不一致` | 两处元信息保持同步 |
| `钩子脚本不存在` | 改了脚本名后同步改注册清单 |
| `带 shebang 但 git 中记录为不可执行` | `git update-index --chmod=+x <path>` |
| `含 CRLF 换行` | 转成 LF；不要把 `core.autocrlf` 设为 `true` |
| `.gitattributes 缺少换行规则` | 不要删 `.gitattributes` 里的 `eol=lf` 规则 |

---

## 还是没解决

1. `make check` 看环境，`make validate` 看结构，`make test` 看钩子——先定位到层。
2. 复现命令与完整输出一起提 issue，注明平台（Linux / macOS / WSL2）与
   `python3 --version`。
