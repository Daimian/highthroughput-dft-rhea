# highthroughput-dft-rhea

面向 BCC 难熔高熵合金（RHEA）的高通量 EMTO-CPA 计算流水线。基于
[pyemto](https://github.com/hpleva/pyemto) 批量生成 KGRN/KFCD 输入文件，并对集群
算完的结果做状态方程（EOS）拟合、弹性常数拟合与力学性能推导。

输入数据为 `20260718-refractory-hea-compositions-1600-highthroughput-dft.csv`，
包含 1597 个成分（Ti, Zr, Hf, V, Nb, Ta, Mo, W, Re 九元素体系，2–7 组元，
原子百分比之和为 100）。

> **注意**：KSTR / BMDL / SHAPE 结构文件由用户自行提供（`--latpath` 指向的目录，
> 默认 `./structures`）。本仓库只负责 KGRN/KFCD 的生成与结果分析，不负责作业提交。

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
CSV (1597 个成分)
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
| `--latpath PATH` | KSTR/BMDL/SHAPE 所在目录，默认 `./structures` |

## 输出文件

全部写入 `results/`，均为可增量追加的 CSV：

| 文件 | 内容 |
| --- | --- |
| `stage1_coarse_results.csv` | `DFT_ID, Alloy, SWS0, B0`（粗扫） |
| `stage1_retry_queue.csv` | `DFT_ID, Alloy, old_sws_center, new_sws_center, reason, retry_round` |
| `stage2_fine_results.csv` | `DFT_ID, Alloy, SWS0, B0`（细扫） |
| `final_mechanical_properties.csv` | SWS0, B0, C11/C12/C44 与派生力学量 |
| `stageN_errors.csv` | `DFT_ID, Alloy, SWS, error_type, message` |

`final_mechanical_properties.csv` 中的派生量：体模量 `B`，剪切模量 `G_V`/`G_R`/`G_VRH`
（Voigt–Reuss–Hill），杨氏模量 `E`，泊松比 `nu`，`B_G_ratio`（Pugh 比），
Cauchy 压 `Cauchy = C12 − C44`，各向异性因子 `A = 2C44/(C11 − C12)`，
以及经验硬度 `Hv = 2(k²G)^0.585 − 3`（`k = G/B`）。

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

- 设计文档：`docs/superpowers/specs/2026-07-20-highthroughput-emto-rhea-design.md`
- 实施计划：`docs/superpowers/plans/2026-07-20-highthroughput-emto-rhea.md`
