.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

# 工程层自己的 make 目标住在 Makefile.product（可选，不存在就忽略）。
# 单独一个文件是为了让升级脚手架时不会和你的目标冲突——本文件属于脚手架层。
# 在那里定义 test-product / lint-product 等目标，`make help` 会自动列出带 ## 注释的项。
-include Makefile.product

.PHONY: help setup check validate test new-skill index lint clean

help: ## 显示可用命令
	@echo "agent-dev-kit — 常用命令"
	@echo
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "示例: make setup && make validate"

setup: ## 一键安装工具链并初始化项目（幂等）
	@bash scripts/bootstrap.sh

check: ## 只检查环境，不安装任何东西
	@bash scripts/bootstrap.sh --check

validate: ## 校验仓库结构（提交前必跑）
	@python3 scripts/validate.py

test: ## 运行回归测试：脚手架层 + 工程层 test-product（若已定义）
	@python3 scripts/test_hooks.py
	@python3 scripts/test_release_notes.py
	@if $(MAKE) -n test-product >/dev/null 2>&1; then \
		echo; echo "→ 检测到 test-product，运行工程层测试"; \
		$(MAKE) --no-print-directory test-product; \
	else \
		echo "（未定义 test-product，跳过工程层测试；在 Makefile.product 里定义即可）"; \
	fi

new-skill: ## 新建技能，用法: make new-skill NAME=my-skill
	@if [ -z "$(NAME)" ]; then \
		echo "用法: make new-skill NAME=my-skill" >&2; exit 1; \
	fi
	@python3 scripts/new_skill.py "$(NAME)"

index: ## 建立/刷新 codegraph 代码图谱索引
	@cgc --database kuzudb --path ./.cgc/graph.kuzu index .

lint: ## 对 shell 脚本运行 shellcheck，对 Python 脚本做语法检查
	@if command -v shellcheck >/dev/null 2>&1; then \
		find hooks scripts -name '*.sh' -type f -print0 | xargs -0 shellcheck && echo "✓ shellcheck 通过"; \
	else \
		echo "未安装 shellcheck，跳过（brew install shellcheck）"; \
	fi
	@python3 -m compileall -q hooks scripts >/dev/null && echo "✓ Python 语法检查通过"

clean: ## 清理本地生成的索引与缓存
	@rm -rf .cgc
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ 已清理 .cgc/ 与 __pycache__/"
