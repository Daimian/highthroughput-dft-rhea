#!/bin/bash
# 跑一个 EMTO KGRN+KFCD 点。
# 用法: jobs/run_one.sh <path/to/JOB.kgrn>   （路径相对当前工作目录）
#
# 必须 cd 进合金目录后再执行：.kgrn 里的 DIR002=kgrn/、DIR011=kgrn/tmp/ 都是
# 相对 cwd 的路径，从仓库根直接跑会让所有合金写进同一个 ./kgrn/。
#
# 环境变量:
#   EMTO_TIMEOUT  单个二进制的墙钟上限，秒，默认 7200
#   WORKLIST_DIR  非空时向 $WORKLIST_DIR/timing.log 追加
#                 "<job> <kgrn秒> <kfcd秒> <退出码>"
#   EMTO_CLEANUP  设为 1 时才删除 KGRN 中间大文件；默认不设，保留中间文件
#                 （便于在冒烟测试阶段排查 SCF 收敛问题），仅在大规模跑批时显式开启
#
# 退出码: 0 = 成功或此前已完成；非 0 = 该点失败（124 = 超时）
set -u

f=${1:?用法: run_one.sh <path/to/JOB.kgrn>}
dir=$(dirname "$f")
job=$(basename "$f" .kgrn)
timeout_s=${EMTO_TIMEOUT:-7200}

cd "$dir" || exit 1
mkdir -p kgrn/tmp kfcd

# 记一行计时。单行 <4096 字节的 >> 追加在 96 并发下是原子的，无需加锁。
log_timing() {
    [ -n "${WORKLIST_DIR:-}" ] || return 0
    printf '%s %s %s %s\n' "$job" "$1" "$2" "$3" >> "$WORKLIST_DIR/timing.log"
}

# 删掉大中间文件，保留 .prn 供分析阶段解析。默认不启用，需显式设置
# EMTO_CLEANUP=1（例如大规模跑批时）。
# 安全性：已完成的点下次直接跳过，未完成的点本来就要从头重算，
# 不存在从已有势函数热启动的需求。
cleanup() {
    [ "${EMTO_CLEANUP:-0}" = "1" ] || return 0
    rm -f "kgrn/$job.atm" "kgrn/$job.chd" "kgrn/$job.pot" "kgrn/$job.zms"
    rm -f "kgrn/tmp/$job"*
}

# 幂等：已完成则跳过
if [ -f "kfcd/$job.prn" ] && grep -qi finished "kfcd/$job.prn"; then
    exit 0
fi

t0=$SECONDS
timeout "$timeout_s" kgrn_cpa < "$job.kgrn" > "kgrn/$job.out" 2>&1
rc=$?
t_kgrn=$((SECONDS - t0))

# SCF 没收敛就别浪费时间跑 KFCD。该点会被 error_collector.py 记为
# scf_not_converged / missing_output。
if [ "$rc" -ne 0 ] || ! grep -qi finished "kgrn/$job.prn" 2>/dev/null; then
    [ "$rc" -eq 0 ] && rc=1
    log_timing "$t_kgrn" 0 "$rc"
    cleanup
    exit "$rc"
fi

t1=$SECONDS
timeout "$timeout_s" kfcd_cpa < "$job.kfcd" > "kfcd/$job.out" 2>&1
rc=$?
t_kfcd=$((SECONDS - t1))

if [ "$rc" -eq 0 ] && ! grep -qi finished "kfcd/$job.prn" 2>/dev/null; then
    rc=1
fi

log_timing "$t_kgrn" "$t_kfcd" "$rc"
cleanup
exit "$rc"
