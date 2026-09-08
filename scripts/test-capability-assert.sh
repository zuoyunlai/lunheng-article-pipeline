#!/usr/bin/env bash
# test-capability-assert.sh — capability-assert.py 测试套件（v2.9.1）

set -uo pipefail

SCRIPT="$(dirname "$0")/capability-assert.py"

# 测试计数器
PASS=0
FAIL=0

# 辅助函数
test_case() {
    local name="$1"
    local role="$2"
    shift 2
    local capabilities=("$@")
    local expect_exit="${capabilities[-1]}"
    unset 'capabilities[-1]'
    
    echo "Testing: $name"
    if output=$("$SCRIPT" "$role" "${capabilities[@]}" 2>&1); then
        exit_code=0
    else
        exit_code=$?
    fi
    
    if [[ $exit_code -eq $expect_exit ]]; then
        echo "  ✅ PASS"
        ((PASS++))
    else
        echo "  ❌ FAIL: Expected exit $expect_exit, got $exit_code"
        echo "     Output: $output"
        ((FAIL++))
    fi
}

echo "=== Capability Assertion Tests ==="
echo

# 合法能力集
test_case "T1 valid capabilities" T1 read web_search tavily_search 0
test_case "T5 writer capabilities" T5 read write edit ask_user 0
test_case "T6 critic capabilities" T6 read memory_search ov_search 0
test_case "T7 auditor capabilities" T7 read memory_get ov_read 0
test_case "T8 final check minimal" T8 read 0

# 禁用能力
test_case "T1 forbidden exec" T1 read exec 1
test_case "T5 forbidden process" T5 write process 1
test_case "T6 forbidden terminal" T6 read terminal 1
test_case "T7 forbidden secrets" T7 read secrets 1
test_case "T0 forbidden browser" T0 read browser 1

# 未知能力
test_case "T1 unknown capability" T1 read unknown_tool 1
test_case "T5 typo capability" T5 read wriet 1

# 边界情况
test_case "Empty capabilities" T1 1  # 最后一个参数是期望退出码
test_case "Unknown role" T99 read 1
test_case "Empty role" "" read 1

# 混合合法+非法
test_case "Mixed valid and forbidden" T5 read write exec 1

# 清理
echo
echo "=== Test Summary ==="
echo "✅ PASS: $PASS"
echo "❌ FAIL: $FAIL"

if [[ $FAIL -eq 0 ]]; then
    echo "All tests passed!"
    exit 0
else
    echo "Some tests failed."
    exit 1
fi
