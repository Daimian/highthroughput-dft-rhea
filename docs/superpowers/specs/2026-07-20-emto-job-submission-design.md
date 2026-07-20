# EMTO 作业提交脚本设计

面向 Lichtenberg (TU Darmstadt) Slurm 集群，为高通量 EMTO 流水线的三个 stage
提供统一的作业提交机制。

## 背景与目标

`run_pipeline.py` 已能生成三个 stage 的 KGRN/KFCD 输入并分析输出，但中间的
「把任务投到集群」这一步还是空白。规模：

| Stage | 合金数 | 每合金点数 | 串行任务总数 |
| --- | --- | --- | --- |
| 1 粗扫 EOS | 1597 | 6 | 9 582 |
| 2 细扫 EOS | 1597 | 11 | 17 567 |
| 3 弹性常数 | 1597 | 12（bcco0-5 + bccm0-5） | 19 164 |
| 合计 | | | **~46 300** |

单个 KGRN+KFCD 约 10~30 min（估值，待测试校准）。按 20 min 计，总量约
15 000 core-h ≈ 160 节点小时。瓶颈不在算力，而在**如何把大量串行小任务喂满
96 核节点**，以及**失败与超时后如何断点续跑**。

目标：

1. 96 核节点始终满载，无 straggler 空等
2. 重跑幂等 —— 补算失败点不需要手工挑合金
3. 三个 stage 共用一套机制
4. 与 Python 侧解耦：计算节点上不需要 Python 环境

非目标：不改动 `run_pipeline.py` 的 generate/analyze 逻辑；不做跨 stage 的自动
串联（stage 之间仍由用户确认后手动推进）。

## 现状调查结论

### pyemto 生成的 `*.sh` 不可用

`stage1_eos_coarse/DFT_0001/DFT_0001_2.855389.sh` 有两个问题：

1. 硬编码 `/home/hpleva/EMTO5.8/kgrn/kgrn_cpa`，该路径不存在。本机可执行文件为
   `~/intel-mkl-omp-build-2021-Mar/bin/kgrn_cpa`。
2. 脚本按「从仓库根运行」写死路径前缀，但 `.kgrn` 内的 `DIR002=kgrn/`、
   `DIR003=`、`DIR006=`、`DIR009=`、`DIR010=`、`DIR011=kgrn/tmp/` 都是**相对
   cwd**。从仓库根运行会让全部 1597 个合金写进同一个 `./kgrn/`，互相覆盖。

结论：忽略这些 `.sh`，由 `run_one.sh` 先 `cd` 进合金目录再执行。这同时满足
`error_collector.py` 期望的 `stage_dir/DFT_XXXX/kgrn/*.prn` 布局。

### `~/.emto.sh` 的函数不可直接复用

- `decide_kgrn` 按 `_` 拆 jobname 取 `comp/lat/sws`。本项目 jobname 形如
  `DFT_0001_2.855389`，会拆成 comp=`DFT`、lat=`0001`、sws=`2.855389` —— 错位，
  写出的 `data.txt` 无意义。本项目结果由 `eos_analysis.py` / `error_collector.py`
  直接解析 `.prn`，`data.txt` 本就多余。
- `checkemto` 用 `pgrep -u md88vyxi kgrn_cpa` **全局**杀超时进程，会误杀同用户
  其它作业。改用 GNU `timeout` 逐进程限时。

因此 worker 逻辑在仓库内自写，不 source `~/.emto.sh`。

### 环境模块

必须按此顺序加载（`intel-oneapi-mkl` 挂在 openmpi 层级下，全名
`openmpi/4.1.8-6xzvfyp/intel-oneapi-mkl/2025.3.1-iqtm`，先 load openmpi 才能用
短名解析）：

```bash
module purge
module load openmpi/4.1.8-6xzv intel-oneapi-compilers/2025.3.1-pbro intel-oneapi-mkl/2025.3.1-iqtm
```

已验证：加载后 `kgrn_cpa` / `kfcd_cpa` 的 `libmkl_intel_lp64.so`、
`libmkl_sequential.so`、`libmkl_core.so`、`libiomp5.so` 全部解析成功。

### 集群资源

| 项 | 值 |
| --- | --- |
| 节点 | 96 核 / 364 800 MB，`avx512` |
| `deflt` | 24 h，1199 节点 |
| `long` | 7 d，606 节点 |
| `deflt_short` | 30 min，1206 节点 |
| MaxArraySize | 10 000 |
| 账户 | `-A p0020465` |

块时长切到 ≤24 h 即可用 `deflt`，节点池比 `long` 大一倍，起跑更快。

## 架构

```
jobs/
├── run_one.sh        # 跑一个 .kgrn：幂等跳过 + 超时保护 + 清中间文件
├── job_array.sh      # array 作业体：认领一个 chunk，xargs -P 96 调 run_one.sh
└── submit_stage.sh   # 扫描未完成 → 写 worklist → 切块 → sbatch
```

三个 stage 共用，唯一差异是扫描哪个目录。

### 数据流

```
stageN_*/DFT_XXXX/*.kgrn
    │  submit_stage.sh 扫描，跳过 kfcd/<job>.prn 已 FINISHED 的
    ▼
jobs/worklists/stageN_<timestamp>/
    ├── chunk_0001   (每行一个 .kgrn 相对路径，默认 1000 行)
    ├── chunk_0002
    └── ...
    │  sbatch --array=1-N%8 job_array.sh
    ▼
每个 array task 独占一节点 → xargs -P 96 → run_one.sh <path>
    │  cd 进合金目录，kgrn_cpa → kfcd_cpa
    ▼
stageN_*/DFT_XXXX/{kgrn,kfcd}/<job>.prn
    │  python run_pipeline.py --stage N --analyze
    ▼
results/
```

## 组件设计

### `jobs/run_one.sh`

输入：一个相对仓库根的 `.kgrn` 路径。输出：该合金目录下的 `kgrn/`、`kfcd/`。

职责与不变量：

- **先 `cd` 到 `dirname` 再执行** —— `.kgrn` 内 `DIR00x` 是相对路径，这是正确性
  前提。
- **幂等**：若 `kfcd/<job>.prn` 存在且含 `FINISHED`，立即退出 0。这条让重复提交
  变成安全操作。
- **超时**：`timeout ${EMTO_TIMEOUT:-7200}` 分别包住 kgrn 和 kfcd。只杀自己的
  子进程。
- **SCF 未收敛不跑 KFCD**：`kgrn/<job>.prn` 不含 `FINISHED` 时直接失败退出，
  省下 KFCD 的时间；该点会被 `error_collector.py` 记为
  `scf_not_converged` / `missing_output`。
- **KFCD 也按同一判据验收**：KFCD 退出码为 0 但 `kfcd/<job>.prn` 不含 `FINISHED`
  时，强制失败退出。否则 `run_one.sh` 会报成功、而提交层的扫描仍视该点为未完成，
  导致它在每一轮重新提交时被反复重算。完成判据必须全脚本统一。
- **清理中间文件（默认关闭）**：`EMTO_CLEANUP=1` 时跑完删
  `kgrn/<job>.{atm,chd,pot,zms}` 与 `kgrn/tmp/<job>*`；默认保留。
  保留是为了冒烟测试阶段能排查 SCF 收敛过程；全量提交时在 `job_array.sh` 里打开
  即可，因为 4.6 万个点的势函数/电荷密度文件会撑爆 scratch 配额。
  删除是安全的：已完成的点下次直接跳过，未完成的点本来也要从头重算，不存在从
  已有势函数热启动的需求。`.prn` 任何情况下都不删。

- **计时**：每个点跑完向 `$WORKLIST_DIR/timing.log` 追加一行
  `<job> <kgrn秒> <kfcd秒> <退出码>`（用 `>>` 单行追加，96 并发下小于 PIPE_BUF
  的写入是原子的，无需加锁）。这是校准 `--chunk` 与 `EMTO_TIMEOUT` 的数据来源，
  也便于事后发现异常慢的成分。

退出码：0 = 成功或已完成；非 0 = 该点失败（超时、SCF 未收敛、二进制报错）。
array task 不因单点失败而中止，失败信息留在 `.prn` 里由分析阶段统一收集。

### `jobs/job_array.sh`

Slurm array 作业体。一个 array task = 一个整节点。

```bash
#SBATCH -N 1 -n 96 -c 1 -A p0020465 -C avx512 --mem-per-cpu=3800
#SBATCH --mail-type=NONE --export=ALL
```

`-t`、`--array`、`-p` 由 `submit_stage.sh` 在命令行覆盖，不写死在文件里。

环境：上文的三个 module，`OMP_NUM_THREADS=1`、`OMP_STACKSIZE=800m`、
`ulimit -s unlimited`。

主体：

```bash
cd "$SLURM_SUBMIT_DIR"
chunk="$WORKLIST_DIR/chunk_$(printf %04d "$SLURM_ARRAY_TASK_ID")"
xargs -a "$chunk" -n 1 -P 96 -I{} bash jobs/run_one.sh {}
```

`xargs -P 96` 是**动态取任务**：worker 跑完一个立刻领下一个，天然负载均衡，不会
因为某个 7 元素合金收敛慢就让 95 个核空等。`WORKLIST_DIR` 由
`sbatch --export` 传入。

### `jobs/submit_stage.sh`

```
用法: jobs/submit_stage.sh <1|2|3> [选项]
  --chunk N        每块任务数（默认 1000）
  --maxpar N       同时运行的 array task 上限（默认 8）
  --time HH:MM:SS  单个 array task 时限（默认 24:00:00）
  --partition P    默认 deflt
  --limit N        只取 worklist 前 N 个任务（用于冒烟测试）
  --dry-run        只打印 worklist 统计与将要执行的 sbatch 命令，不提交
```

流程：

1. 按 stage 号从 `config.py` 对应的 `STAGE_DIRS` 取目录名（在脚本内以常量镜像，
   避免 shell 依赖 Python）。
2. 遍历 `<stage_dir>/*/*.kgrn`，对每个 job 检查同目录 `kfcd/<job>.prn` 是否存在
   且含 `FINISHED`；未完成的写入 worklist。
3. 按 `--chunk` 切成 `chunk_0001`…，放在
   `jobs/worklists/stage<N>_<YYYYmmdd-HHMMSS>/`。
4. `sbatch --array=1-<Nchunks>%<maxpar> --export=ALL,WORKLIST_DIR=<dir> \
   -t <time> -p <partition> -J emto_s<N> jobs/job_array.sh`
5. 打印 jobid、块数、任务总数。

**重跑即再执行一次本脚本**。断点续跑、超时点补算、`--retry` 重生成后的补算，全
由第 2 步的扫描自动覆盖，不需要手工挑合金。这是 worklist 方案相对「按目录分组」
方案的核心优势。

时间戳目录保证历史 worklist 不被覆盖，便于事后追查某次提交跑了哪些点。

## 参数默认值

| 参数 | 默认 | 依据 |
| --- | --- | --- |
| `--chunk` | 1000 | 1000 × 20 min / 96 核 ≈ 3.5 h，远低于 24 h 上限，给慢点留余量 |
| `--maxpar` | 8 | 8 节点 = 768 核，不霸队又保证吞吐 |
| `--time` | 24:00:00 | `deflt` 上限；块本身只需 ~3.5 h，余量吸收慢点 |
| `--partition` | `deflt` | 节点池 1199 vs `long` 606，起跑更快 |
| `EMTO_TIMEOUT` | 7200 | 单点 2 h 封顶，不收敛的点不吃满整块 |
| `EMTO_CLEANUP` | 未设（不清理） | 冒烟阶段保留中间文件便于排查；全量提交时置 1 |

按 chunk=1000：stage1 → 10 块，stage2 → 18 块，stage3 → 20 块，均远低于
MaxArraySize=10000。

**这组默认值基于「单点 20 min」的估算，必须由冒烟测试校准后再全量提交。** 若实测
为 5 min，`--chunk` 应放大到约 4000，否则 array task 过碎、调度开销占比升高。

## 测试计划

### 冒烟测试：前 96 个任务（一整节点）

```bash
jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00
```

96 个任务恰好铺满一个 96 核节点，即 DFT_0001~DFT_0016 各 6 个 SWS 点，一轮跑完。
相比只测单个合金，这样能同时得到**耗时分布**（而非单点值）和**满载时的真实 I/O
表现**。时限给 2 h 而非投 `deflt_short`(30 min)，避免慢点被砍导致测不出上界。

验证 7 件事：

1. module 环境在计算节点上与登录节点一致，`kgrn_cpa` 动态库全部解析
2. `run_one.sh` 的 `cd` 使输出落在 `stage1_eos_coarse/DFT_XXXX/kgrn/`，而非仓库根
3. `.kgrn` 中 `FOR001=.../structures/kstr/bcc.tfh` 等绝对路径在节点上可读
4. **单点耗时分布**（均值 / 最慢值）→ 校准 `--chunk` 与 `EMTO_TIMEOUT`
5. **96 核满载下的 I/O 与内存表现** —— 96 个 KGRN 同时写各自的 `kgrn/tmp/`，
   确认无明显 I/O 争用、`--mem-per-cpu=3800` 够用
6. 幂等性：再次执行同一命令，worklist 应为空（96 个点全部被跳过）
7. `python run_pipeline.py --stage 1 --analyze` 能消费这 16 个合金的输出并拟合出
   SWS0/B0

为了拿到第 4 项，`run_one.sh` 需为每个点记录墙钟时间（见组件设计的计时要求）。

### 参数校准与全量提交

冒烟测试通过并取得耗时分布后，按下式重定参数，再全量提交 stage 1：

- `--chunk` ≈ 96 × (目标块时长 3~4 h) / 平均单点耗时
- `EMTO_TIMEOUT` ≈ 最慢点耗时的 3~4 倍

stage 2、3 沿用校准后的参数（stage 2 单点应更快，因为初值更接近平衡）。

### 脚本自身的验证

`--dry-run` 用于在不占用队列的前提下检查 worklist 规模、块数与 sbatch 命令行。

## 运行流程（三个 stage）

```bash
# Stage 1
python run_pipeline.py --stage 1 --generate
jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00   # 冒烟：一整节点
jobs/submit_stage.sh 1                                         # 校准参数后全量
python run_pipeline.py --stage 1 --analyze
python run_pipeline.py --stage 1 --retry     # 极小值在边缘的合金重生成
jobs/submit_stage.sh 1                       # 补算（自动只捡未完成的）
python run_pipeline.py --stage 1 --analyze

# Stage 2 / 3 同构
python run_pipeline.py --stage 2 --generate && jobs/submit_stage.sh 2
python run_pipeline.py --stage 2 --analyze
python run_pipeline.py --stage 3 --generate && jobs/submit_stage.sh 3
python run_pipeline.py --stage 3 --analyze
```

## 风险与对策

| 风险 | 对策 |
| --- | --- |
| scratch 配额被中间文件撑爆 | 全量提交时置 `EMTO_CLEANUP=1`，`run_one.sh` 跑完即删 `.atm/.chd/.pot/.zms` 与 `tmp/`（默认保留，供冒烟阶段排查） |
| 单点不收敛吃满整块时间 | `EMTO_TIMEOUT` 单点 2 h 封顶 |
| 96 个并发进程的 I/O 压力 | 中间文件写在各合金自己的 `kgrn/tmp/`，分散在不同目录；冒烟测试后观察全节点满载时的表现 |
| 误杀其它作业的进程 | 用 `timeout` 而非 `pgrep kill` |
| array task 被抢占/超时中断 | 幂等扫描使重新提交自动接续，已完成的点不重算 |
| 单点耗时估算偏差导致块划分不当 | 冒烟测试校准后再全量提交 |

## 未来可选项（当前不做）

- `deflt_short`（30 min）投小块捡空闲节点，压缩排队时间
- 三个 stage 之间用 `--dependency=afterok` 自动串联（当前保留人工确认）
