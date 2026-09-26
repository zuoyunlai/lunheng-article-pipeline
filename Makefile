# 论衡开发工具 Makefile（P1-5 修订 2026-09-08）

.PHONY: help test lint format audit changelog-check path-canonical scripts-index clean install

help:
	@echo "论衡开发工具"
	@echo ""
	@echo "可用命令："
	@echo "  make install    - 安装开发依赖"
	@echo "  make test       - 运行测试套件"
	@echo "  make lint       - 运行代码检查（ShellCheck + Python 语法）"
	@echo "  make format     - 格式化 Python 代码（black + isort）"
	@echo "  make audit      - 运行自审门"
	@echo "  make changelog-check - 校验 changelog 完整性（每个版本 tag 都有章节）"
	@echo "  make scripts-index - 刷新 scripts/README.md 脚本索引（从脚本头部生成；漂移由 pytest 锁死）"
	@echo "  make preflight  - 发版前置闸（四查一停：在飞链 / 编号占用 / 工作区干净 / CI 不红）"
	@echo "  make clean      - 清理临时文件"
	@echo "  make all        - 运行全部检查（lint + test + audit + changelog-check）"

install:
	@echo "安装依赖..."
	pip install -r requirements.txt
	@echo "✓ 依赖安装完成"

test:
	@echo "运行测试套件..."
	pytest -v --tb=short
	@echo ""
	@echo "运行 capability-assert 测试..."
	bash scripts/test-capability-assert.sh
	@echo ""
	@echo "运行 path-canonical 测试..."
	bash scripts/test-path-canonical.sh
	@echo "✓ 测试完成"

path-canonical:
	@echo "运行 path-canonical 测试..."
	bash scripts/test-path-canonical.sh

lint:
	@command -v shellcheck >/dev/null 2>&1 || { echo "❌ 未找到 shellcheck（Debian/Ubuntu: sudo apt install shellcheck）；缺工具会静默跳过全部 Shell 检查，故此处 fail-loud" >&2; exit 1; }
	@echo "运行 ShellCheck..."
	@# v2.12.40 修复（2026-09-14）：去掉 `|| true` —— 旧写法吞掉退出码，使 make lint / make all
	@#   永不因 ShellCheck 失败（等于没有 lint 门）。风格噪声改由 `--severity=warning` **显式分级**
	@#   承受（与 .github/workflows/quality.yml 的 `severity: warning` 同口径），而不是吞掉退出码。
	shellcheck --severity=warning scripts/*.sh
	@echo ""
	@echo "检查 Python 语法..."
	python3 -m py_compile scripts/*.py tests/*.py
	@echo "✓ 代码检查完成"

format:
	@echo "格式化 Python 代码..."
	black scripts/ tests/
	isort scripts/ tests/
	@echo "✓ 格式化完成"

audit:
	@echo "运行自审门..."
	bash scripts/self-audit-gate.sh
	@echo "✓ 自审门完成"

changelog-check:
	@echo "校验 changelog 完整性..."
	python3 scripts/changelog-check.py --check
	@echo "✓ changelog 完整性校验完成（--online 可追加校验 GitHub Release 覆盖）"

# 脚本索引（派生视图，真源 = 各脚本头部注释）：改了脚本头就重跑本目标
# 判据与 tests/test_scripts_index.py 同源（同一个 --check），索引落在 scripts/README.md
scripts-index:
	@python3 scripts/gen-scripts-index.py

# 发版前置闸（教训 #332，四查一停）——任何对外发版动作（push / tag / Release / 净化包）之前必跑
# 本链自身会话 key 用 LUNHENG_PREFLIGHT_SELF_SESSION 传入，否则本链会被闸算作在飞链（失败关闭）。
# 指定目标编号：make preflight PREFLIGHT_TAG=v2.12.21（默认取 SKILL.md frontmatter 版本）
preflight:
	@OPENCLAW_BIN="$${LUNHENG_OPENCLAW_BIN:-$$(command -v openclaw 2>/dev/null || true)}"; \
	if [ -z "$$OPENCLAW_BIN" ] && [ -z "$${PREFLIGHT_SESSIONS_FILE:-}" ]; then \
		echo "❌ 未找到 openclaw。请设置 LUNHENG_OPENCLAW_BIN，或提供 PREFLIGHT_SESSIONS_FILE 快照。" >&2; exit 2; \
	fi; \
	if [ -n "$$PREFLIGHT_SESSIONS_FILE" ]; then \
		bash scripts/release-preflight.sh $(PREFLIGHT_TAG) --sessions-file "$$PREFLIGHT_SESSIONS_FILE"; \
	else \
		LUNHENG_PREFLIGHT_SESSIONS_CMD="$$OPENCLAW_BIN sessions list --json --all-agents --limit all" bash scripts/release-preflight.sh $(PREFLIGHT_TAG); \
	fi

clean:
	@echo "清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	@echo "✓ 清理完成"

all: lint test audit changelog-check
	@echo ""
	@echo "✅ 全部检查通过！"

# 版本同步（发布前必跑）
sync-version:
	@echo "同步版本号..."
	bash scripts/sync-version.sh
	@echo "✓ 版本号同步完成"

# 构建 ClawHub 发布包
build-release:
	@echo "构建 ClawHub 发布包..."
	bash scripts/build-clawhub-release.sh
	@echo "✓ 发布包构建完成"

# 完整发布流程（发版前置闸 + 版本同步 + 审计 + 构建）
# 闸在最前：工作区不干净 / 有在飞链 / 编号被占 ⇒ 一步都不做（发版是收口动作，不是推进动作）
release: preflight sync-version all build-release
	@echo ""
	@echo "✅ 发布准备完成！"
	@echo "下一步: git commit + git tag + git push"
