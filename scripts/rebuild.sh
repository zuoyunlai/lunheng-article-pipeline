#!/usr/bin/env bash
# 论衡 phase-order.yaml 一键重建（v2.15.7 新增）
# 用法（生成器无 --build 旗标：无参 = 生成/刷新；--check = 仅校验）：
#   ./scripts/rebuild.sh                 # 生成/刷新 phase-order.yaml（无参调生成器）
#   ./scripts/rebuild.sh check           # 仅门 AA 校验
#   ./scripts/rebuild.sh build-check     # 先生成再校验（推荐）
#   ./scripts/rebuild.sh diff            # 与上次生成做 diff（看本轮切片变更影响）

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
SCRIPT="$ROOT/scripts/phase-order-slice.py"

if [[ ! -f "$SCRIPT" ]]; then
  echo "❌ 找不到 $SCRIPT" >&2
  exit 2
fi

ACTION="${1:-build}"
case "$ACTION" in
  --build|build)
    echo "🔨 生成/刷新 phase-order.yaml（生成器无参调用）..."
    "$PY" "$SCRIPT"
    echo "✅ 生成完成"
    ;;
  --check|check)
    echo "🔍 门 AA 校验 ..."
    "$PY" "$SCRIPT" --check
    ;;
  --build-check|build-check)
    "$PY" "$SCRIPT"
    "$PY" "$SCRIPT" --check
    ;;
  --diff|diff)
    ASSEMBLY="$ROOT/references/_shared/真源/phase-order.yaml"
    cp "$ASSEMBLY" /tmp/phase-order.yaml.prev
    "$PY" "$SCRIPT" --build
    diff -u /tmp/phase-order.yaml.prev "$ASSEMBLY" || true
    ;;
  *)
    echo "❓ 未知动作：$ACTION" >&2
    echo "支持：build | check | build-check | diff" >&2
    exit 2
    ;;
esac

echo ""
echo "📌 说明：OpenClaw 当前无自定义 slash 命令注册面（已核对 openclaw.json），"
echo "   本脚本是唯一入口：主人 shell 直跑，或让 agent 经 exec 调用。"