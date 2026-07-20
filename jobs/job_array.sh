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
