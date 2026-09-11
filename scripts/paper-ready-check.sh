#!/usr/bin/env bash
# paper-ready-check.sh —— 论衡 v2.12.0 可发表性 48 项本地自动检查封装
# 教训 #252：把内容质量门从 SKILL.md 散文层迁回机器可执行层
# 配套判定表：references/_shared/可发表性判定表.md
# 配套 python：scripts/paper-ready-check.py
#
# ⚠️ 本脚本为本地开发者工具，ClawHub 净化版已剥离（build-clawhub-release.sh 排除 scripts/）

set -euo pipefail
PROJECT="${1:?用法: bash scripts/paper-ready-check.sh <项目名>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/paper-ready-check.py" "$PROJECT"
