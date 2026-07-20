#!/bin/bash
# 跑一个 EMTO KGRN+KFCD 点。
# 用法: jobs/run_one.sh <path/to/JOB.kgrn>   （路径相对当前工作目录）
#
# 必须 cd 进合金目录后再执行：.kgrn 里的 DIR002=kgrn/、DIR011=kgrn/tmp/ 都是
# 相对 cwd 的路径，从仓库根直接跑会让所有合金写进同一个 ./kgrn/。
set -u

f=${1:?用法: run_one.sh <path/to/JOB.kgrn>}
dir=$(dirname "$f")
job=$(basename "$f" .kgrn)

cd "$dir" || exit 1
mkdir -p kgrn/tmp kfcd

kgrn_cpa < "$job.kgrn" > "kgrn/$job.out" 2>&1
kfcd_cpa < "$job.kfcd" > "kfcd/$job.out" 2>&1
