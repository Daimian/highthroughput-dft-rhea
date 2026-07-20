#!/bin/bash
# 跑 jobs/tests/ 下所有 test_*.sh 并汇总。
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

failed=0
for t in test_*.sh; do
    echo "=== $t ==="
    if bash "$t"; then
        echo "=== $t 通过 ==="
    else
        echo "=== $t 失败 ==="
        failed=$((failed + 1))
    fi
    echo
done

if [ "$failed" -eq 0 ]; then
    echo "全部测试通过"
else
    echo "$failed 个测试文件失败"
fi
exit "$failed"
