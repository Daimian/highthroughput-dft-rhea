# shellcheck shell=bash
# 极简 bash 测试断言库。本机没有 pytest / bats，故自带。

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export repo_root

_T_CHECKS=0
_T_FAILED=0
_T_NAME=""

it() {
    _T_NAME="$1"
    echo "- $_T_NAME"
}

_t_fail() {
    _T_FAILED=$((_T_FAILED + 1))
    echo "    FAIL [$_T_NAME] $*" >&2
}

assert_eq() {
    _T_CHECKS=$((_T_CHECKS + 1))
    if [ "$1" != "$2" ]; then
        _t_fail "$3: 期望 '$1'，实际 '$2'"
        return 1
    fi
}

assert_file() {
    _T_CHECKS=$((_T_CHECKS + 1))
    if [ ! -f "$1" ]; then
        _t_fail "$2: 文件不存在 $1"
        return 1
    fi
}

assert_no_file() {
    _T_CHECKS=$((_T_CHECKS + 1))
    if [ -e "$1" ]; then
        _t_fail "$2: 文件本应被删除但仍存在 $1"
        return 1
    fi
}

assert_contains() {
    _T_CHECKS=$((_T_CHECKS + 1))
    if ! grep -qi -- "$2" "$1" 2>/dev/null; then
        _t_fail "$3: $1 中找不到 '$2'"
        return 1
    fi
}

summary() {
    echo "---- $_T_CHECKS 项断言，$_T_FAILED 项失败"
    [ "$_T_FAILED" -eq 0 ]
}

# make_fixture <根目录> <合金ID> <sws...>
# 生成 <根目录>/<合金ID>/<合金ID>_<sws>.{kgrn,kfcd}
make_fixture() {
    local root=$1 alloy=$2
    shift 2
    local sws job
    mkdir -p "$root/$alloy"
    for sws in "$@"; do
        job="${alloy}_${sws}"
        printf 'KGRN\nJOBNAM=%s\n' "$job" > "$root/$alloy/$job.kgrn"
        printf 'KFCD\nJOBNAM=%s\n' "$job" > "$root/$alloy/$job.kfcd"
    done
}
