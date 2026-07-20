"""逐合金估算 KGRN 的费米能级初始猜测 EFGS。

背景：pyemto 默认 EFGS=0，而 E_F 相对 muffin-tin 零点的位置随 d 带填充度
单调变化，在平均化学价电子数 n ≈ 4.84 处穿过零点。用固定的 0 会让穿越点
两侧的合金各有一半从错误的方向起步，导致 "EFXMOM: Fermi level not found"。

与 vegard.py 同构：都是按成分做加权平均，再线性映射到一个 KGRN 输入参数。
"""

from config import (ELEMENT_VALENCE, EFGS_SLOPE, EFGS_INTERCEPT, EFGS_SCALE)


def calc_valence_electrons(composition):
    """平均化学价电子数。composition 是 {元素: 原子百分比}。"""
    if not composition:
        raise ValueError("composition must not be empty")
    total = sum(composition.values())
    if abs(total - 100.0) > 0.5:
        raise ValueError(f"concentrations sum to {total}, expected 100")
    return sum((conc / 100.0) * ELEMENT_VALENCE[elem]
               for elem, conc in composition.items())


def estimate_ef(composition):
    """按标定关系估算收敛后的 E_F（Ry，相对 muffin-tin 零点）。"""
    return EFGS_SLOPE * calc_valence_electrons(composition) + EFGS_INTERCEPT


def calc_efgs(composition):
    """该合金应当使用的 EFGS。

    取估算 E_F 的 EFGS_SCALE 倍：与 E_F 同号、幅度更大，让费米搜索从
    E_F 外侧向内收敛。起在错误一侧会失败，这是标定中反复观察到的。
    """
    return EFGS_SCALE * estimate_ef(composition)
