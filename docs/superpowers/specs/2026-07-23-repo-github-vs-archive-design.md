# 设计:仓库分流 — GitHub vs 本地存档

日期:2026-07-23　|　范围:`highthroughput-dft-rhea` 仓库当前状态的一次性整理

## 1. 目标与原则

把仓库整理成一个**可复现研究包**:GitHub 里放"clone 后能重新推导出全部结果的一切",但不含"可再生且巨大"的 raw DFT 输出。

**核心洞察**:所有 load-bearing 的科学量(sws0、B0、C11/C12/C44、cprime、R²、Born 稳定性、各 stage 误差)**都已被提取进 `results/` 的 CSV**。raw DFT 目录(每个畸变点的 `.prn/.pot/.chd/.atm`、kgrn/kfcd 工作文件)只是这些数字的可再生原料。

由此:
- **进 git 的精选 CSV + 代码 + 输入卡 = 完整可复现包**。
- **raw DFT 目录既不进 git、也不归档**——内容已在 CSV 里,且由 `run_pipeline.py` + `structures/` 输入卡可再生。
- 无独立"本地存档"层。整理产出一份 manifest 记录曾存在什么、如何再生、逐条删除命令。

## 2. 三个桶

### 桶 A — 进 GitHub

**已跟踪,保留不动**(154 文件):`*.py`(config/elastic_analysis/emto_generator/efgs/eos_analysis/error_collector/run_pipeline/vegard)、`tests/`、`docs/`、`jobs/`、`structures/` 输入卡、`20260718-refractory-hea-compositions-1600-highthroughput-dft.csv`、`README.md`、`.gitignore`。

**新增**(从当前被 `.gitignore` 屏蔽的 `results/` 里精选,这一层即捕获全部科学产出):

| 文件 | 类别 |
|---|---|
| `results/20260723-难熔高熵合金弹性力学性质-基态确认1598条-高通量DFT计算.csv` | 交付物(全库 v3) |
| `results/final_mechanical_properties.csv` | 交付物(全量,内容同上) |
| `results/README-弹性力学性质.md` | 交付物说明 |
| `results/20260722-难熔高熵合金弹性力学性质-基态确认1480条-高通量DFT计算.csv` | 历史 v1(README 引用) |
| `results/stage1_coarse_results.csv` | 复现中间表 |
| `results/stage2_fine_results.csv` | 复现中间表(提供 sws0/B0) |
| `results/stage3_elastic_r2.csv` | 拟合质量表 |
| `results/stage1_errors.csv` `results/stage2_errors.csv` `results/stage3_errors.csv` | provenance 误差日志 |

**不进 git**:`results/mechanical_properties_healthy.csv`(与 1598 CSV 逐字节相同的通用名副本,冗余)、`results/*.bak_*`(被取代的备份)。

### 桶 B — 不归档 / 待删(不进 git、不存档)

内容已进 CSV,可由代码+输入再生。可安全删除或任 scratch 清理。

| 目录 | 大小 | 再生方式 |
|---|---|---|
| `stage1_eos_coarse/` | 21G | `run_pipeline.py --generate --stage 1` 后提交 |
| `stage2_eos_fine/` | 36G | `run_pipeline.py --generate --stage 2` |
| `stage3_elastic/` | 39G | `run_pipeline.py --generate --stage 3` |
| `stage3_g118/` | 2.7G | 一次性修正跑(结果已并入 final CSV) |
| `stage3_v9/` | 55M | 一次性验证跑(结论:9 个富 V 可信) |
| `stage3_a01 cross d10 dirac gapchk hfcore iex lmaxh niter sofc ta100 tune tune9 tuneA tuneB tuneD vmix` | 合计 ~800M | 定向调参诊断,结论已入 `docs/stage3-report.md` §5/§5.1 与 memory |

### 桶 C — 丢弃(零残值)

| 文件 | 原因 |
|---|---|
| `dos_DFT_0007.png` `dos_DFT_0229.png` `eos_DFT_0243.png` | 一次性诊断图,无处引用 |
| `job-emto-default.sh` | 被 `jobs/job_array.sh`+`submit_stage.sh` 取代;且硬编码了错误账号 `p0020465`(正确应为 `p0020537`) |

## 3. `.gitignore` 改动

把笼统的 `results/` 规则换成白名单;新增 `stage3_*/`、`*.png` 让 `git status` 保持干净。

```gitignore
# --- 替换原来的 `results/` 单行 ---
results/*
!results/20260723-难熔高熵合金弹性力学性质-基态确认1598条-高通量DFT计算.csv
!results/20260722-难熔高熵合金弹性力学性质-基态确认1480条-高通量DFT计算.csv
!results/final_mechanical_properties.csv
!results/README-弹性力学性质.md
!results/stage1_coarse_results.csv
!results/stage2_fine_results.csv
!results/stage3_elastic_r2.csv
!results/stage1_errors.csv
!results/stage2_errors.csv
!results/stage3_errors.csv
results/*.bak_*

# --- 新增 ---
stage3_*/          # 所有 stage3 变体(elastic + 调参 + g118/v9);raw 不进 git
*.png
```

注:`stage3_*/` 覆盖了原来单列的 `stage3_elastic/`(可删除那行);`stage1_eos_coarse/`、`stage2_eos_fine/` 保留原有忽略行。

## 4. `docs/archive-manifest.md`(整理产出的 provenance 记录)

内容:
1. **说明**:raw DFT 目录未归档,内容已在 `results/` CSV,可由代码+`structures/` 再生。
2. **逐条删除命令**(含大小、再生提示):

```bash
# raw DFT 主目录(可由 run_pipeline.py --generate 再生;删前确认 results/ 下对应 CSV 已提交)
rm -rf stage1_eos_coarse/    # 21G  -> stage1_coarse_results.csv
rm -rf stage2_eos_fine/      # 36G  -> stage2_fine_results.csv (sws0/B0)
rm -rf stage3_elastic/       # 39G  -> final_mechanical_properties.csv

# 一次性修正/验证跑(结果已并入 final CSV / 结论已入报告)
rm -rf stage3_g118/          # 2.7G
rm -rf stage3_v9/            # 55M

# 定向调参诊断目录(结论已入 docs/stage3-report.md §5/§5.1 + memory)
rm -rf stage3_a01 stage3_cross stage3_d10 stage3_dirac stage3_gapchk \
       stage3_hfcore stage3_iex stage3_lmaxh stage3_niter stage3_sofc \
       stage3_ta100 stage3_tune stage3_tune9 stage3_tuneA stage3_tuneB \
       stage3_tuneD stage3_vmix    # 合计 ~800M

# 丢弃的零残值文件
rm -f dos_DFT_0007.png dos_DFT_0229.png eos_DFT_0243.png job-emto-default.sh

# results/ 冗余副本与备份(可选)
rm -f results/mechanical_properties_healthy.csv results/*.bak_*
```

3. **安全前置检查**(放在命令前):`git ls-files results/ | grep -E 'final_mech|stage2_fine'` 确认交付/中间表已入库,再删 raw。

## 5. 执行步骤(桶 A 由我做,桶 B/C 由用户按 manifest 做)

1. 改 `.gitignore`(§3)。
2. `git add` 白名单 CSV + `README-弹性力学性质.md` + 本设计文档 + `docs/archive-manifest.md` + 本轮更新的 `docs/stage3-report.md`。
3. 提交(信息说明:精选成果入库 + 归档策略 + gitignore 白名单)。
4. 用户按 `docs/archive-manifest.md` 的逐条命令自行清理 raw 目录。

## 6. YAGNI / 不做的事

- 不建独立本地存档(tar/移盘)——中间产物无需保留。
- 不做无关重构。
- 不动 `structures/` 现有的 decks-tracked / binaries-ignored 策略(已合理)。
