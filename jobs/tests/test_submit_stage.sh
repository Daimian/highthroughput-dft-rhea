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

it "--chunk 选项缺少值时报错退出 2"
tmp6=$(mktemp -d)
setup_fakerepo "$tmp6"
make_fixture "$tmp6/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp6" && REPO_ROOT="$tmp6" bash jobs/submit_stage.sh 1 --chunk 2>&1)
assert_eq "2" "$?" "--chunk 缺少值退出 2"
printf '%s\n' "$err" | grep -q "错误：" && assert_eq "1" "1" "--chunk 缺少值报错" || assert_eq "有错误" "无错误" "--chunk 缺少值应报错"

it "--chunk 非整数值时报错退出 2"
tmp7=$(mktemp -d)
setup_fakerepo "$tmp7"
make_fixture "$tmp7/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp7" && REPO_ROOT="$tmp7" bash jobs/submit_stage.sh 1 --chunk abc 2>&1)
assert_eq "2" "$?" "--chunk 非整数退出 2"
printf '%s\n' "$err" | grep -q "正整数" && assert_eq "1" "1" "--chunk 非整数报错提示" || assert_eq "有提示" "无提示" "--chunk 非整数应提示正整数"

it "--chunk 零值时报错退出 2"
tmp8=$(mktemp -d)
setup_fakerepo "$tmp8"
make_fixture "$tmp8/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp8" && REPO_ROOT="$tmp8" bash jobs/submit_stage.sh 1 --chunk 0 2>&1)
assert_eq "2" "$?" "--chunk 零值退出 2"
printf '%s\n' "$err" | grep -q "正整数" && assert_eq "1" "1" "--chunk 零值报错提示" || assert_eq "有提示" "无提示" "--chunk 零值应提示正整数"

it "--maxpar 选项缺少值时报错退出 2"
tmp9=$(mktemp -d)
setup_fakerepo "$tmp9"
make_fixture "$tmp9/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp9" && REPO_ROOT="$tmp9" bash jobs/submit_stage.sh 1 --maxpar 2>&1)
assert_eq "2" "$?" "--maxpar 缺少值退出 2"
printf '%s\n' "$err" | grep -q "错误：" && assert_eq "1" "1" "--maxpar 缺少值报错" || assert_eq "有错误" "无错误" "--maxpar 缺少值应报错"

it "--limit 选项缺少值时报错退出 2"
tmp10=$(mktemp -d)
setup_fakerepo "$tmp10"
make_fixture "$tmp10/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp10" && REPO_ROOT="$tmp10" bash jobs/submit_stage.sh 1 --limit 2>&1)
assert_eq "2" "$?" "--limit 缺少值退出 2"
printf '%s\n' "$err" | grep -q "错误：" && assert_eq "1" "1" "--limit 缺少值报错" || assert_eq "有错误" "无错误" "--limit 缺少值应报错"

it "--limit 零值允许（无限制）"
tmp11=$(mktemp -d)
setup_fakerepo "$tmp11"
make_fixture "$tmp11/stage1_eos_coarse" DFT_0001 2.85 2.90 2.95
out=$(cd "$tmp11" && REPO_ROOT="$tmp11" SUBMIT_CMD=true bash jobs/submit_stage.sh 1 --limit 0 2>&1)
assert_eq "0" "$?" "--limit 0 应成功"
wl=$(printf '%s\n' "$out" | sed -n 's/^worklist: //p')
assert_eq "3" "$(wc -l < "$wl/chunk_0001")" "--limit 0 应包含全部 3 个任务"

it "--limit 非整数值时报错退出 2"
tmp12=$(mktemp -d)
setup_fakerepo "$tmp12"
make_fixture "$tmp12/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp12" && REPO_ROOT="$tmp12" bash jobs/submit_stage.sh 1 --limit xyz 2>&1)
assert_eq "2" "$?" "--limit 非整数退出 2"
printf '%s\n' "$err" | grep -q "非负整数" && assert_eq "1" "1" "--limit 非整数报错提示" || assert_eq "有提示" "无提示" "--limit 非整数应提示非负整数"

it "--time 选项缺少值时报错退出 2"
tmp13=$(mktemp -d)
setup_fakerepo "$tmp13"
make_fixture "$tmp13/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp13" && REPO_ROOT="$tmp13" bash jobs/submit_stage.sh 1 --time 2>&1)
assert_eq "2" "$?" "--time 缺少值退出 2"
printf '%s\n' "$err" | grep -q "错误：" && assert_eq "1" "1" "--time 缺少值报错" || assert_eq "有错误" "无错误" "--time 缺少值应报错"

it "--partition 选项缺少值时报错退出 2"
tmp14=$(mktemp -d)
setup_fakerepo "$tmp14"
make_fixture "$tmp14/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp14" && REPO_ROOT="$tmp14" bash jobs/submit_stage.sh 1 --partition 2>&1)
assert_eq "2" "$?" "--partition 缺少值退出 2"
printf '%s\n' "$err" | grep -q "错误：" && assert_eq "1" "1" "--partition 缺少值报错" || assert_eq "有错误" "无错误" "--partition 缺少值应报错"

it "--chunk 前导零时报错退出 2（octal 回归测试）"
tmp15=$(mktemp -d)
setup_fakerepo "$tmp15"
make_fixture "$tmp15/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp15" && REPO_ROOT="$tmp15" bash jobs/submit_stage.sh 1 --chunk 010 2>&1)
assert_eq "2" "$?" "--chunk 010 应退出 2"
printf '%s\n' "$err" | grep -q "错误：" && assert_eq "1" "1" "--chunk 010 应报错" || assert_eq "有错误" "无错误" "--chunk 010 应报错"

it "--limit 前导零时报错退出 2（octal 回归测试）"
tmp16=$(mktemp -d)
setup_fakerepo "$tmp16"
make_fixture "$tmp16/stage1_eos_coarse" DFT_0001 2.85
err=$(cd "$tmp16" && REPO_ROOT="$tmp16" bash jobs/submit_stage.sh 1 --limit 009 2>&1)
assert_eq "2" "$?" "--limit 009 应退出 2"
printf '%s\n' "$err" | grep -q "错误：" && assert_eq "1" "1" "--limit 009 应报错" || assert_eq "有错误" "无错误" "--limit 009 应报错"

it "传给 sbatch 的参数正确"
tmp6=$(mktemp -d)
setup_fakerepo "$tmp6"
make_fixture "$tmp6/stage1_eos_coarse" DFT_0001 2.85 2.90 2.95
cap="$tmp6/sbatch_args.txt"
out=$(cd "$tmp6" && REPO_ROOT="$tmp6" SBATCH_CAPTURE="$cap" bash jobs/submit_stage.sh 1 \
        --chunk 2 --maxpar 3 --time 02:00:00 --partition deflt_short 2>&1)
assert_file "$cap" "sbatch 被调用"
assert_eq "1" "$(grep -cx -- '--array=1-2%3' "$cap")" "array 规格：2 块、并发 3"
assert_eq "1" "$(grep -cx '02:00:00' "$cap")" "时限"
assert_eq "1" "$(grep -cx 'deflt_short' "$cap")" "分区"
assert_eq "1" "$(grep -cx 'emto_s1' "$cap")" "作业名"
wl6=$(printf '%s\n' "$out" | sed -n 's/^worklist: //p')
assert_eq "1" "$(grep -cx -- "--export=ALL,WORKLIST_DIR=${wl6}" "$cap")" "导出 WORKLIST_DIR"
assert_eq "1" "$(grep -cx -- "$tmp6/jobs/job_array.sh" "$cap")" "作业体路径"
assert_eq "1" "$(printf '%s\n' "$out" | grep -c 'Submitted batch job')" "透传 sbatch 输出"

it "默认值：chunk=1000 maxpar=8 time=24:00:00 partition=deflt"
tmp7=$(mktemp -d)
setup_fakerepo "$tmp7"
make_fixture "$tmp7/stage1_eos_coarse" DFT_0001 2.85
cap2="$tmp7/sbatch_args.txt"
out7=$(cd "$tmp7" && REPO_ROOT="$tmp7" SBATCH_CAPTURE="$cap2" bash jobs/submit_stage.sh 1 2>&1)
assert_eq "1" "$(grep -cx -- '--array=1-1%8' "$cap2")" "默认 maxpar=8，1 个任务 1 块"
assert_eq "1" "$(grep -cx '24:00:00' "$cap2")" "默认时限"
assert_eq "1" "$(grep -cx 'deflt' "$cap2")" "默认分区"
assert_eq "1" "$(printf '%s\n' "$out7" | grep -cE '块数:[[:space:]]+1（每块 1000）')" "默认 chunk=1000 体现在块数统计打印中"

rm -rf "$tmp" "$tmp2" "$tmp3" "$tmp4" "$tmp5" "$tmp6" "$tmp7" "$tmp8" "$tmp9" "$tmp10" "$tmp11" "$tmp12" "$tmp13" "$tmp14" "$tmp15" "$tmp16"
summary
