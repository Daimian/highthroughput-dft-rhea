# 归档 / 清理 manifest

日期:2026-07-23　|　设计依据:`docs/superpowers/specs/2026-07-23-repo-github-vs-archive-design.md`

## 结论

**raw DFT 目录一律不归档、不进 git。** 每个 stage 下单个 DFT 计算的中间产物（`.prn/.pot/.chd/.atm`、kgrn/kfcd 工作文件）承载的科学量都已提取进 `results/` 的 CSV,且可由 `run_pipeline.py --generate` + `structures/` 输入卡再生。故这些目录可安全删除,腾出 ~98 GB。

进 git 的精选成果见 `.gitignore` 白名单;此文件只负责记录"曾存在什么、如何再生、怎么删"。

## 删除前安全检查

先确认交付物与复现中间表已入库,再删 raw:

```bash
git ls-files results/ | grep -E 'final_mechanical_properties|stage2_fine_results|1598条'
# 应列出这三者;若为空,先提交 results/ 白名单文件再往下删。
```

## 逐条删除命令

```bash
# --- raw DFT 主目录（run_pipeline.py --generate 可再生；箭头为已入库的对应 CSV） ---
rm -rf stage1_eos_coarse/    # 21G  -> results/stage1_coarse_results.csv
rm -rf stage2_eos_fine/      # 36G  -> results/stage2_fine_results.csv (sws0/B0)
rm -rf stage3_elastic/       # 39G  -> results/final_mechanical_properties.csv

# --- 一次性修正 / 验证跑（结果已并入 final CSV / 结论已入报告） ---
rm -rf stage3_g118/          # 2.7G 30 个 Hf 激发态修正 + 78 个复核，已并入 final CSV
rm -rf stage3_v9/            # 55M  9 个富 V depth0.95+amix0.01 验证（结论:production 值可信）

# --- 定向调参诊断目录（结论已入 docs/stage3-report.md §5/§5.1 + memory，合计 ~800M） ---
rm -rf stage3_a01/ stage3_cross/ stage3_d10/ stage3_dirac/ stage3_gapchk/ \
       stage3_hfcore/ stage3_iex/ stage3_lmaxh/ stage3_niter/ stage3_sofc/ \
       stage3_ta100/ stage3_tune/ stage3_tune9/ stage3_tuneA/ stage3_tuneB/ \
       stage3_tuneD/ stage3_vmix/

# --- 零残值文件 ---
rm -f dos_DFT_0007.png dos_DFT_0229.png eos_DFT_0243.png   # 一次性诊断图，无引用
rm -f job-emto-default.sh                                   # 被 jobs/ 取代，且账号 p0020465 是错的

# --- results/ 冗余副本与备份 ---
rm -f results/mechanical_properties_healthy.csv            # 与 1598 CSV 逐字节相同
rm -f results/final_mechanical_properties.csv.bak_pre_g118merge \
      results/final_mechanical_properties.csv.bak_premixed \
      results/stage2_fine_results.csv.bak_predepth80
```

## 再生方式（如日后需要 raw 数据）

1. `python run_pipeline.py --generate --stage {1,2,3}` 重新生成输入并提交 Slurm(见 `jobs/submit_stage.sh`、memory `emto-analysis-env`)。
2. 分档收敛参数（depth/AMIX/IEX）已固化在 `config.py` 的 `_params_for`,再生即复现同一结果。
3. `structures/` 的 kstr/bmdl/shape 二进制由 `structures/get_kstr.sh` 再生。

## 大小汇总

| 桶 | 内容 | 大小 |
|---|---|---|
| raw 主目录 | stage1/2/3_elastic | ~96 G |
| 修正/验证 | g118 + v9 | ~2.8 G |
| 调参诊断 | 17 个 stage3_* 变体 | ~0.8 G |
| 零残值 | PNG + job 脚本 + bak | < 1 M |
| **合计可释放** | | **~98 GB** |
