#!/usr/bin/env bash
# 一键安装本仓库所需的工具链。
#
# 用法:
#   bash scripts/bootstrap.sh              # 安装全部（缺什么装什么）
#   bash scripts/bootstrap.sh --check      # 只检查环境，不安装
#   bash scripts/bootstrap.sh --skip-rtk   # 跳过 rtk
#   bash scripts/bootstrap.sh --skip-codegraph
#   bash scripts/bootstrap.sh --index      # 安装后立即建立 codegraph 索引
#
# 幂等：已安装的工具会跳过，可重复执行。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CHECK_ONLY=0
SKIP_RTK=0
SKIP_CODEGRAPH=0
DO_INDEX=0

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --skip-rtk) SKIP_RTK=1 ;;
    --skip-codegraph) SKIP_CODEGRAPH=1 ;;
    --index) DO_INDEX=1 ;;
    -h|--help)
      sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^#\{1,\} \{0,1\}//'
      exit 0
      ;;
    *)
      echo "未知参数: ${arg}（用 --help 查看用法）" >&2
      exit 1
      ;;
  esac
done

# ---------- 输出辅助 ----------
if [[ -t 1 ]]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
  C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_OFF=""
fi

ok()   { echo "${C_OK}✓${C_OFF} $*"; }
warn() { echo "${C_WARN}!${C_OFF} $*"; }
err()  { echo "${C_ERR}✗${C_OFF} $*" >&2; }
info() { echo "${C_DIM}  $*${C_OFF}"; }
step() { echo; echo "── $* ──"; }

WARNINGS=0

has() { command -v "$1" >/dev/null 2>&1; }

# 部分工具（如 cgc）把版本号打到 stderr，这里统一合并捕获
version_of() { "$@" 2>&1 | head -1; }

# 把常见的用户级 bin 目录并入 PATH，便于检测刚装好的工具
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:$PATH"

detect_os() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux)  echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

OS="$(detect_os)"

# WSL 对外表现为 linux，这里单独识别只为在输出里标注清楚
is_wsl() {
  [[ -n "${WSL_DISTRO_NAME:-}" ]] && return 0
  grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null
}

# ---------- 前置检查 ----------
step "环境检查"

# 本项目只支持 WSL2 / macOS / Linux。原生 Windows（Git Bash / MSYS / Cygwin）
# 下 chmod 无效、工具链安装路径也未经验证，与其提供一套没跑通过的兼容路径，
# 不如明确拒绝并指向 WSL2。
if [[ "$OS" == "windows" ]]; then
  err "不支持原生 Windows（Git Bash / MSYS / Cygwin），请改用 WSL2"
  cat >&2 <<'EOF'

  1. 安装 WSL2（PowerShell，管理员；Windows 10 2004+ / Windows 11）:
       wsl --install -d Ubuntu
     完成后重启，从开始菜单打开 Ubuntu 终端。

  2. 在 WSL 内把仓库克隆到 Linux 文件系统，不要放在 /mnt/c:
       cd ~ && git clone <repo-url> agent-dev-kit && cd agent-dev-kit

     放在 /mnt/c 会同时踩两个坑——跨文件系统 IO 慢，且 Windows 侧的 git
     与编辑器会破坏脚本的可执行位和 LF 换行符。

  3. 在 WSL 内安装 Claude Code 与 Node.js，然后重新执行:
       bash scripts/bootstrap.sh

详见 docs/01-getting-started.md 的「运行环境」一节。
EOF
  exit 1
fi

if [[ "$OS" == "linux" ]] && is_wsl; then
  echo "操作系统: linux (WSL2${WSL_DISTRO_NAME:+ / $WSL_DISTRO_NAME})"
  if [[ "$ROOT" == /mnt/* ]]; then
    warn "仓库位于 $ROOT —— Windows 挂载盘下 IO 较慢，且可执行位与换行符可能被破坏"
    info "建议改为克隆到 WSL 的 Linux 文件系统（如 ~/agent-dev-kit）"
    WARNINGS=$((WARNINGS + 1))
  fi
else
  echo "操作系统: $OS"
fi

if ! has git; then
  err "未找到 git，请先安装 git"
  exit 1
fi
ok "git $(git --version | awk '{print $3}')"

# validate.py 需要 Python 3；仅用标准库，无需 pip 安装依赖
PYTHON=""
for candidate in python3 python; do
  if has "$candidate" && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  err "未找到 Python 3.8+，scripts/validate.py 需要它"
  info "安装方式: https://www.python.org/downloads/"
  exit 1
fi
ok "$PYTHON $("$PYTHON" -c 'import platform; print(platform.python_version())')"

if has curl; then
  ok "curl"
elif has wget; then
  ok "wget"
else
  warn "未找到 curl 或 wget，自动安装工具链将不可用"
  WARNINGS=$((WARNINGS + 1))
fi

# ---------- rtk ----------
install_rtk() {
  if has rtk; then
    ok "rtk 已安装（$(version_of rtk --version)）"
    return 0
  fi

  if [[ $CHECK_ONLY -eq 1 ]]; then
    warn "rtk 未安装"
    WARNINGS=$((WARNINGS + 1))
    return 0
  fi

  echo "正在安装 rtk（CLI 输出压缩，可省 60-90% token）..."

  if [[ "$OS" == "macos" ]] && has brew; then
    brew install rtk-ai/tap/rtk && return 0
    warn "brew 安装失败，回退到官方安装脚本"
  fi

  if has curl; then
    curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/develop/install.sh | bash && return 0
  elif has wget; then
    wget -qO- https://raw.githubusercontent.com/rtk-ai/rtk/develop/install.sh | bash && return 0
  fi

  warn "rtk 自动安装失败，可手动安装: https://github.com/rtk-ai/rtk"
  info "rtk 是可选增强，缺少它不影响仓库校验与技能使用"
  WARNINGS=$((WARNINGS + 1))
  return 0
}

# ---------- codegraph ----------
install_codegraph() {
  if has cgc; then
    ok "codegraph 已安装（$(version_of cgc --version)）"
    return 0
  fi

  if [[ $CHECK_ONLY -eq 1 ]]; then
    warn "codegraph (cgc) 未安装"
    WARNINGS=$((WARNINGS + 1))
    return 0
  fi

  echo "正在安装 codegraph（代码图谱 MCP 服务器）..."

  # codegraphcontext 要求 Python >= 3.10。uv 能自带并管理独立的 Python，
  # 避免依赖系统 Python 版本，也不污染系统环境。
  if ! has uv; then
    echo "  未找到 uv，正在安装（用于隔离安装 Python 工具）..."
    if [[ "$OS" == "macos" ]] && has brew; then
      brew install uv || true
    fi
    if ! has uv; then
      if has curl; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || true
      elif has wget; then
        wget -qO- https://astral.sh/uv/install.sh | sh || true
      fi
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    fi
  fi

  if has uv; then
    if uv tool install --python 3.12 codegraphcontext; then
      export PATH="$HOME/.local/bin:$PATH"
      return 0
    fi
    warn "uv 安装 codegraphcontext 失败"
  else
    warn "uv 不可用"
  fi

  # 回退：系统 Python 已经是 3.10+ 时直接用 pip
  if "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    info "回退到 pip 安装"
    "$PYTHON" -m pip install --user codegraphcontext && return 0
  fi

  warn "codegraph 自动安装失败，可手动安装: uv tool install --python 3.12 codegraphcontext"
  info "codegraph 是可选增强，缺少它不影响仓库校验与技能使用"
  WARNINGS=$((WARNINGS + 1))
  return 0
}

if [[ $SKIP_RTK -eq 0 ]]; then
  step "rtk (Rust Token Killer)"
  install_rtk
fi

if [[ $SKIP_CODEGRAPH -eq 0 ]]; then
  step "codegraph (CodeGraphContext)"
  install_codegraph
fi

# ---------- 项目配置 ----------
step "项目配置"

# 个人本地配置：从 .example 复制，不覆盖已存在的文件
LOCAL_SETTINGS="$ROOT/.claude/settings.local.json"
if [[ -f "$LOCAL_SETTINGS" ]]; then
  ok "已存在 .claude/settings.local.json（保持不变）"
elif [[ $CHECK_ONLY -eq 1 ]]; then
  warn "缺少 .claude/settings.local.json（安装时会从 .example 创建）"
elif [[ -f "$LOCAL_SETTINGS.example" ]]; then
  cp "$LOCAL_SETTINGS.example" "$LOCAL_SETTINGS"
  ok "已创建 .claude/settings.local.json（个人覆盖配置，不会被提交）"
fi

# 确保脚本可执行（部分系统 clone 后会丢失执行位）
missing_exec=0
fixed=0
while IFS= read -r script; do
  if [[ ! -x "$script" ]]; then
    if [[ $CHECK_ONLY -eq 1 ]]; then
      missing_exec=$((missing_exec + 1))
    else
      chmod +x "$script"
      fixed=$((fixed + 1))
    fi
  fi
done < <(find "$ROOT/hooks" "$ROOT/scripts" "$ROOT/skills" \
  \( -name '*.sh' -o -name '*.py' \) -type f 2>/dev/null)

if [[ $missing_exec -gt 0 ]]; then
  warn "有 $missing_exec 个脚本缺少可执行权限（去掉 --check 可自动修复）"
  WARNINGS=$((WARNINGS + 1))
elif [[ $fixed -gt 0 ]]; then
  ok "已修复 $fixed 个脚本的可执行权限"
else
  ok "脚本权限正常"
fi

# ---------- codegraph 索引 ----------
if [[ $DO_INDEX -eq 1 && $CHECK_ONLY -eq 0 ]]; then
  step "建立 codegraph 索引"
  if has cgc; then
    if (cd "$ROOT" && cgc --database kuzudb --path ./.cgc/graph.kuzu index .); then
      ok "索引完成"
    else
      warn "索引失败，可稍后手动执行"
    fi
  else
    warn "cgc 不可用，跳过索引"
  fi
fi

# ---------- 校验 ----------
step "仓库校验"
if (cd "$ROOT" && "$PYTHON" scripts/validate.py); then
  :
else
  err "仓库校验未通过"
  exit 1
fi

if (cd "$ROOT" && "$PYTHON" scripts/test_hooks.py); then
  :
else
  err "钩子回归测试未通过"
  exit 1
fi

# ---------- 总结 ----------
step "完成"

if has rtk; then
  ok "rtk        $(version_of rtk --version)"
else
  warn "rtk        未安装（可选）"
fi

if has cgc; then
  ok "codegraph  $(version_of cgc --version)"
else
  warn "codegraph  未安装（可选）"
fi

echo
if [[ $WARNINGS -gt 0 ]]; then
  warn "有 $WARNINGS 项提醒，但核心功能可用"
fi

cat <<EOF

后续步骤:
  1. 在 Claude Code 中安装本插件:
       /plugin marketplace add $ROOT
       /plugin install agent-dev-kit
  2. 建立代码图谱索引（首次使用 codegraph 前）:
       cgc --database kuzudb --path ./.cgc/graph.kuzu index .
  3. 新增技能:
       python3 scripts/new_skill.py <skill-name>

若 rtk / cgc 提示 command not found，请把 ~/.local/bin 加入 PATH:
  export PATH="\$HOME/.local/bin:\$PATH"
EOF
