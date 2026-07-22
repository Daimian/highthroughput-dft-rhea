ELEMENT_SWS = {
    'Ti': 3.05, 'Zr': 3.35, 'Hf': 3.31,
    'V': 2.82, 'Nb': 3.07, 'Ta': 3.07,
    'Mo': 2.93, 'W': 2.95, 'Re': 2.88,
}

ELEMENTS = ['Ti', 'Zr', 'Hf', 'V', 'Nb', 'Ta', 'Mo', 'W', 'Re']

EMTO_PARAMS = dict(
    lat='bcc',
    xc='PBE',
    afm='P',
    expan='S',
    sofc='Y',
    # 针对 "EFXMOM: Fermi level not found" 的设置。逐项都有因子实验支持：
    #   depth=0.95  必需 —— 其余项到位时 depth=1.0 在 Hf72Ta26Mo2 上仍失败
    #   nx=9        无害的余量（因子实验证明它不是四元系回归的原因）
    #   Hf_4f5d6s   4f14 进入价带
    # amix 曾试过 0.02，但因子实验显示它才是 Nb/Ta/Mo/W 四元系大面积失败的
    # 元凶（混合太慢，前几次迭代的势停在重叠原子势附近），故保持默认 0.05。
    depth=0.95,          # 能量围道深度（Ry），pyemto 默认 1.0
    nx=9,                # 费米能级搜索窗口点数，默认 5
    niter=500,           # SCF 迭代上限，pyemto 默认 100；已收敛的点用 18~26 次，
                         # 加大只影响难收敛的点。注意实测约 4.5 s/次迭代，跑满
                         # 500 次约 38 min，会超过建议的 EMTO_TIMEOUT=1800（30 min），
                         # 届时由墙钟超时先行终止。
    setups={'Hf': '4f5d6s'},   # Hf 的 4f14 进入价带，默认为 Hf_5d6s
    # efgs 不在这里 —— 它逐合金计算，见 efgs.py 与下面的常量。
)

# 富 Ta 角落的收敛覆盖（成分判据）：Ta>=DEEP_TA_THRESHOLD 的合金改用较小的 depth 和
# 较慢的电荷混合 AMIX，避免 SCF 陷入亚稳电子态。
#
# depth：默认 0.95 在富 Ta 合金上会让 SCF 第 4 步就崩 / 陷入亚稳态。depth 扫描显示
#   <=0.85 收敛且能量一致（亚 mRy）、>=0.90 全失败，取 0.80 留悬崖余量。
# 阈值：最初定 70（针对 stage1 粗窗口的压缩端失败）。stage2 精细窗口暴露出问题从
#   Ta~30 就显著：全库统计 Ta<10 基态<4 率 0.7%，Ta30-40 升到 17.5%、Ta40-70 达
#   31~35%（Ta>=70 用 0.80 后为 0%）。故阈值下放到 30。
# AMIX：0.02 比默认 0.05 混得慢，实测能把裂成多态的点收敛回单一基态（DFT_0480 掉队
#   点 -26658→-26693 基态；DFT_1568/1259 从 3~4 态压成 1 态 11 点）。EFMIX 无此作用。
#   历史上 AMIX=0.02 曾在 depth 0.95 破坏 Nb/Ta/Mo/W 四元系，但实测在 depth 0.80 下对
#   Nb 富集的 DFT_0951 无害，故与 depth 0.80 配套使用。
#
# 注意：depth/amix 都会影响能量，同一次 EOS 拟合的所有点必须用同一组参数。判据在输入
# 生成时应用（emto_generator._params_for），每个 stage 各自内部一致。
DEEP_TA_THRESHOLD = 30.0   # Ta 原子百分比，>= 此值用下面的 depth/amix
DEEP_TA_DEPTH = 0.80
DEEP_TA_AMIX = 0.02

# 显式完整覆盖：个别 Ta<30 的合金同样需要 depth 0.80 + AMIX 0.02（与 Ta>=30 同等）。
# 三批：
#   1009/1245/0270 —— 陷入亚稳多态，仅降 AMIX 不够、需连 depth 一起下调（均 Nb 富集）。
#   0334/0791/0243/0497/1366/0779 —— 精细拟合能量有近简并散点（BM 的 B' 爆到 ±几十、
#     Morse R² 只有 0.64~0.87），多为 Nb/Mo/W 富集；用慢混合+小 depth 消掉散点。
#   STAGE3_TA_BATCH（下方 95 个，Ta 1-29）—— stage3 弹性畸变破坏立方对称，比 EOS 更难
#     收敛：这些含 Ta 合金 EOS(对称)在 depth 0.95 下收敛正常，但畸变(破缺)在 depth 0.95
#     会前 1-5 步就崩（实测 DFT_0218/1204：depth0.95 仅 3-8/12 收敛；depth0.80 则 12/12）。
#     故 stage3 畸变一律用 depth 0.80 + AMIX 0.02。depth 非能量中性(改 C')。
#
#     ⚠️ depth 与含 Hf 合金的 EOS 互斥（实测）：depth 0.80 会把富 Hf 合金的 EOS 收敛到伪
#     的膨胀软态（Hf 4f/semicore 需深围道；实测 Hf>=40 的 sws0 外推出窗口、B0 腰斩，如
#     DFT_0070 Hf51 B0 170->65）。故本批按 Hf 分两路，且 depth 是 STAGE 相关的：
#       - 无 Hf 的 35 个：depth 0.80 贯穿 stage2+stage3（EOS 已在 depth0.80 重算、自洽）。
#       - 含 Hf 的 60 个：stage2 的 B0/sws0 保留 depth 0.95（正确 EOS，见 results CSV），
#         仅 stage3 畸变用 depth 0.80（在 depth0.95 的 sws0 处）——即 B0@0.95 + C'@0.80 的
#         混合，C' 带 depth 不一致注脚（条件 A 已验证物理合理，见 docs/stage3-report.md）。
#     注意：_params_for 是 stage 无关的，对这 60 个含 Hf 合金**不要**重跑 stage2 --generate
#     （会错误地产出 depth0.80 的 EOS）；它们的 depth0.95 B0 已固化在 stage2 结果 CSV 里。
_STAGE3_TA_BATCH = {
    'DFT_0067', 'DFT_0070', 'DFT_0080', 'DFT_0095', 'DFT_0100', 'DFT_0108',
    'DFT_0118', 'DFT_0130', 'DFT_0141', 'DFT_0218', 'DFT_0220', 'DFT_0226',
    'DFT_0228', 'DFT_0253', 'DFT_0255', 'DFT_0265', 'DFT_0267', 'DFT_0279',
    'DFT_0296', 'DFT_0329', 'DFT_0332', 'DFT_0349', 'DFT_0350', 'DFT_0357',
    'DFT_0359', 'DFT_0368', 'DFT_0372', 'DFT_0395', 'DFT_0415', 'DFT_0448',
    'DFT_0460', 'DFT_0461', 'DFT_0476', 'DFT_0485', 'DFT_0490', 'DFT_0504',
    'DFT_0506', 'DFT_0514', 'DFT_0534', 'DFT_0535', 'DFT_0537', 'DFT_0552',
    'DFT_0579', 'DFT_0614', 'DFT_0619', 'DFT_0622', 'DFT_0634', 'DFT_0653',
    'DFT_0654', 'DFT_0660', 'DFT_0661', 'DFT_0664', 'DFT_0679', 'DFT_0696',
    'DFT_0700', 'DFT_0747', 'DFT_0777', 'DFT_0818', 'DFT_0871', 'DFT_0889',
    'DFT_0902', 'DFT_0903', 'DFT_0950', 'DFT_0958', 'DFT_0987', 'DFT_1001',
    'DFT_1007', 'DFT_1029', 'DFT_1060', 'DFT_1063', 'DFT_1080', 'DFT_1085',
    'DFT_1092', 'DFT_1109', 'DFT_1117', 'DFT_1204', 'DFT_1217', 'DFT_1271',
    'DFT_1273', 'DFT_1283', 'DFT_1286', 'DFT_1287', 'DFT_1318', 'DFT_1341',
    'DFT_1350', 'DFT_1354', 'DFT_1382', 'DFT_1391', 'DFT_1398', 'DFT_1466',
    'DFT_1472', 'DFT_1479', 'DFT_1571', 'DFT_1580', 'DFT_1586',
}
DEEP_TA_ALLOYS = {
    'DFT_1009', 'DFT_1245', 'DFT_0270',
    'DFT_0334', 'DFT_0791', 'DFT_0243', 'DFT_0497', 'DFT_1366', 'DFT_0779',
} | _STAGE3_TA_BATCH

# 仅降 AMIX（depth 保持 0.95）覆盖：无 Ta 的富 Hf/V 合金 stage3 畸变会散进伪电子态，但
# depth 0.95 本身收敛正常（不像含 Ta 会早崩）。AMIX=0.02 单独即可把畸变点钉回基态，且
# AMIX 是能量中性的（实测 DFT_1105 用 AMIX0.02/depth0.95 的基态能量与 stage2 逐位吻合），
# 故 depth 不动、stage2 B0 仍有效，只需重算 stage3。定向调参条件 B 验证（1105/0607）。
AMIX_ONLY_ALLOYS = {
    'DFT_0307', 'DFT_0502', 'DFT_0508', 'DFT_0548', 'DFT_0576', 'DFT_0607',
    'DFT_0771', 'DFT_0825', 'DFT_0874', 'DFT_1014', 'DFT_1105', 'DFT_1146',
    'DFT_1225', 'DFT_1260', 'DFT_1300', 'DFT_1560',
}

# --- 逐点的费米能级初始猜测 (EFGS) -------------------------------------
#
# EFGS 只是 KGRN 费米能级搜索的初值，与收敛后的能量无关 —— 已实测确认：同一个
# 点用 EFGS = 0.05/0.15/0.40/-0.10（含反号）都收敛到逐位相同的总能量。因此可以
# 自由地逐点设置 EFGS 来帮助难收敛的点起步。
#
# 标定（2026-07-21，stage1 全量运行的 9399 个收敛点）：E_F 相对 muffin-tin 零点
# 主要由原子体积(sws)决定，平均化学价几乎没有解释力（旧的仅-n 模型 R² 仅 0.10，
# 那是 9 点小样本里 n 与压缩端 sws 混杂造成的假象）。改用逐元素成分 + sws 的线性
# 模型，逐点估算：
#     E_F = Σ conc_el · EFGS_EF_COEF[el] + EFGS_SWS_COEF · sws
# 无独立截距 —— 成分分数和为 1，各元素系数自身承载常数并因此可辨识。
# R² = 0.66，符号正确率 0.94（详见 efgs.py）。
EFGS_EF_COEF = {
    'Ti': 1.6282, 'Zr': 1.7772, 'Hf': 1.8161,
    'V': 1.5632, 'Nb': 1.6937, 'Ta': 1.7108,
    'Mo': 1.6501, 'W': 1.6734, 'Re': 1.8571,
}
EFGS_SWS_COEF = -0.5682

# EFGS 在预测 E_F 之上再沿其符号方向外推一个固定余量，即
#     EFGS = E_F + sign(E_F) · EFGS_MARGIN
# 依据 stage1 重投实测：直接取预测 E_F（无余量）能救回约一半原失败点，但剩下的
# 失败集中在 |E_F|<0.03 的近零穿越区 —— EFGS 太靠近 0，费米搜索分不清方向就失败。
# 费米搜索需要从 E_F 外侧向内收敛（config 实测：Ta80W20 E_F≈+0.024，EFGS +0.05/
# +0.10/+0.20 收敛、+0.024 及 0.0 失败），所以把猜测推离 0 至少 EFGS_MARGIN。
# 取固定加法量而非乘法系数：近零点最需要的是绝对余量，乘法对最小的 |E_F| 给不出
# 足够推力；同时加法对本就收敛的大 |E_F| 点更温和。
EFGS_MARGIN = 0.05

# --- Stage3 弹性畸变拟合的离群点守卫 ------------------------------------
# 每个畸变模式采 6 个应变点。偶发某一点 KFCD 落进伪电子态，其能量比干净抛物线高
# 10^3~10^5 meV（实测 bcco3 高达 283000 meV）。pyemto 的 elastic_constants_analyze
# 对 6 点做朴素最小二乘，一个坏点就把 R² 拖到 0。守卫分两步剔除伪点：
#   1. 绝对间隔：真畸变能量在 delta<=0.05 内 < ~0.01 Ry(最硬的 W 也仅 86 meV)，故凡比
#      曲线最低点高出 ELASTIC_OUTLIER_GAP_RY 的点必是伪电子态，直接剔。
#   2. 统计离群：再迭代剔除残差远超同伴(> FACTOR*中位, 且 > FLOOR)的中等离群点。
# 剔完后 **无条件接受**拟合(只要剩 >= ELASTIC_MIN_PTS 点)——R² 低往往只是 c'≈0 的
# 近失稳软合金抛物线本就平坦(同 stage2 浅阱：不能用 R² 判物理性)，其小/负 c' 是真实
# 结果，Born 稳定性由 c' 的符号判断。R² 仅作诊断列输出，不作接受门槛。
ELASTIC_MIN_PTS = 4            # 至少保留这么多点才拟合（<此值判为需重算/无输出）
ELASTIC_OUTLIER_GAP_RY = 0.05  # 高出曲线最低点这么多(Ry)即判伪电子态 (~680 meV)
ELASTIC_OUTLIER_FACTOR = 8.0   # 残差 > 此倍数 x 同伴残差中位 才算统计离群
ELASTIC_OUTLIER_FLOOR_RY = 0.002  # 且残差需 > 此绝对值(~27 meV)才剔，护住干净平坦曲线

CSV_FILE = '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv'

STAGE_DIRS = {
    1: 'stage1_eos_coarse',
    2: 'stage2_eos_fine',
    3: 'stage3_elastic',
}

RESULTS_DIR = 'results'

DEFAULT_LATPATH = '/work/scratch/md88vyxi/workplace/highthroughput-dft-rhea/structures'

COARSE_N_POINTS = 6
COARSE_RANGE = 0.03

FINE_N_POINTS = 11
FINE_RANGE = 0.015
