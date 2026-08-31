#!/bin/bash
# helpers.sh 自身的冒烟测试
set -u
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"

it "assert_eq 相等时不计失败"
assert_eq "a" "a" "相同字符串"

it "make_fixture 生成 .kgrn 与 .kfcd"
tmp=$(mktemp -d)
make_fixture "$tmp" DFT_0001 2.85 2.90
assert_file "$tmp/DFT_0001/DFT_0001_2.85.kgrn" "第一个点的 kgrn"
assert_file "$tmp/DFT_0001/DFT_0001_2.90.kfcd" "第二个点的 kfcd"
assert_contains "$tmp/DFT_0001/DFT_0001_2.85.kgrn" "JOBNAM=DFT_0001_2.85" "jobname 写入"

it "桩程序 kgrn_cpa 写出 FINISHED 的 prn"
mkdir -p "$tmp/DFT_0001/kgrn/tmp"
( cd "$tmp/DFT_0001" && PATH="$repo_root/jobs/tests/stubs:$PATH" kgrn_cpa < DFT_0001_2.85.kgrn > /dev/null )
assert_contains "$tmp/DFT_0001/kgrn/DFT_0001_2.85.prn" "FINISHED" "kgrn prn 含 FINISHED"
assert_file "$tmp/DFT_0001/kgrn/DFT_0001_2.85.chd" "桩程序生成中间文件 .chd"

it "桩程序 STUB_KGRN_NOCONV=1 时 prn 不含 FINISHED"
( cd "$tmp/DFT_0001" && PATH="$repo_root/jobs/tests/stubs:$PATH" STUB_KGRN_NOCONV=1 kgrn_cpa < DFT_0001_2.90.kgrn > /dev/null )
assert_contains "$tmp/DFT_0001/kgrn/DFT_0001_2.90.prn" "NOT CONVERGED" "未收敛标记"

rm -rf "$tmp"
summary
