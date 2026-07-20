#!/bin/bash
set -u
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"

export PATH="$repo_root/jobs/tests/stubs:$PATH"

# 造一个假仓库：jobs/ 是真实目录，里面用符号链接指向真仓库要用到的
# 具体脚本（而不是把整个 jobs/ 符号链接回去），这样 worklist 写到
# $root/jobs/worklists 时落在假仓库自己的物理目录里，不会串到真仓库。
# stage 目录用 fixture。
setup_fakerepo() {
    local root=$1
    mkdir -p "$root/jobs"
    ln -s "$repo_root/jobs/submit_stage.sh" "$root/jobs/submit_stage.sh"
    ln -s "$repo_root/jobs/job_array.sh" "$root/jobs/job_array.sh"
    ln -s "$repo_root/jobs/run_one.sh" "$root/jobs/run_one.sh"
    mkdir -p "$root/stage1_eos_coarse"
}

it "扫描出全部未完成任务并按 chunk 切块"
tmp=$(mktemp -d)
setup_fakerepo "$tmp"
make_fixture "$tmp/stage1_eos_coarse" DFT_0001 2.85 2.90 2.95
make_fixture "$tmp/stage1_eos_coarse" DFT_0002 3.01 3.05
out=$(cd "$tmp" && REPO_ROOT="$tmp" SUBMIT_CMD=true bash jobs/submit_stage.sh 1 --chunk 2 2>&1)
assert_eq "0" "$?" "退出码"
wl=$(printf '%s\n' "$out" | sed -n 's/^worklist: //p')
assert_file "$wl/chunk_0001" "第 1 块"
assert_file "$wl/chunk_0002" "第 2 块"
assert_file "$wl/chunk_0003" "第 3 块"
assert_eq "2" "$(wc -l < "$wl/chunk_0001")" "第 1 块 2 行"
assert_eq "1" "$(wc -l < "$wl/chunk_0003")" "第 3 块 1 行（余数）"
assert_contains "$wl/chunk_0001" "stage1_eos_coarse/DFT_0001/DFT_0001_2.85.kgrn" "路径相对仓库根"

it "跳过已完成的点"
tmp2=$(mktemp -d)
setup_fakerepo "$tmp2"
make_fixture "$tmp2/stage1_eos_coarse" DFT_0001 2.85 2.90
mkdir -p "$tmp2/stage1_eos_coarse/DFT_0001/kfcd"
echo "KFCD FINISHED" > "$tmp2/stage1_eos_coarse/DFT_0001/kfcd/DFT_0001_2.85.prn"
out=$(cd "$tmp2" && REPO_ROOT="$tmp2" SUBMIT_CMD=true bash jobs/submit_stage.sh 1 --chunk 10 2>&1)
wl=$(printf '%s\n' "$out" | sed -n 's/^worklist: //p')
assert_eq "1" "$(wc -l < "$wl/chunk_0001")" "只剩 1 个未完成"
assert_contains "$wl/chunk_0001" "DFT_0001_2.90.kgrn" "剩下的是未完成那个"

it "全部完成时不提交，直接退出 0"
mkdir -p "$tmp2/stage1_eos_coarse/DFT_0001/kfcd"
echo "KFCD FINISHED" > "$tmp2/stage1_eos_coarse/DFT_0001/kfcd/DFT_0001_2.90.prn"
out=$(cd "$tmp2" && REPO_ROOT="$tmp2" SUBMIT_CMD=false bash jobs/submit_stage.sh 1 2>&1)
assert_eq "0" "$?" "无事可做时退出码 0"
printf '%s\n' "$out" | grep -qi "无未完成任务" && assert_eq "1" "1" "打印无事可做" || assert_eq "有提示" "无提示" "应提示无事可做"

it "--limit 只取前 N 个"
tmp3=$(mktemp -d)
setup_fakerepo "$tmp3"
make_fixture "$tmp3/stage1_eos_coarse" DFT_0001 2.85 2.90 2.95 3.00
out=$(cd "$tmp3" && REPO_ROOT="$tmp3" SUBMIT_CMD=true bash jobs/submit_stage.sh 1 --limit 2 --chunk 2 2>&1)
wl=$(printf '%s\n' "$out" | sed -n 's/^worklist: //p')
assert_eq "2" "$(wc -l < "$wl/chunk_0001")" "只有 2 个任务"
assert_no_file "$wl/chunk_0002" "不应有第 2 块"

it "--dry-run 不落盘不提交"
tmp4=$(mktemp -d)
setup_fakerepo "$tmp4"
make_fixture "$tmp4/stage1_eos_coarse" DFT_0001 2.85 2.90
out=$(cd "$tmp4" && REPO_ROOT="$tmp4" SUBMIT_CMD=false bash jobs/submit_stage.sh 1 --dry-run 2>&1)
assert_eq "0" "$?" "dry-run 退出码 0"
assert_no_file "$tmp4/jobs/worklists" "dry-run 不应创建 worklist 目录"
printf '%s\n' "$out" | grep -q "sbatch" && assert_eq "1" "1" "打印了 sbatch 命令" || assert_eq "有" "无" "应打印 sbatch 命令"

it "stage 目录不存在时报错退出 1"
tmp5=$(mktemp -d)
setup_fakerepo "$tmp5"
rm -rf "$tmp5/stage1_eos_coarse"
( cd "$tmp5" && REPO_ROOT="$tmp5" bash jobs/submit_stage.sh 1 > /dev/null 2>&1 )
assert_eq "1" "$?" "缺 stage 目录应退出 1"

it "stage 参数非法时退出 2"
( cd "$tmp" && REPO_ROOT="$tmp" bash jobs/submit_stage.sh 9 > /dev/null 2>&1 )
assert_eq "2" "$?" "非法 stage 退出 2"

rm -rf "$tmp" "$tmp2" "$tmp3" "$tmp4" "$tmp5"
summary
