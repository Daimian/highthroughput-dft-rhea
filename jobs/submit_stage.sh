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

# Helper: ensure an option has a value before accessing $2
check_option_has_value() {
    local option=$1
    local remaining_arg_count=$2
    if [ "$remaining_arg_count" -lt 2 ]; then
        echo "错误：选项 $option 需要一个值" >&2
        exit 2
    fi
}

# Helper: validate that a value is a positive integer (>= 1)
validate_positive_int() {
    local option=$1
    local value=$2
    if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
        echo "错误：$option 必须是正整数，得到 '$value'" >&2
        exit 2
    fi
}

# Helper: validate that a value is a non-negative integer (>= 0)
validate_nonnegative_int() {
    local option=$1
    local value=$2
    if ! [[ "$value" =~ ^(0|[1-9][0-9]*)$ ]]; then
        echo "错误：$option 必须是非负整数，得到 '$value'" >&2
        exit 2
    fi
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
        --chunk)
            check_option_has_value "--chunk" "$#"
            CHUNK=$2
            validate_positive_int "--chunk" "$CHUNK"
            shift 2
            ;;
        --maxpar)
            check_option_has_value "--maxpar" "$#"
            MAXPAR=$2
            validate_positive_int "--maxpar" "$MAXPAR"
            shift 2
            ;;
        --time)
            check_option_has_value "--time" "$#"
            TIME=$2
            shift 2
            ;;
        --partition|-p)
            check_option_has_value "$1" "$#"
            PARTITION=$2
            shift 2
            ;;
        --limit)
            check_option_has_value "--limit" "$#"
            LIMIT=$2
            validate_nonnegative_int "--limit" "$LIMIT"
            shift 2
            ;;
        --dry-run)
            DRYRUN=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "错误：未知选项 $1" >&2
            usage
            exit 2
            ;;
    esac
done

# REPO_ROOT 可覆盖，便于测试用假仓库（使用本地 REPO_ROOT 而非相对路径查找）
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
found=0
while IFS= read -r kgrn_file; do
    found=$((found + 1))
    d=$(dirname "$kgrn_file")
    j=$(basename "$kgrn_file" .kgrn)
    if [ -f "$d/kfcd/$j.prn" ] && grep -qi finished "$d/kfcd/$j.prn"; then
        continue
    fi
    pending+=("$kgrn_file")
done < <(find "$stage_dir" -mindepth 2 -maxdepth 2 -name '*.kgrn' | sort)

# find 一个 .kgrn 都没扫到，但 stage 目录下确实有子目录：说明这个 stage
# 的实际布局和 -mindepth 2 -maxdepth 2 假设的“stage/<合金>/<job>.kgrn”
# 两层结构对不上（例如 stage3 弹性常数输入嵌套更深），而不是真的全部
# 完成。这种情况不能打印“无未完成任务”后退出 0——那和真正做完了没法
# 区分，会被上层脚本/人误判为成功。
if [ "$found" -eq 0 ]; then
    if find "$stage_dir" -mindepth 1 -maxdepth 1 -type d -print -quit | grep -q .; then
        echo "警告：$stage_dir 下有子目录，但没有找到任何 *.kgrn 文件（预期路径形如 $stage_dir/<合金>/<job>.kgrn）；请检查该 stage 的目录层级是否与预期不同" >&2
        exit 1
    fi
fi

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
    "--export=ALL,WORKLIST_DIR=${worklist_dir},EMTO_REPO_ROOT=${repo_root}"
    "-o" "${worklist_dir}/slurm-%A_%a.out"
    "$repo_root/jobs/job_array.sh"
)

if [ "$DRYRUN" -eq 1 ]; then
    echo "dry-run: 不写 worklist，不提交"
    echo "将执行 sbatch 命令: $submit_cmd ${sbatch_args[*]}"
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
