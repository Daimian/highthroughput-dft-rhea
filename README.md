# highthroughput-dft-rhea

难熔高熵合金（RHEA）的高通量 EMTO/DFT 计算流水线，覆盖 1600 个 BCC 成分。

## 入口

`run_pipeline.py --stage {1,2,3}` —— 三阶段流水线。

## 模块

| 文件 | 职责 |
|---|---|
| `config.py` | 元素集、粗/细扫描点数与范围、目录布局 |
| `vegard.py` | Vegard 定律估算 Wigner-Seitz 半径 |
| `emto_generator.py` | 解析成分 CSV，生成 EOS 与弹性常数输入 |
| `eos_analysis.py` | 状态方程拟合 |
| `elastic_analysis.py` | 弹性常数分析 |
| `error_collector.py` | 失败算例汇总 |

## 数据

`20260718-refractory-hea-compositions-1600-highthroughput-dft.csv` —— 1600 个成分定义。

## 环境

无依赖声明。需要 Python + numpy，以及外部 EMTO 程序（kgrn/kfcd，不在本仓库）。
方法学与 `FeC-BCC-EMTO` 同源。
