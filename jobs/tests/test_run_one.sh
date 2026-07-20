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

rm -rf "$tmp"
summary
