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
    # 以下四项共同解决 "EFXMOM: Fermi level not found"。它们是组合起效的：
    # 在 Hf72Ta26Mo2（Ta+Hf 占 98%，数据集中最难的成分之一）的最压缩点上，
    # 单独放宽任何一项都不够，且 depth 保持 1.0 时即便其余三项到位仍然失败。
    depth=0.95,          # 能量围道深度（Ry），pyemto 默认 1.0
    amix=0.02,           # SCF 混合步长，默认 0.05
    nx=9,                # 费米能级搜索窗口点数，默认 5
    setups={'Hf': '4f5d6s'},   # Hf 的 4f14 进入价带，默认为 Hf_5d6s
)

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
