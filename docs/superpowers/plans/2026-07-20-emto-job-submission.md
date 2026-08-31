# EMTO 作业提交脚本 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为高通量 EMTO 流水线的三个 stage 提供一套幂等、满载、可断点续跑的 Slurm 作业提交脚本。

**Architecture:** 三层 shell 脚本。`submit_stage.sh` 扫描某个 stage 下所有未完成的 `.kgrn`，切成固定大小的 chunk 写进带时间戳的 worklist 目录，然后提交一个 Slurm array 作业；`job_array.sh` 是 array 作业体，每个 array task 独占一个 96 核节点，用 `xargs -P 96` 动态消费自己那块 chunk；`run_one.sh` 是最小执行单元，`cd` 进合金目录跑一个 KGRN+KFCD 点。幂等性完全由「扫描时跳过已 FINISHED 的点」实现，因此重复提交是安全操作。

**Tech Stack:** Bash 4（Slurm 集群自带）、Slurm job array、GNU `xargs` / `timeout`、Lmod。测试用纯 bash 断言脚本 + 假的 `kgrn_cpa`/`kfcd_cpa`/`sbatch` 桩程序（**本机没有 pytest 也没有 bats**，不引入新依赖）。

## Global Constraints

- 仓库根目录：`/work/scratch/md88vyxi/workplace/highthroughput-dft-rhea`
- 所有新脚本放在 `jobs/`，纯 bash，计算节点上不需要 Python
- **不得** `source ~/.emto.sh`：其 `decide_kgrn` 对本项目 jobname 解析错位，其 `checkemto` 用全局 `pgrep kill` 会误杀同用户其它作业
- **不得**使用 pyemto 生成的 `stageN_*/DFT_XXXX/*.sh`：内含不存在的二进制路径 `/home/hpleva/EMTO5.8/...`
- module 加载**必须**按此顺序（`intel-oneapi-mkl` 挂在 openmpi 层级下）：
  `module load openmpi/4.1.8-6xzv intel-oneapi-compilers/2025.3.1-pbro intel-oneapi-mkl/2025.3.1-iqtm`
- EMTO 二进制目录：`$HOME/intel-mkl-omp-build-2021-Mar/bin`（含 `kgrn_cpa`、`kfcd_cpa`）
- Slurm 账户 `-A p0020465`，节点约束 `-C avx512`，`--mem-per-cpu=3800`，每节点 96 核
- Stage 目录名：`stage1_eos_coarse`、`stage2_eos_fine`、`stage3_elastic`（与 `config.py` 的 `STAGE_DIRS` 一致）
- **完成判据**（全脚本统一）：合金目录下 `kfcd/<job>.prn` 存在且内容含 `FINISHED`（大小写不敏感）
- 参数默认值：`--chunk 1000`、`--maxpar 8`、`--time 24:00:00`、`--partition deflt`、`EMTO_TIMEOUT=7200`
- 所有测试用 `bash jobs/tests/run_all.sh` 运行，必须在登录节点上无 Slurm、无 EMTO 二进制的情况下通过

---

## File Structure

| 文件 | 职责 |
| --- | --- |
| `jobs/run_one.sh` | 跑一个 `.kgrn` 点：幂等跳过、超时保护、清中间文件、记录耗时 |
| `jobs/job_array.sh` | Slurm array 作业体：加载 module，`xargs -P 96` 消费一个 chunk |
| `jobs/submit_stage.sh` | 扫描未完成任务 → 切块写 worklist → `sbatch` |
| `jobs/tests/helpers.sh` | 断言函数与 fixture 构造器 |
| `jobs/tests/stubs/kgrn_cpa` | 假 KGRN：按环境变量模拟成功/不收敛/崩溃/挂起 |
| `jobs/tests/stubs/kfcd_cpa` | 假 KFCD |
| `jobs/tests/stubs/sbatch` | 假 sbatch：把收到的参数写进 `$SBATCH_CAPTURE` |
| `jobs/tests/test_run_one.sh` | `run_one.sh` 的测试 |
| `jobs/tests/test_job_array.sh` | `job_array.sh` 的测试 |
| `jobs/tests/test_submit_stage.sh` | `submit_stage.sh` 的测试 |
| `jobs/tests/run_all.sh` | 跑全部测试并汇总 |
| `README.md` | 增加「集群提交」一节 |
| `.gitignore` | 忽略 `jobs/worklists/` |

---

### Task 1: 测试骨架与桩程序

先建测试基础设施，后续三个任务都靠它做 TDD。

**Files:**
- Create: `jobs/tests/helpers.sh`
- Create: `jobs/tests/stubs/kgrn_cpa`
- Create: `jobs/tests/stubs/kfcd_cpa`
- Create: `jobs/tests/run_all.sh`
- Test: `jobs/tests/test_helpers.sh`

**Interfaces:**
- Consumes: 无
- Produces:
  - `helpers.sh` 导出函数：`it <描述>`、`assert_eq <期望> <实际> <消息>`、`assert_file <路径> <消息>`、`assert_no_file <路径> <消息>`、`assert_contains <文件> <模式> <消息>`、`summary`（全部通过返回 0）、`make_fixture <根目录> <合金ID> <sws...>`、`repo_root`（变量，仓库绝对路径）
  - 桩程序读 stdin 中的 `JOBNAM=<job>` 行决定输出文件名；行为由环境变量控制：`STUB_KGRN_NOCONV=1`（写不含 FINISHED 的 prn 后正常退出）、`STUB_KGRN_FAIL=1`（退出码 3）、`STUB_KGRN_SLEEP=<秒>`（先睡再成功）、`STUB_KFCD_FAIL=1`

- [ ] **Step 1: 写 helpers.sh 的测试**

创建 `jobs/tests/test_helpers.sh`：

```bash
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `bash jobs/tests/test_helpers.sh`
Expected: FAIL —— `helpers.sh: No such file or directory`

- [ ] **Step 3: 实现 helpers.sh**

创建 `jobs/tests/helpers.sh`：

```bash
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
```

- [ ] **Step 4: 实现 kgrn_cpa 桩程序**

创建 `jobs/tests/stubs/kgrn_cpa`：

```bash
#!/bin/bash
# 假 KGRN。从 stdin 读 JOBNAM= 决定输出文件名，行为由环境变量控制。
set -u
input=$(cat)
job=$(printf '%s\n' "$input" | sed -n 's/^JOBNAM=//p' | head -1)
mkdir -p kgrn/tmp

if [ "${STUB_KGRN_FAIL:-0}" = "1" ]; then
    echo "KGRN crashed" > "kgrn/$job.prn"
    exit 3
fi

if [ -n "${STUB_KGRN_SLEEP:-}" ]; then
    sleep "$STUB_KGRN_SLEEP"
fi

if [ "${STUB_KGRN_NOCONV:-0}" = "1" ]; then
    echo "KGRN NOT CONVERGED" > "kgrn/$job.prn"
    exit 0
fi

echo "KGRN FINISHED for $job" > "kgrn/$job.prn"
touch "kgrn/$job.atm" "kgrn/$job.chd" "kgrn/$job.pot" "kgrn/$job.zms" "kgrn/tmp/$job.tmp"
echo "stdout from kgrn_cpa"
```

创建 `jobs/tests/stubs/kfcd_cpa`：

```bash
#!/bin/bash
# 假 KFCD。
set -u
input=$(cat)
job=$(printf '%s\n' "$input" | sed -n 's/^JOBNAM=//p' | head -1)
mkdir -p kfcd

if [ "${STUB_KFCD_FAIL:-0}" = "1" ]; then
    echo "KFCD crashed" > "kfcd/$job.prn"
    exit 4
fi

if [ -n "${STUB_KFCD_SLEEP:-}" ]; then
    sleep "$STUB_KFCD_SLEEP"
fi

printf 'KFCD FINISHED for %s\nTOT-PBE   -1234.567890\n' "$job" > "kfcd/$job.prn"
echo "stdout from kfcd_cpa"
```

两个桩程序都要可执行：`chmod +x jobs/tests/stubs/kgrn_cpa jobs/tests/stubs/kfcd_cpa`

- [ ] **Step 5: 实现 run_all.sh**

创建 `jobs/tests/run_all.sh`：

```bash
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
```

- [ ] **Step 6: 运行测试确认通过**

Run: `bash jobs/tests/test_helpers.sh`
Expected: 输出 4 个 `- <描述>` 行，末尾 `---- <N> 项断言，0 项失败`，退出码 0

Run: `bash jobs/tests/run_all.sh`
Expected: `全部测试通过`，退出码 0

- [ ] **Step 7: 提交**

```bash
chmod +x jobs/tests/stubs/kgrn_cpa jobs/tests/stubs/kfcd_cpa
git add jobs/tests/
git commit -m "test: add bash test harness and fake EMTO binaries"
```

---

### Task 2: `run_one.sh` 的正常执行路径

**Files:**
- Create: `jobs/run_one.sh`
- Test: `jobs/tests/test_run_one.sh`

**Interfaces:**
- Consumes: `jobs/tests/helpers.sh` 的 `it` / `assert_*` / `summary` / `make_fixture` / `repo_root`；`jobs/tests/stubs/` 下的 `kgrn_cpa`、`kfcd_cpa`
- Produces: `jobs/run_one.sh <相对仓库根的 .kgrn 路径>`，退出码 0 = 成功或已完成，非 0 = 该点失败。读环境变量 `EMTO_TIMEOUT`（秒，默认 7200）、`WORKLIST_DIR`（绝对路径，非空时向 `$WORKLIST_DIR/timing.log` 追加计时行）

- [ ] **Step 1: 写失败的测试**

创建 `jobs/tests/test_run_one.sh`：

```bash
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `bash jobs/tests/test_run_one.sh`
Expected: FAIL —— `run_one.sh: No such file or directory`，断言报「文件不存在」

- [ ] **Step 3: 实现 run_one.sh 的最小版本**

创建 `jobs/run_one.sh`：

```bash
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `bash jobs/tests/test_run_one.sh`
Expected: 末尾 `0 项失败`，退出码 0

- [ ] **Step 5: 提交**

```bash
chmod +x jobs/run_one.sh
git add jobs/run_one.sh jobs/tests/test_run_one.sh
git commit -m "feat: add run_one.sh to run a single EMTO point in its alloy dir"
```

---

### Task 3: `run_one.sh` 的幂等、失败处理、超时、清理与计时

**Files:**
- Modify: `jobs/run_one.sh`
- Modify: `jobs/tests/test_run_one.sh`

**Interfaces:**
- Consumes: Task 2 的 `jobs/run_one.sh`
- Produces: 同 Task 2 的接口，另外保证：已完成的点秒退且不重跑；KGRN 未收敛时不跑 KFCD；超时退出码 124；跑完删除 `kgrn/<job>.{atm,chd,pot,zms}` 与 `kgrn/tmp/<job>*`；`WORKLIST_DIR` 非空时向 `$WORKLIST_DIR/timing.log` 追加一行 `<job> <kgrn秒> <kfcd秒> <退出码>`

- [ ] **Step 1: 追加失败的测试**

把下面的内容插到 `jobs/tests/test_run_one.sh` 的 `rm -rf "$tmp"` 之前（即最后一个 `it` 块之后、清理之前）：

```bash
it "幂等：已完成的点直接跳过，不重跑"
( cd "$tmp" && bash "$repo_root/jobs/run_one.sh" DFT_0001/DFT_0001_2.85.kgrn )
before=$(cat "$tmp/DFT_0001/kfcd/DFT_0001_2.85.prn")
# 让桩程序在重跑时必崩，若真的重跑了 prn 内容会变
( cd "$tmp" && STUB_KGRN_FAIL=1 bash "$repo_root/jobs/run_one.sh" DFT_0001/DFT_0001_2.85.kgrn )
assert_eq "0" "$?" "已完成点的退出码应为 0"
after=$(cat "$tmp/DFT_0001/kfcd/DFT_0001_2.85.prn")
assert_eq "$before" "$after" "kfcd prn 不应被改写"

it "跑完清掉大中间文件，但保留 prn"
tmp2=$(mktemp -d)
make_fixture "$tmp2" DFT_0002 3.01
( cd "$tmp2" && bash "$repo_root/jobs/run_one.sh" DFT_0002/DFT_0002_3.01.kgrn )
assert_no_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.chd" ".chd 应被删除"
assert_no_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.pot" ".pot 应被删除"
assert_no_file "$tmp2/DFT_0002/kgrn/tmp/DFT_0002_3.01.tmp" "tmp 文件应被删除"
assert_file "$tmp2/DFT_0002/kgrn/DFT_0002_3.01.prn" "kgrn prn 必须保留"

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

rm -rf "$tmp2" "$tmp3" "$tmp4" "$tmp5" "$tmp6" "$wl"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `bash jobs/tests/test_run_one.sh`
Expected: FAIL —— 幂等、清理、超时、timing.log 相关断言全部报错（当前实现只是无脑跑两个二进制）

- [ ] **Step 3: 完整实现 run_one.sh**

用下面内容**整体替换** `jobs/run_one.sh`：

```bash
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

# 删掉大中间文件，保留 .prn 供分析阶段解析。
# 安全性：已完成的点下次直接跳过，未完成的点本来就要从头重算，
# 不存在从已有势函数热启动的需求。
cleanup() {
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

log_timing "$t_kgrn" "$t_kfcd" "$rc"
cleanup
exit "$rc"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `bash jobs/tests/test_run_one.sh`
Expected: 末尾 `0 项失败`，退出码 0

注：超时那条测试会真实等待约 1 秒。

- [ ] **Step 5: 提交**

```bash
git add jobs/run_one.sh jobs/tests/test_run_one.sh
git commit -m "feat: make run_one.sh idempotent with timeout, cleanup and timing"
```

---

### Task 4: `job_array.sh`

**Files:**
- Create: `jobs/job_array.sh`
- Test: `jobs/tests/test_job_array.sh`

**Interfaces:**
- Consumes: `jobs/run_one.sh`
- Produces: `jobs/job_array.sh`，作为 `sbatch` 的作业体。从环境变量读 `WORKLIST_DIR`（绝对路径）与 `SLURM_ARRAY_TASK_ID`，处理 `$WORKLIST_DIR/chunk_$(printf %04d $SLURM_ARRAY_TASK_ID)`。可用 `EMTO_NPROC` 覆盖并发数（默认 96），`EMTO_BIN` 覆盖二进制目录（默认 `$HOME/intel-mkl-omp-build-2021-Mar/bin`），`EMTO_SKIP_MODULES=1` 跳过 module 加载（测试用）

- [ ] **Step 1: 写失败的测试**

创建 `jobs/tests/test_job_array.sh`：

```bash
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

rm -rf "$tmp" "$tmp2"
summary
```

- [ ] **Step 2: 运行测试确认失败**

Run: `bash jobs/tests/test_job_array.sh`
Expected: FAIL —— `job_array.sh: No such file or directory`

- [ ] **Step 3: 实现 job_array.sh**

创建 `jobs/job_array.sh`：

```bash
#!/bin/bash
#SBATCH -N 1
#SBATCH -n 96
#SBATCH -c 1
#SBATCH -A p0020465
#SBATCH -C avx512
#SBATCH --mem-per-cpu=3800
#SBATCH --mail-type=NONE
#SBATCH --export=ALL
#
# Slurm array 作业体：一个 array task 独占一个 96 核节点，用 xargs -P 96
# 动态消费自己那块 chunk。-t / --array / -p / -J 由 submit_stage.sh 在命令行
# 指定，不写死在这里。
#
# 环境变量:
#   WORKLIST_DIR        worklist 目录绝对路径（由 submit_stage.sh 通过 --export 传入）
#   EMTO_NPROC          并发数，默认 96
#   EMTO_BIN            EMTO 二进制目录，默认 $HOME/intel-mkl-omp-build-2021-Mar/bin
#   EMTO_SKIP_MODULES   置 1 跳过 module 加载（测试用）
set -u

if [ "${EMTO_SKIP_MODULES:-0}" != "1" ]; then
    # sbatch 用非登录 shell 执行本脚本，/etc/profile.d 不会被自动 source。
    # module 函数与 MODULEPATH 通常靠 --export=ALL 继承，但这里显式兜底。
    if ! command -v module > /dev/null 2>&1; then
        # shellcheck source=/dev/null
        [ -f /etc/profile.d/new_modules.sh ] && . /etc/profile.d/new_modules.sh
        # shellcheck source=/dev/null
        [ -f /etc/profile.d/tuda.sh ] && . /etc/profile.d/tuda.sh
    fi
    module purge
    # 注意顺序：intel-oneapi-mkl 挂在 openmpi 层级下，必须先 load openmpi
    module load openmpi/4.1.8-6xzv intel-oneapi-compilers/2025.3.1-pbro intel-oneapi-mkl/2025.3.1-iqtm
fi

export PATH="${EMTO_BIN:-$HOME/intel-mkl-omp-build-2021-Mar/bin}:$PATH"
export OMP_NUM_THREADS=1
export OMP_STACKSIZE=800m
ulimit -s unlimited

# run_one.sh 的绝对路径必须在 cd 之前算出来
script_dir=$(cd "$(dirname "$0")" && pwd)

cd "${SLURM_SUBMIT_DIR:-$PWD}" || exit 1

chunk="$WORKLIST_DIR/chunk_$(printf '%04d' "${SLURM_ARRAY_TASK_ID:-1}")"
if [ ! -f "$chunk" ]; then
    echo "错误：找不到 chunk 文件 $chunk" >&2
    exit 1
fi

ntasks=$(wc -l < "$chunk")
echo "[$(date '+%F %T')] 开始 $chunk（$ntasks 个任务，并发 ${EMTO_NPROC:-96}）"

# xargs -P 是动态取任务：worker 跑完一个立刻领下一个，天然负载均衡。
# run_one.sh 单点失败不影响其它任务，失败信息留在 .prn 里由分析阶段收集。
xargs -a "$chunk" -n 1 -P "${EMTO_NPROC:-96}" -I{} bash "$script_dir/run_one.sh" {}

echo "[$(date '+%F %T')] 完成 $chunk"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `bash jobs/tests/test_job_array.sh`
Expected: 末尾 `0 项失败`，退出码 0

- [ ] **Step 5: 提交**

```bash
chmod +x jobs/job_array.sh
git add jobs/job_array.sh jobs/tests/test_job_array.sh
git commit -m "feat: add job_array.sh consuming one worklist chunk per node"
```

---

### Task 5: `submit_stage.sh` 的扫描、切块与 `--dry-run`

**Files:**
- Create: `jobs/submit_stage.sh`
- Create: `jobs/tests/stubs/sbatch`
- Test: `jobs/tests/test_submit_stage.sh`

**Interfaces:**
- Consumes: `jobs/job_array.sh`
- Produces: `jobs/submit_stage.sh <1|2|3> [--chunk N] [--maxpar N] [--time HH:MM:SS] [--partition P] [--limit N] [--dry-run]`。`--dry-run` 只打印统计与将要执行的 sbatch 命令、不落盘不提交；正常执行时把 worklist 写进 `jobs/worklists/stage<N>_<YYYYmmdd-HHMMSS>/chunk_XXXX` 并调用 `${SUBMIT_CMD:-sbatch}`。桩程序 `jobs/tests/stubs/sbatch` 把收到的全部参数写进 `$SBATCH_CAPTURE` 指向的文件

- [ ] **Step 1: 写失败的测试**

创建 `jobs/tests/stubs/sbatch`：

```bash
#!/bin/bash
# 假 sbatch：把收到的参数逐行写进 $SBATCH_CAPTURE，然后打印一个假 jobid。
if [ -n "${SBATCH_CAPTURE:-}" ]; then
    printf '%s\n' "$@" > "$SBATCH_CAPTURE"
fi
echo "Submitted batch job 999999"
```

创建 `jobs/tests/test_submit_stage.sh`：

```bash
#!/bin/bash
set -u
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"

export PATH="$repo_root/jobs/tests/stubs:$PATH"

# 造一个假仓库：jobs/ 用符号链接指回真仓库，stage 目录用 fixture
setup_fakerepo() {
    local root=$1
    mkdir -p "$root"
    ln -s "$repo_root/jobs" "$root/jobs"
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
mkdir -p "$tmp5"
ln -s "$repo_root/jobs" "$tmp5/jobs"
( cd "$tmp5" && REPO_ROOT="$tmp5" bash jobs/submit_stage.sh 1 > /dev/null 2>&1 )
assert_eq "1" "$?" "缺 stage 目录应退出 1"

it "stage 参数非法时退出 2"
( cd "$tmp" && REPO_ROOT="$tmp" bash jobs/submit_stage.sh 9 > /dev/null 2>&1 )
assert_eq "2" "$?" "非法 stage 退出 2"

rm -rf "$tmp" "$tmp2" "$tmp3" "$tmp4" "$tmp5"
summary
```

- [ ] **Step 2: 运行测试确认失败**

Run: `bash jobs/tests/test_submit_stage.sh`
Expected: FAIL —— `submit_stage.sh: No such file or directory`

- [ ] **Step 3: 实现 submit_stage.sh**

创建 `jobs/submit_stage.sh`：

```bash
#!/bin/bash
# 扫描某个 stage 下所有未完成的 EMTO 任务，切块写 worklist，提交 Slurm array 作业。
#
# 用法: jobs/submit_stage.sh <1|2|3> [选项]
#   --chunk N        每块任务数（默认 1000）
#   --maxpar N       同时运行的 array task 上限（默认 8）
#   --time HH:MM:SS  单个 array task 时限（默认 24:00:00）
#   --partition P    分区（默认 deflt）
#   --limit N        只取 worklist 前 N 个任务（冒烟测试用）
#   --dry-run        只打印统计与 sbatch 命令，不落盘不提交
#
# 重跑就是再执行一次本脚本：扫描天然跳过已完成的点，
# 断点续跑 / 超时补算 / --retry 后的补算都不需要手工挑合金。
set -u

usage() {
    sed -n '2,15p' "$0"
}

stage=${1:-}
case "$stage" in
    1|2|3) shift ;;
    *) echo "错误：stage 必须是 1、2 或 3" >&2; usage; exit 2 ;;
esac

CHUNK=1000
MAXPAR=8
TIME=24:00:00
PARTITION=deflt
LIMIT=0
DRYRUN=0

while [ $# -gt 0 ]; do
    case "$1" in
        --chunk)     CHUNK=$2; shift 2 ;;
        --maxpar)    MAXPAR=$2; shift 2 ;;
        --time)      TIME=$2; shift 2 ;;
        --partition|-p) PARTITION=$2; shift 2 ;;
        --limit)     LIMIT=$2; shift 2 ;;
        --dry-run)   DRYRUN=1; shift ;;
        -h|--help)   usage; exit 0 ;;
        *) echo "错误：未知选项 $1" >&2; usage; exit 2 ;;
    esac
done

# REPO_ROOT 可覆盖，测试用假仓库时需要（jobs/ 是指回真仓库的符号链接）
repo_root=${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
cd "$repo_root" || exit 1

case "$stage" in
    1) stage_dir=stage1_eos_coarse ;;
    2) stage_dir=stage2_eos_fine ;;
    3) stage_dir=stage3_elastic ;;
esac

if [ ! -d "$stage_dir" ]; then
    echo "错误：找不到 $stage_dir，请先运行 python run_pipeline.py --stage $stage --generate" >&2
    exit 1
fi

# 扫描：完成判据是 kfcd/<job>.prn 存在且含 FINISHED
pending=()
while IFS= read -r kgrn_file; do
    d=$(dirname "$kgrn_file")
    j=$(basename "$kgrn_file" .kgrn)
    if [ -f "$d/kfcd/$j.prn" ] && grep -qi finished "$d/kfcd/$j.prn"; then
        continue
    fi
    pending+=("$kgrn_file")
done < <(find "$stage_dir" -mindepth 2 -maxdepth 2 -name '*.kgrn' | sort)

total=${#pending[@]}
if [ "$total" -eq 0 ]; then
    echo "无未完成任务：$stage_dir 下所有点都已完成。"
    exit 0
fi

if [ "$LIMIT" -gt 0 ] && [ "$LIMIT" -lt "$total" ]; then
    pending=("${pending[@]:0:$LIMIT}")
    total=$LIMIT
fi

nchunks=$(( (total + CHUNK - 1) / CHUNK ))
ts=$(date +%Y%m%d-%H%M%S)
worklist_dir="$repo_root/jobs/worklists/stage${stage}_${ts}"

echo "stage:     $stage ($stage_dir)"
echo "任务数:    $total"
echo "块数:      $nchunks（每块 $CHUNK）"
echo "并发上限:  $MAXPAR 个节点"

submit_cmd=${SUBMIT_CMD:-sbatch}
sbatch_args=(
    "--array=1-${nchunks}%${MAXPAR}"
    "-t" "$TIME"
    "-p" "$PARTITION"
    "-J" "emto_s${stage}"
    "--export=ALL,WORKLIST_DIR=${worklist_dir}"
    "-o" "${worklist_dir}/slurm-%A_%a.out"
    "$repo_root/jobs/job_array.sh"
)

if [ "$DRYRUN" -eq 1 ]; then
    echo "dry-run: 不写 worklist，不提交"
    echo "将执行: $submit_cmd ${sbatch_args[*]}"
    exit 0
fi

mkdir -p "$worklist_dir"
i=0
c=1
for f in "${pending[@]}"; do
    printf '%s\n' "$f" >> "$worklist_dir/$(printf 'chunk_%04d' "$c")"
    i=$((i + 1))
    if [ $((i % CHUNK)) -eq 0 ]; then
        c=$((c + 1))
    fi
done

echo "worklist: $worklist_dir"
"$submit_cmd" "${sbatch_args[@]}"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `bash jobs/tests/test_submit_stage.sh`
Expected: 末尾 `0 项失败`，退出码 0

- [ ] **Step 5: 提交**

```bash
chmod +x jobs/submit_stage.sh jobs/tests/stubs/sbatch
git add jobs/submit_stage.sh jobs/tests/stubs/sbatch jobs/tests/test_submit_stage.sh
git commit -m "feat: add submit_stage.sh scanning pending jobs into worklist chunks"
```

---

### Task 6: `submit_stage.sh` 传给 sbatch 的参数

上一个任务用 `SUBMIT_CMD=true` 忽略了 sbatch 参数。这里断言参数确实正确。

**Files:**
- Modify: `jobs/tests/test_submit_stage.sh`

**Interfaces:**
- Consumes: Task 5 的 `jobs/submit_stage.sh` 与 `jobs/tests/stubs/sbatch`
- Produces: 无新接口，仅补测试

- [ ] **Step 1: 追加失败的测试**

把下面内容插到 `jobs/tests/test_submit_stage.sh` 的 `rm -rf "$tmp" ...` 之前：

```bash
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
assert_eq "1" "$(grep -c 'WORKLIST_DIR=' "$cap")" "导出 WORKLIST_DIR"
assert_eq "1" "$(grep -c 'jobs/job_array.sh' "$cap")" "作业体路径"
assert_eq "1" "$(printf '%s\n' "$out" | grep -c 'Submitted batch job')" "透传 sbatch 输出"

it "默认值：chunk=1000 maxpar=8 time=24:00:00 partition=deflt"
tmp7=$(mktemp -d)
setup_fakerepo "$tmp7"
make_fixture "$tmp7/stage1_eos_coarse" DFT_0001 2.85
cap2="$tmp7/sbatch_args.txt"
( cd "$tmp7" && REPO_ROOT="$tmp7" SBATCH_CAPTURE="$cap2" bash jobs/submit_stage.sh 1 > /dev/null 2>&1 )
assert_eq "1" "$(grep -cx -- '--array=1-1%8' "$cap2")" "默认 maxpar=8，1 个任务 1 块"
assert_eq "1" "$(grep -cx '24:00:00' "$cap2")" "默认时限"
assert_eq "1" "$(grep -cx 'deflt' "$cap2")" "默认分区"

rm -rf "$tmp6" "$tmp7"
```

用 `grep -cx` 精确匹配整行（假 sbatch 把每个参数单独写一行），比子串匹配更严格。
`--array=...` 以 `-` 开头，故 `grep` 需要 `--` 分隔符。

- [ ] **Step 2: 运行测试**

Run: `bash jobs/tests/test_submit_stage.sh`
Expected: 若 Task 5 的参数拼装正确，这些断言应**直接通过**（`0 项失败`）。任何一条
失败都说明 `submit_stage.sh` 的 `sbatch_args` 数组有误，回到 Task 5 的实现修正后
重跑本测试。

- [ ] **Step 3: 运行全部测试**

Run: `bash jobs/tests/run_all.sh`
Expected: `全部测试通过`，退出码 0

- [ ] **Step 4: 提交**

```bash
git add jobs/tests/test_submit_stage.sh
git commit -m "test: assert sbatch argument construction in submit_stage.sh"
```

---

### Task 7: 文档与 `.gitignore`

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Consumes: 前六个任务的全部脚本
- Produces: 无代码接口

- [ ] **Step 1: 忽略 worklist 目录**

在 `.gitignore` 的 `results/` 一行之后插入：

```
jobs/worklists/
```

- [ ] **Step 2: 验证 worklist 不再被跟踪**

Run: `bash jobs/tests/run_all.sh > /dev/null 2>&1; git status --short | grep -c worklists`
Expected: `0`

- [ ] **Step 3: 在 README 增加「集群提交」一节**

在 README 的「## 输出文件」一节**之前**插入：

````markdown
## 集群提交（Slurm）

每个 stage 生成输入后，用 `jobs/submit_stage.sh` 提交到 Lichtenberg：

```bash
# 冒烟测试：前 96 个任务铺满一个节点，拿到耗时分布
jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00

# 校准参数后全量提交
jobs/submit_stage.sh 1
```

| 选项 | 默认 | 说明 |
| --- | --- | --- |
| `--chunk N` | 1000 | 每块任务数；一块由一个 96 核节点消费 |
| `--maxpar N` | 8 | 同时运行的 array task（节点）上限 |
| `--time HH:MM:SS` | 24:00:00 | 单个 array task 时限 |
| `--partition P` | `deflt` | 分区 |
| `--limit N` | 全部 | 只取前 N 个未完成任务 |
| `--dry-run` | | 只打印统计与 sbatch 命令，不提交 |

脚本会扫描 `stageN_*/DFT_XXXX/*.kgrn`，**跳过 `kfcd/<job>.prn` 已含 `FINISHED`
的点**，把剩下的切块写进 `jobs/worklists/stageN_<时间戳>/`，再提交一个 Slurm
array 作业。因此**重跑就是再执行一次同一条命令** —— 断点续跑、超时点补算、
`--retry` 重生成后的补算都不需要手工挑合金。

三个脚本的分工：

| 脚本 | 职责 |
| --- | --- |
| `jobs/submit_stage.sh` | 扫描未完成 → 切块 → `sbatch` |
| `jobs/job_array.sh` | array 作业体：加载 module，`xargs -P 96` 消费一块 |
| `jobs/run_one.sh` | 跑一个点：`cd` 进合金目录、幂等跳过、`timeout` 保护、清中间文件、记录耗时 |

每个点的墙钟时间记录在 `jobs/worklists/<本次>/timing.log`，格式
`<jobname> <kgrn秒> <kfcd秒> <退出码>`，用来校准 `--chunk` 与 `EMTO_TIMEOUT`：

- `--chunk` ≈ 96 × 目标块时长(3~4 h) / 平均单点耗时
- `EMTO_TIMEOUT` ≈ 最慢点耗时的 3~4 倍（默认 7200 秒）

完整流程：

```bash
python run_pipeline.py --stage 1 --generate
jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00   # 冒烟
jobs/submit_stage.sh 1                                         # 全量
python run_pipeline.py --stage 1 --analyze
python run_pipeline.py --stage 1 --retry
jobs/submit_stage.sh 1                                         # 补算
python run_pipeline.py --stage 1 --analyze
```

Stage 2、3 同构。

### 测试

提交脚本自带一套纯 bash 测试（不依赖 Slurm、EMTO 二进制、pytest 或 bats）：

```bash
bash jobs/tests/run_all.sh
```
````

- [ ] **Step 4: 更新 README 的模块结构表**

在 README「## 模块结构」的表格末尾追加三行：

```markdown
| `jobs/submit_stage.sh` | 扫描未完成任务、切块、提交 Slurm array 作业 |
| `jobs/job_array.sh` | array 作业体，每节点 `xargs -P 96` 消费一块 worklist |
| `jobs/run_one.sh` | 单点执行器：幂等、超时保护、清中间文件、计时 |
```

- [ ] **Step 5: 确认全部测试仍通过**

Run: `bash jobs/tests/run_all.sh`
Expected: `全部测试通过`，退出码 0

- [ ] **Step 6: 提交**

```bash
git add .gitignore README.md
git commit -m "docs: document cluster submission workflow"
```

---

## 冒烟测试（脚本写完后，在真实集群上执行）

这一步不是自动化测试，需要人工观察结果。

- [ ] **Step 1: 先 dry-run 确认规模**

Run: `jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00 --dry-run`
Expected: 打印 `任务数: 96`、`块数: 1（每块 96）`，以及完整的 sbatch 命令行

- [ ] **Step 2: 真实提交**

Run: `jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00`
Expected: 打印 worklist 路径与 `Submitted batch job <id>`

- [ ] **Step 3: 等待完成并检查 7 项**

```bash
squeue -u $USER
```

作业结束后依次确认：

1. module 环境正常：`jobs/worklists/stage1_*/slurm-*.out` 里没有 `module: command not found` 或 `error while loading shared libraries`
2. 输出落位正确：`ls stage1_eos_coarse/DFT_0001/kgrn/` 有 `.prn`，且**仓库根目录没有** `kgrn/` 目录
3. 结构文件可读：`.prn` 里没有 `FOR001` 相关的 I/O 报错
4. 耗时分布：
   ```bash
   awk '{print $2+$3}' jobs/worklists/stage1_*/timing.log | sort -n | \
     awk '{a[NR]=$1} END{printf "n=%d 均值=%.0fs 中位=%ds 最慢=%ds\n", NR, (NR?s/NR:0), a[int(NR/2)+1], a[NR]} {s+=$1}'
   ```
5. 满载表现：`sacct -j <jobid> --format=JobID,Elapsed,MaxRSS,State` 看 MaxRSS 是否远低于 3800 MB×96
6. 幂等：再跑一次 `jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00 --dry-run`，应报「无未完成任务」或任务数显著减少
7. 分析可消费：`python run_pipeline.py --stage 1 --analyze`，`results/stage1_coarse_results.csv` 里出现 DFT_0001~DFT_0016 的 SWS0/B0

- [ ] **Step 4: 按实测校准参数**

用第 3 步第 4 项的均值与最慢值代入：

- `--chunk` = 96 × 12600 秒(3.5 h) / 平均单点秒数
- `EMTO_TIMEOUT` = 最慢点秒数 × 4

把算得的值写进 README 的默认值说明，并提交。
