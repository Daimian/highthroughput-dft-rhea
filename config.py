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
    setups={'Hf': '4f5d6s'},   # Hf 的 4f14 进入价带，默认为 Hf_5d6s
    # efgs 不在这里 —— 它逐合金计算，见 efgs.py 与下面的常量。
)

# --- 逐合金的费米能级初始猜测 (EFGS) -----------------------------------
#
# 化学价电子数。注意这是**化学价**，不是 KGRN 输入里的价带电子数：
# 上面的 setups 让 Hf 把 4f14 放进价带（KGRN 里 Hf 算 18 个电子），
# 但与 E_F 位置相关的是化学价 4。下面的拟合就是用这一列做的。
ELEMENT_VALENCE = {
    'Ti': 4, 'Zr': 4, 'Hf': 4,
    'V': 5, 'Nb': 5, 'Ta': 5,
    'Mo': 6, 'W': 6,
    'Re': 7,
}

# 实测标定：9 个合金在各自压缩端收敛后的 E_F 与平均化学价电子数 n 的关系
#     E_F ≈ EFGS_SLOPE * n + EFGS_INTERCEPT      (R² = 0.990, 残差 RMS 0.0046 Ry)
# 零点在 n = 4.835：n 低于它 E_F 为负（Ti/Zr/Hf 富集），高于它为正（Ta/Mo/W/Re 富集）。
EFGS_SLOPE = 0.0742
EFGS_INTERCEPT = -0.3587

# EFGS 取与 E_F 同号、幅度更大的值，从外侧向内收敛才稳定。
# 依据：Hf72Ta26Mo2 (E_F=-0.041) 在 -0.10/-0.20 收敛、0.0 失败；
#       Ta80W20     (E_F=+0.024) 在 +0.05/+0.10/+0.20 收敛、0.0 及负值全失败。
EFGS_SCALE = 3.0

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
