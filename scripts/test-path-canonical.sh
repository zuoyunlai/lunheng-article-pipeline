#!/usr/bin/env bash
# test-path-canonical.sh — path-canonical.py 测试套件（v2.9.1）

set -uo pipefail

SCRIPT="$(dirname "$0")/path-canonical.py"
BASE_DIR="/tmp/lunheng-test-$$"

# 测试计数器
PASS=0
FAIL=0

# 辅助函数
test_case() {
    local name="$1"
    local target="$2"
    local expect_exit="$3"
    local expect_pattern="${4:-}"
    
    echo "Testing: $name"
    if output=$("$SCRIPT" "$BASE_DIR" "$target" 2>&1); then
        exit_code=0
    else
        exit_code=$?
    fi
    
    if [[ $exit_code -eq $expect_exit ]]; then
        if [[ -n "$expect_pattern" && ! "$output" =~ $expect_pattern ]]; then
            echo "  ❌ FAIL: Output mismatch (expected pattern: $expect_pattern)"
            echo "     Got: $output"
            ((FAIL++))
        else
            echo "  ✅ PASS"
            ((PASS++))
        fi
    else
        echo "  ❌ FAIL: Expected exit $expect_exit, got $exit_code"
        echo "     Output: $output"
        ((FAIL++))
    fi
}

# 准备测试环境
mkdir -p "$BASE_DIR"

echo "=== Path Canonical Validator Tests ==="
echo "Base dir: $BASE_DIR"
echo

# 合法路径
test_case "Valid relative path" "drafts/outline.md" 0 "$BASE_DIR/drafts/outline.md"
test_case "Valid nested path" "data/sources/paper1.pdf" 0 "$BASE_DIR/data/sources/paper1.pdf"
test_case "Single file" "status.md" 0 "$BASE_DIR/status.md"

# 路径遍历攻击
test_case "Parent traversal" "../etc/passwd" 1 "Path traversal detected"
test_case "Multiple parent traversal" "../../etc/passwd" 1 "Path traversal detected"
test_case "Hidden parent traversal" "drafts/../../etc/passwd" 1 "Path traversal detected"

# 绝对路径
test_case "Absolute path" "/etc/passwd" 1 "Absolute path not allowed"
test_case "Absolute path in base" "$BASE_DIR/drafts/outline.md" 1 "Absolute path not allowed"

# 边界情况
test_case "Current dir" "." 0 "$BASE_DIR"
test_case "Current dir explicit" "./" 0 "$BASE_DIR"
test_case "Redundant slashes" "drafts//outline.md" 0 "$BASE_DIR/drafts/outline.md"

# 符号链接场景（需要实际文件系统）
mkdir -p "$BASE_DIR/drafts"
echo "test" > "$BASE_DIR/drafts/real.md"
ln -s "$BASE_DIR/drafts/real.md" "$BASE_DIR/drafts/link.md" 2>/dev/null || true
test_case "Symlink within base" "drafts/link.md" 0 "$BASE_DIR/drafts/real.md"

# 清理
rm -rf "$BASE_DIR"

# 汇总
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
