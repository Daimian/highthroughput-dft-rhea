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
# R² = 0.66，符号正确率 0.94（详见 efgs.py）。EFGS 直接取该预测 E_F，不再乘余量
# 系数：新模型预测的就是真实 E_F，旧代码的 3× 只是补偿旧模型误差用的。
EFGS_EF_COEF = {
    'Ti': 1.6282, 'Zr': 1.7772, 'Hf': 1.8161,
    'V': 1.5632, 'Nb': 1.6937, 'Ta': 1.7108,
    'Mo': 1.6501, 'W': 1.6734, 'Re': 1.8571,
}
EFGS_SWS_COEF = -0.5682

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
