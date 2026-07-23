# highthroughput-dft-rhea

面向 BCC 难熔高熵合金（RHEA）的高通量 EMTO-CPA 计算流水线。基于
[pyemto](https://github.com/hpleva/pyemto) 批量生成 KGRN/KFCD 输入文件，并对集群
算完的结果做状态方程（EOS）拟合、弹性常数拟合与力学性能推导。

输入数据为 `20260718-refractory-hea-compositions-1600-highthroughput-dft.csv`，
包含 1598 个成分（Ti, Zr, Hf, V, Nb, Ta, Mo, W, Re 九元素体系，2–7 组元，
原子百分比之和为 100）。

> **注意**：KSTR / BMDL / SHAPE 结构文件由用户自行提供（`--latpath` 指向的目录，
> 默认 `/work/scratch/md88vyxi/workplace/highthroughput-dft-rhea/structures`）。本仓库负责
> KGRN/KFCD 输入的生成、向 Slurm 提交（`jobs/`，见「集群提交」一节）与结果分析。
>
> 仓库里的 `structures/` 只跟踪 kstr/bmdl/shape 的**输入卡**（`*.kstr` / `*.bmdl` /
> `*.shape`）和生成脚本 `get_kstr.sh`。KGRN 真正读取的 `kstr/*.tfh`、KFCD 读取的
> `bmdl/*.mdl` 与 `shape/*.shp`（约 280 MB）未纳入版本管理，clone 后需在
> `structures/` 下运行 `get_kstr.sh`（即 `kstr < X.kstr`、`bmdl < X.bmdl`、
> `shape < X.shape`）重新生成。

## 结果与状态

**流水线已跑通全库:stage1 / stage2 / stage3 均 1598 / 1598 = 100%。**

- `results/final_mechanical_properties.csv` —— 全 1598 个合金的 C11/C12/C44/C′ + 派生力学量 + 拟合质量(R²、离群剔除点数)+ Born 稳定性,**全部经基态确认**。
- `results/20260723-难熔高熵合金弹性力学性质-基态确认1598条-高通量DFT计算.csv` + `results/README-弹性力学性质.md` —— 面向合作者的交付版(附中文列说明、方法、局限、溯源)。
- **验证**:W91Re9(DFT_0001)与纯 W 单晶实验各弹性常数均在几个 % 内吻合(C11 533 vs 522、C44 158 vs 161、B 306 vs 310 GPa)。

关键发现(详见 `docs/stage3-report.md`):

- **收敛调参**:弹性畸变破坏立方对称、比 EOS 难收敛。全库靠**离群守卫** + 分档 **depth/AMIX/IEX**(`config.py` 的 `_params_for`)达到 100%——含 Hf 合金走混合 depth(B0@0.95 + C′@浅),富 Ta 角要更深 depth,DFT_0198 靠 IEX=3(VWN)修 Hf 4f 原子解发散。
- **AMIX 物理**(§5.1):慢 AMIX 对 Hf 双稳合金钉基态(解药),对富 V 尖 DOS 合金反而破坏费米搜索(毒药);真正的数据健康判据是**拟合质量,不是原始 energy-gap**。
- **Born 失稳规律**(§4.1):12 个 C′≤0 失稳合金**全部**落在低 VEC(≤4.5)+ Hf 富集角,符合第 4 族(Ti/Zr/Hf)BCC 在 0 K 力学亚稳的物理——经全库 1598 检验无反例。

> **原始 DFT 数据不纳入版本管理**:`stageN_*/DFT_XXXX/` 下的逐点中间产物(~98 GB)可由 `run_pipeline.py --generate` + `structures/` 再生,所有 load-bearing 的量已提取进 `results/*.csv`。本地清理与再生见 `docs/archive-manifest.md`。

## 计算参数

| 项 | 值 |
| --- | --- |
| 结构 | BCC（无序合金用 CPA） |
| 交换关联泛函 | PBE |
| 磁性 | 非磁 (`afm='P'`) |
| 展开 | 单展开 (`expan='S'`) |
| 芯态 | 软芯 (`sofc='Y'`) |
| 其余 KGRN/KFCD 参数 | pyemto 默认值 |

## 三阶段流程

```
CSV (1598 个成分)
   │  vegard.py:  SWS_guess = Σ (c_i/100) · SWS_i
   ▼
Stage 1  粗扫 EOS   6 点, SWS_guess ±3%     → stage1_eos_coarse/DFT_XXXX/
   │  (用户提交集群) → 分析 → SWS0, B0
   │      ├─ 极小值落在采样区间边缘/外部 → 写入 retry queue（平移中心）→ --retry 重生成
   │      └─ EMTO 报错 → stage1_errors.csv
   ▼
Stage 2  细扫 EOS   11 点, SWS0 ±1.5%       → stage2_eos_fine/DFT_XXXX/
   │  (提交集群) → 分析 → 精确 SWS0, B0
   ▼
Stage 3  弹性常数（基于 stage2 的 SWS0/B0） → stage3_elastic/DFT_XXXX/
   │  (提交集群) → 分析 → C11, C12, C44 + 力学性能
   ▼
results/final_mechanical_properties.csv
```

每个阶段都是 **生成 → 用户自行提交集群 → 分析** 的手动三步循环；生成与分析都会跳过
已存在的目录 / 已写入结果的 DFT_ID，可以安全地重复执行。

## 用法

```bash
# Stage 1：生成粗扫输入（结构文件目录用 --latpath 指定）
python run_pipeline.py --stage 1 --generate --latpath /path/to/structures

# ——— 用户把 stage1_eos_coarse/ 下的作业提交到集群并等待完成 ———

# Stage 1：拟合 EOS，输出 SWS0/B0，并生成重试队列
python run_pipeline.py --stage 1 --analyze

# 对拟合极小值落在边缘的合金，按平移后的 SWS 中心重新生成输入
python run_pipeline.py --stage 1 --retry
# （重新提交后再次 --analyze）

# Stage 2：细扫
python run_pipeline.py --stage 2 --generate
python run_pipeline.py --stage 2 --analyze

# Stage 3：弹性常数与力学性能
python run_pipeline.py --stage 3 --generate
python run_pipeline.py --stage 3 --analyze

# 错误汇总（不带 --stage 时汇总全部三个阶段）
python run_pipeline.py --errors
python run_pipeline.py --errors --stage 1
```

### 命令行参数

| 参数 | 说明 |
| --- | --- |
| `--stage {1,2,3}` | 阶段编号；除 `--errors` 外必填 |
| `--generate` | 生成该阶段的 EMTO 输入文件 |
| `--analyze` | 分析该阶段已完成的输出 |
| `--retry` | 按重试队列重新生成输入（仅 stage 1 支持） |
| `--errors` | 打印错误统计汇总 |
| `--latpath PATH` | KSTR/BMDL/SHAPE 所在目录，默认 `/work/scratch/md88vyxi/workplace/highthroughput-dft-rhea/structures` |

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
| `--partition P` / `-p P` | `deflt` | 分区 |
| `--account A` | `p0020537` | Slurm 账户 |
| `--limit N` | 0（全部） | 只取前 N 个未完成任务；0 表示不限制 |
| `--dry-run` | | 只打印统计与 sbatch 命令，不落盘不提交 |

`stage` 必须是 `1`、`2` 或 `3`；`--chunk`/`--maxpar` 需为正整数，`--limit`
需为非负整数，选项值不合法或缺失时脚本会打印错误并以退出码 2 结束，不会
提交任何作业。

脚本会扫描 `stageN_*/DFT_XXXX/*.kgrn`，**跳过 `kfcd/<job>.prn` 已含 `FINISHED`
的点**，把剩下的切块写进 `jobs/worklists/stageN_<时间戳>/`，再提交一个 Slurm
array 作业。因此**重跑就是再执行一次同一条命令** —— 断点续跑、超时点补算、
`--retry` 重生成后的补算都不需要手工挑合金。

注意重跑收敛的前提是失败原因是**被打断**（超时、节点故障等）：一个点如果
本身会持续崩溃或永不收敛，每次重跑都会被原样重新排进 worklist，每次都要
再烧掉最多 `EMTO_TIMEOUT` 秒才失败，不会自己停止重试；这类点需要靠
`python run_pipeline.py --stage N --analyze` / `--errors` 识别出来，人工处理
或调整参数后再走 `--retry`。

三个脚本的分工：

| 脚本 | 职责 |
| --- | --- |
| `jobs/submit_stage.sh` | 扫描未完成 → 切块 → `sbatch` |
| `jobs/job_array.sh` | array 作业体：加载 module，`xargs -P 96` 消费一块 |
| `jobs/run_one.sh` | 跑一个点：`cd` 进合金目录、幂等跳过、`timeout` 保护、记录耗时；`EMTO_CLEANUP=1` 时额外清中间文件 |

每个点跑完（无论成功还是失败）都会在 `jobs/worklists/<本次>/timing.log` 追加
一行，格式 `<jobname> <kgrn秒> <kfcd秒> <退出码>`；但幂等跳过的点（上次已经
`FINISHED`、这次直接跳过）不会写入，所以行数不等于该次 worklist 的任务总数，
只能反映本次实际运行过的点。用它来校准 `--chunk` 与 `EMTO_TIMEOUT`：

- `--chunk` ≈ 96 × 目标块时长(3~4 h) / 平均单点耗时
- `EMTO_TIMEOUT` ≈ 最慢点耗时的 3~4 倍（默认 7200 秒）

### 环境变量（`jobs/run_one.sh` / `jobs/job_array.sh`）

`run_one.sh` / `job_array.sh` 本身在计算节点上运行，不接受命令行参数；下面
这些变量全部要设在**提交作业的那条 `submit_stage.sh` 命令行**上，通过
`sbatch --export=ALL` 原样带到计算节点，而不是登录到计算节点后再设置：

```bash
EMTO_TIMEOUT=10800 EMTO_NPROC=48 EMTO_CLEANUP=1 jobs/submit_stage.sh 1
```

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `EMTO_TIMEOUT` | 7200 | 单个 KGRN/KFCD 二进制的墙钟上限（秒） |
| `EMTO_CLEANUP` | 未设置（不清理） | 设为 `1` 才删除 `.atm/.chd/.pot/.zms` 与 `kgrn/tmp/` 等中间大文件；`.prn` 始终保留供分析阶段解析 |
| `WORKLIST_DIR` | （由 `submit_stage.sh` 传入） | 非空时向 `$WORKLIST_DIR/timing.log` 追加计时；不建议手动覆盖 |
| `EMTO_NPROC` | 96 | `job_array.sh` 内 `xargs -P` 的并发数 |
| `EMTO_BIN` | `$HOME/intel-mkl-omp-build-2021-Mar/bin` | EMTO 二进制所在目录 |

`EMTO_CLEANUP` 默认不开启：冒烟测试阶段需要保留 `.pot`/`.chd` 等文件排查 SCF
收敛问题；但全量跑批时 46000 个点若都保留这些势函数与电荷密度文件会很快
把 scratch 配额耗尽，因此大规模提交前应显式设置 `EMTO_CLEANUP=1`：

```bash
EMTO_CLEANUP=1 jobs/submit_stage.sh 1
```

完整流程：

```bash
python run_pipeline.py --stage 1 --generate
jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00   # 冒烟
EMTO_CLEANUP=1 jobs/submit_stage.sh 1                           # 全量
python run_pipeline.py --stage 1 --analyze
python run_pipeline.py --stage 1 --retry
EMTO_CLEANUP=1 jobs/submit_stage.sh 1                           # 补算
python run_pipeline.py --stage 1 --analyze
```

Stage 2、3 同构。

### 测试

提交脚本自带一套纯 bash 测试（不依赖 Slurm、EMTO 二进制、pytest 或 bats）：

```bash
bash jobs/tests/run_all.sh
```

## 输出文件

全部写入 `results/`，均为可增量追加的 CSV：

| 文件 | 内容 |
| --- | --- |
| `stage1_coarse_results.csv` | `DFT_ID, Alloy, SWS0, B0`（粗扫） |
| `stage1_retry_queue.csv` | `DFT_ID, Alloy, old_sws_center, new_sws_center, reason, retry_round` |
| `stage2_fine_results.csv` | `DFT_ID, Alloy, SWS0, B0`（细扫，供 stage3 用） |
| `stage3_elastic_r2.csv` | 各合金 C′/C44 畸变拟合的 R²、离群剔除点数 |
| `final_mechanical_properties.csv` | 全量 1598 条:SWS0, B0, C11/C12/C44/C′ 与派生力学量 + R² + Born 稳定性 |
| `stageN_errors.csv` | `DFT_ID, Alloy, SWS, error_type, message` |

**面向合作者的交付版**（`git` 中随版本管理，附中文说明）:

| 文件 | 内容 |
| --- | --- |
| `20260723-…基态确认1598条….csv` | 全库交付版（与 `final_mechanical_properties.csv` 同内容） |
| `README-弹性力学性质.md` | 23 列定义、方法、解读、已知局限、溯源 |
| `20260722-…基态确认1480条….csv` | 历史 v1（README 记录演进用） |

`final_mechanical_properties.csv` 的列：`SWS0, B0, C11, C12, C44, cprime, B,
G_V, G_R, G_VRH, E, nu, B_G_ratio, Cauchy, A, Hv, R2_cprime, R2_c44,
n_drop_cprime, n_drop_c44, born_stable`。派生量:体模量 `B`，剪切模量
`G_V`/`G_R`/`G_VRH`（Voigt–Reuss–Hill），杨氏模量 `E`，泊松比 `nu`，
`B_G_ratio`（Pugh 比），Cauchy 压 `Cauchy = C12 − C44`，各向异性因子
`A = 2C44/(C11 − C12)`，经验硬度 `Hv = 2(k²G)^0.585 − 3`（`k = G/B`），
`R2_*`/`n_drop_*` 为畸变拟合的质量与离群守卫剔除点数，`born_stable` 为
Born 力学稳定性（Y/N）。

## 模块结构

| 文件 | 职责 |
| --- | --- |
| `config.py` | 常量：元素 Wigner–Seitz 半径、EMTO 参数、目录名、采样点数与范围 |
| `vegard.py` | Vegard 定律估算初始 SWS；校验浓度和为 100 |
| `emto_generator.py` | CSV 解析；调用 pyemto 生成 EOS / 弹性常数输入 |
| `eos_analysis.py` | EOS 拟合、粗扫拟合质量检查（`check_coarse_fit`）与重试队列写出 |
| `elastic_analysis.py` | 解析弹性常数输出、计算力学性能 |
| `error_collector.py` | 扫描 kgrn/kfcd 输出，识别错误类型并汇总 |
| `run_pipeline.py` | CLI 入口，串联各阶段 |
| `jobs/submit_stage.sh` | 扫描未完成任务、切块、提交 Slurm array 作业 |
| `jobs/job_array.sh` | array 作业体，每节点 `xargs -P 96` 消费一块 worklist |
| `jobs/run_one.sh` | 单点执行器：幂等、超时保护、计时；`EMTO_CLEANUP=1` 时清中间文件 |

### 错误类型

`error_collector.py` 逐个 job 检查 `kgrn/*.prn` 与 `kfcd/*.prn`，可报出：

- `missing_output` —— kfcd 输出缺失或为空
- `scf_not_converged` —— KGRN 输出中出现 `NOT CONVERGED`
- `no_energy` —— kfcd 输出中找不到 `TOT-PBE` / `TOT-LDA`
- `nan_energy` —— 总能为 NaN 或无法解析

EOS 拟合额外的保护：有效 SWS 点少于 4 个、拟合抛异常，或 `B0 ≤ 0`、`B0 > 1000 GPa`
都判为失败并进入重试队列（stage 1）。

## 依赖

- Python 3
- `numpy`
- `pyemto`
- `pytest`（仅测试）

## 测试

测试直接 import 顶层模块，需要在仓库根目录运行：

```bash
python -m pytest tests/
```

## 文档

- **stage3 弹性常数报告**：`docs/stage3-report.md` —— 方法、全库结果、§4.1 Born 失稳成分规律、§5 收敛调参分档、§5.1 AMIX 物理
- **stage2 细扫 EOS 报告**：`docs/stage2-summary-report.md`
- **交付版说明**：`results/README-弹性力学性质.md`
- **归档 / 清理 manifest**：`docs/archive-manifest.md` —— raw DFT 目录逐条删除命令 + 再生方式
- 设计文档：`docs/superpowers/specs/2026-07-20-highthroughput-emto-rhea-design.md`、`docs/superpowers/specs/2026-07-23-repo-github-vs-archive-design.md`
- 实施计划：`docs/superpowers/plans/2026-07-20-highthroughput-emto-rhea.md`
