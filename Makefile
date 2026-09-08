# 论衡开发工具 Makefile（P1-5 修订 2026-09-08）

.PHONY: help test lint format audit clean install

help:
	@echo "论衡开发工具"
	@echo ""
	@echo "可用命令："
	@echo "  make install    - 安装开发依赖"
	@echo "  make test       - 运行测试套件"
	@echo "  make lint       - 运行代码检查（ShellCheck + Python 语法）"
	@echo "  make format     - 格式化 Python 代码（black + isort）"
	@echo "  make audit      - 运行自审门"
	@echo "  make clean      - 清理临时文件"
	@echo "  make all        - 运行全部检查（lint + test + audit）"

install:
	@echo "安装依赖..."
	pip install -r requirements.txt
	@echo "✓ 依赖安装完成"

test:
	@echo "运行测试套件..."
	cd tests && pytest -v --tb=short
	@echo "✓ 测试完成"

lint:
	@echo "运行 ShellCheck..."
	shellcheck scripts/*.sh || true
	@echo ""
	@echo "检查 Python 语法..."
	python -m py_compile scripts/*.py tests/*.py
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

clean:
	@echo "清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	@echo "✓ 清理完成"

all: lint test audit
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

# 完整发布流程（版本同步 + 审计 + 构建）
release: sync-version all build-release
	@echo ""
	@echo "✅ 发布准备完成！"
	@echo "下一步: git commit + git tag + git push"
