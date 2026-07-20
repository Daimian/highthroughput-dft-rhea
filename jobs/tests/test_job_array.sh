#!/bin/bash
set -u
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"

export PATH="$repo_root/jobs/tests/stubs:$PATH"

it "消费一个 chunk，把其中每个点都跑完"
tmp=$(mktemp -d)
wl="$tmp/worklist"
mkdir -p "$wl"
make_fixture "$tmp/work" DFT_0001 2.85 2.90
make_fixture "$tmp/work" DFT_0002 3.01
printf 'DFT_0001/DFT_0001_2.85.kgrn\nDFT_0001/DFT_0001_2.90.kgrn\nDFT_0002/DFT_0002_3.01.kgrn\n' \
    > "$wl/chunk_0001"

( cd "$tmp/work" && \
  SLURM_SUBMIT_DIR="$tmp/work" SLURM_ARRAY_TASK_ID=1 WORKLIST_DIR="$wl" \
  EMTO_NPROC=2 EMTO_SKIP_MODULES=1 EMTO_BIN="$repo_root/jobs/tests/stubs" \
  bash "$repo_root/jobs/job_array.sh" > "$tmp/array.log" 2>&1 )
assert_eq "0" "$?" "array 作业体退出码"

assert_file "$tmp/work/DFT_0001/kfcd/DFT_0001_2.85.prn" "第 1 个点完成"
assert_file "$tmp/work/DFT_0001/kfcd/DFT_0001_2.90.prn" "第 2 个点完成"
assert_file "$tmp/work/DFT_0002/kfcd/DFT_0002_3.01.prn" "第 3 个点完成"
assert_file "$wl/timing.log" "计时日志已写"
assert_eq "3" "$(wc -l < "$wl/timing.log")" "计时日志 3 行"

it "chunk 文件不存在时报错退出"
( cd "$tmp/work" && \
  SLURM_SUBMIT_DIR="$tmp/work" SLURM_ARRAY_TASK_ID=99 WORKLIST_DIR="$wl" \
  EMTO_SKIP_MODULES=1 bash "$repo_root/jobs/job_array.sh" > /dev/null 2>&1 )
assert_eq "1" "$?" "缺 chunk 应退出码 1"

it "run_one 的失败不会让整块中止"
tmp2=$(mktemp -d)
wl2="$tmp2/worklist"
mkdir -p "$wl2"
make_fixture "$tmp2/work" DFT_0007 2.80 2.84
printf 'DFT_0007/DFT_0007_2.80.kgrn\nDFT_0007/DFT_0007_2.84.kgrn\n' > "$wl2/chunk_0001"
( cd "$tmp2/work" && \
  SLURM_SUBMIT_DIR="$tmp2/work" SLURM_ARRAY_TASK_ID=1 WORKLIST_DIR="$wl2" \
  EMTO_NPROC=1 EMTO_SKIP_MODULES=1 STUB_KGRN_NOCONV=1 \
  bash "$repo_root/jobs/job_array.sh" > /dev/null 2>&1 )
assert_eq "2" "$(wc -l < "$wl2/timing.log")" "两个点都被尝试过"

it "module 加载失败时退出"
tmp3=$(mktemp -d)
wl3="$tmp3/worklist"
mkdir -p "$wl3"
make_fixture "$tmp3/work" DFT_0009 2.75
printf 'DFT_0009/DFT_0009_2.75.kgrn\n' > "$wl3/chunk_0001"
# 使用特殊环境绕过 Lmod，注入失败的假 module 命令
( cd "$tmp3/work" && \
  env -u BASH_ENV -u 'BASH_FUNC_module%%' -u 'BASH_FUNC__module_raw%%' \
  PATH="$repo_root/jobs/tests/stubs:$PATH" \
  SLURM_SUBMIT_DIR="$tmp3/work" SLURM_ARRAY_TASK_ID=1 WORKLIST_DIR="$wl3" \
  STUB_MODULE_FAIL=1 EMTO_NPROC=1 \
  bash "$repo_root/jobs/job_array.sh" > /dev/null 2>&1 )
assert_eq "1" "$?" "module 失败应退出码 1"
assert_no_file "$tmp3/work/DFT_0009/kfcd/DFT_0009_2.75.prn" "module 失败时不应执行计算"

rm -rf "$tmp" "$tmp2" "$tmp3"
summary
