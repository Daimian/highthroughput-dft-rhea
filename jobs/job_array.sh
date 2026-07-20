#!/bin/bash
#SBATCH -N 1
#SBATCH -n 96
#SBATCH -c 1
#SBATCH -C avx512
#SBATCH --mem-per-cpu=3800
#SBATCH --mail-type=NONE
#SBATCH --export=ALL
#
# Slurm array 作业体：一个 array task 独占一个 96 核节点，用 xargs -P 96
# 动态消费自己那块 chunk。-t / --array / -p / -J / -A 由 submit_stage.sh 在
# 命令行指定，不写死在这里。
#
# 环境变量:
#   WORKLIST_DIR        worklist 目录绝对路径（由 submit_stage.sh 通过 --export 传入）
#   EMTO_REPO_ROOT       仓库根绝对路径（由 submit_stage.sh 通过 --export 传入）；
#                        sbatch 会把本脚本复制到 slurmd 的 spool 目录再执行，
#                        这时 $0 指向的是那份拷贝，不能再用它反推仓库根/run_one.sh 路径
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
    if [ $? -ne 0 ]; then
        echo "错误：module purge 失败，模块系统不可用" >&2
        exit 1
    fi
    # 注意顺序：intel-oneapi-mkl 挂在 openmpi 层级下，必须先 load openmpi
    module load openmpi/4.1.8-6xzv intel-oneapi-compilers/2025.3.1-pbro intel-oneapi-mkl/2025.3.1-iqtm
    if [ $? -ne 0 ]; then
        echo "错误：module load 失败，检查模块名称或模块树：openmpi/4.1.8-6xzv intel-oneapi-compilers/2025.3.1-pbro intel-oneapi-mkl/2025.3.1-iqtm" >&2
        exit 1
    fi
fi

export PATH="${EMTO_BIN:-$HOME/intel-mkl-omp-build-2021-Mar/bin}:$PATH"
export OMP_NUM_THREADS=1
export OMP_STACKSIZE=800m
ulimit -s unlimited

# run_one.sh 的绝对路径必须在 cd 之前算出来。sbatch 执行的是本脚本在
# slurmd spool 目录下的拷贝，$0 推出来的目录是 spool 目录而不是仓库的
# jobs/ 目录，所以优先用 submit_stage.sh 显式传入的 EMTO_REPO_ROOT；
# 只有直接调用本脚本（没有 EMTO_REPO_ROOT，例如测试）时才回退到 $0。
if [ -n "${EMTO_REPO_ROOT:-}" ]; then
    run_one="$EMTO_REPO_ROOT/jobs/run_one.sh"
else
    script_dir=$(cd "$(dirname "$0")" && pwd)
    run_one="$script_dir/run_one.sh"
fi

if [ ! -x "$run_one" ]; then
    echo "错误：找不到可执行的 run_one.sh：$run_one（检查 EMTO_REPO_ROOT 是否正确传入）" >&2
    exit 1
fi

# 同理，chunk 文件里的路径是相对仓库根的，cd 目标也优先用 EMTO_REPO_ROOT。
cd "${EMTO_REPO_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}" || exit 1

: "${WORKLIST_DIR:?错误：WORKLIST_DIR 未设置（应由 submit_stage.sh 通过 --export 传入）}"

chunk="$WORKLIST_DIR/chunk_$(printf '%04d' "${SLURM_ARRAY_TASK_ID:-1}")"
if [ ! -f "$chunk" ]; then
    echo "错误：找不到 chunk 文件 $chunk" >&2
    exit 1
fi

ntasks=$(wc -l < "$chunk")
echo "[$(date '+%F %T')] 开始 $chunk（$ntasks 个任务，并发 ${EMTO_NPROC:-96}）"

# xargs -P 是动态取任务：worker 跑完一个立刻领下一个，天然负载均衡。
# run_one.sh 单点失败不影响其它任务，失败信息留在 .prn 里由分析阶段收集。
# -I{} 已隐含每次调用一个参数，不能再加 -n 1（两者同时给 GNU xargs 会告警）。
xargs -a "$chunk" -P "${EMTO_NPROC:-96}" -I{} bash "$run_one" {}
xargs_rc=$?

echo "[$(date '+%F %T')] 完成 $chunk（xargs 退出码 $xargs_rc）"

# xargs 退出码：0 = 全部成功；123 = 至少一次调用返回非 0（即某些点失败，
# 这是设计上容忍的情况，失败详情留在各点的 .prn/日志里，不应让整个
# array task 失败）；126/127 等是 xargs 自身或 run_one.sh 启动失败
# （命令不可执行 / 找不到），这类必须让 array task 失败，否则会和
# Fix 1 的问题一样被 Slurm 误报为 COMPLETED。
if [ "$xargs_rc" -eq 0 ] || [ "$xargs_rc" -eq 123 ]; then
    exit 0
fi
exit "$xargs_rc"
