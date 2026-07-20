#!/bin/bash
set -u
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"

export PATH="$repo_root/jobs/tests/stubs:$PATH"

it "正常执行：输出落在合金目录的 kgrn/ 与 kfcd/ 下"
tmp=$(mktemp -d)
make_fixture "$tmp" DFT_0001 2.85
( cd "$tmp" && bash "$repo_root/jobs/run_one.sh" DFT_0001/DFT_0001_2.85.kgrn )
assert_eq "0" "$?" "退出码"
assert_file "$tmp/DFT_0001/kgrn/DFT_0001_2.85.prn" "kgrn prn 落在合金目录下"
assert_file "$tmp/DFT_0001/kfcd/DFT_0001_2.85.prn" "kfcd prn 落在合金目录下"
assert_contains "$tmp/DFT_0001/kfcd/DFT_0001_2.85.prn" "TOT-PBE" "kfcd 输出含总能"

it "不在仓库根留下 kgrn/ 目录（cd 生效）"
assert_no_file "$tmp/kgrn/DFT_0001_2.85.prn" "根目录不应有 prn"

it "幂等：已完成的点直接跳过，不重跑"
( cd "$tmp" && bash "$repo_root/jobs/run_one.sh" DFT_0001/DFT_0001_2.85.kgrn )
before=$(cat "$tmp/DFT_0001/kfcd/DFT_0001_2.85.prn")
# 让桩程序在重跑时必崩，若真的重跑了 prn 内容会变
( cd "$tmp" && STUB_KGRN_FAIL=1 bash "$repo_root/jobs/run_one.sh" DFT_0001/DFT_0001_2.85.kgrn )
assert_eq "0" "$?" "已完成点的退出码应为 0"
after=$(cat "$tmp/DFT_0001/kfcd/DFT_0001_2.85.prn")
assert_eq "$before" "$after" "kfcd prn 不应被改写"

it "EMTO_CLEANUP=1 时跑完清掉大中间文件，但保留 prn"
tmp2=$(mktemp -d)
make_fixture "$tmp2" DFT_0002 3.01
( cd "$tmp2" && EMTO_CLEANUP=1 bash "$repo_root/jobs/run_one.sh" DFT_0002/DFT_0002_3.01.kgrn )
assert_no_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.atm" ".atm 应被删除"
assert_no_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.chd" ".chd 应被删除"
assert_no_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.pot" ".pot 应被删除"
assert_no_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.zms" ".zms 应被删除"
assert_no_file "$tmp2/DFT_0002/kgrn/tmp/DFT_0002_3.01.tmp" "tmp 文件应被删除"
assert_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.prn" "kgrn prn 必须保留"

it "默认（不设 EMTO_CLEANUP）跑完保留中间文件"
tmp2b=$(mktemp -d)
make_fixture "$tmp2b" DFT_0002B 3.02
( cd "$tmp2b" && bash "$repo_root/jobs/run_one.sh" DFT_0002B/DFT_0002B_3.02.kgrn )
assert_file "$tmp2b/DFT_0002B/kgrn/DFT_0002B_3.02.atm" ".atm 应保留"
assert_file "$tmp2b/DFT_0002B/kgrn/DFT_0002B_3.02.chd" ".chd 应保留"
assert_file "$tmp2b/DFT_0002B/kgrn/DFT_0002B_3.02.pot" ".pot 应保留"
assert_file "$tmp2b/DFT_0002B/kgrn/DFT_0002B_3.02.zms" ".zms 应保留"
assert_file "$tmp2b/DFT_0002B/kgrn/tmp/DFT_0002B_3.02.tmp" "tmp 文件应保留"
assert_file "$tmp2b/DFT_0002B/kgrn/DFT_0002B_3.02.prn" "kgrn prn 必须保留"

it "KGRN 未收敛时不跑 KFCD，退出码非 0"
tmp3=$(mktemp -d)
make_fixture "$tmp3" DFT_0003 2.99
( cd "$tmp3" && STUB_KGRN_NOCONV=1 bash "$repo_root/jobs/run_one.sh" DFT_0003/DFT_0003_2.99.kgrn )
rc=$?
if [ "$rc" -eq 0 ]; then
    assert_eq "非0" "0" "未收敛应返回非 0"
else
    assert_eq "1" "1" "未收敛返回非 0"
fi
assert_no_file "$tmp3/DFT_0003/kfcd/DFT_0003_2.99.prn" "不应产生 kfcd prn"

it "KGRN 崩溃时透传退出码"
tmp4=$(mktemp -d)
make_fixture "$tmp4" DFT_0004 2.88
( cd "$tmp4" && STUB_KGRN_FAIL=1 bash "$repo_root/jobs/run_one.sh" DFT_0004/DFT_0004_2.88.kgrn )
assert_eq "3" "$?" "透传桩程序的退出码 3"

it "超时被 timeout 杀掉，退出码 124"
tmp5=$(mktemp -d)
make_fixture "$tmp5" DFT_0005 2.95
( cd "$tmp5" && EMTO_TIMEOUT=1 STUB_KGRN_SLEEP=5 bash "$repo_root/jobs/run_one.sh" DFT_0005/DFT_0005_2.95.kgrn )
assert_eq "124" "$?" "timeout 的退出码"

it "WORKLIST_DIR 非空时写 timing.log"
tmp6=$(mktemp -d)
wl=$(mktemp -d)
make_fixture "$tmp6" DFT_0006 3.10
( cd "$tmp6" && WORKLIST_DIR="$wl" bash "$repo_root/jobs/run_one.sh" DFT_0006/DFT_0006_3.10.kgrn )
assert_file "$wl/timing.log" "timing.log 存在"
assert_contains "$wl/timing.log" "DFT_0006_3.10" "记录了 jobname"
assert_eq "4" "$(awk '{print NF}' "$wl/timing.log" | head -1)" "每行 4 列"

it "KFCD 退出码 0 但 prn 未含 FINISHED 时应报非 0"
tmp7=$(mktemp -d)
make_fixture "$tmp7" DFT_0007 3.15
( cd "$tmp7" && STUB_KFCD_NOFINISH=1 bash "$repo_root/jobs/run_one.sh" DFT_0007/DFT_0007_3.15.kgrn )
rc=$?
if [ "$rc" -eq 0 ]; then
    assert_eq "非0" "0" "kfcd 未完成应返回非 0"
else
    assert_eq "1" "1" "kfcd 未完成返回非 0"
fi

rm -rf "$tmp" "$tmp2" "$tmp2b" "$tmp3" "$tmp4" "$tmp5" "$tmp6" "$tmp7" "$wl"
summary
