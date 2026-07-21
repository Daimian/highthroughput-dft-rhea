"""逐点估算 KGRN 的费米能级初始猜测 EFGS。

背景：pyemto 默认 EFGS=0，而 E_F 相对 muffin-tin 零点主要随原子体积(sws)变化，
成分是次要修正。用固定的 0 会让一部分合金从错误的方向起步，导致
"EFXMOM: Fermi level not found"。EFGS 只是初值、不影响收敛后的能量（已实测确认），
所以逐点按体积设置最合理。

与 vegard.py 同构：都按成分做加权，再叠加一个体积线性项，映射到 KGRN 输入参数。
标定见 config.py（stage1 全量 9399 个收敛点，逐元素成分 + sws，R²=0.66，
符号正确率 0.94）。
"""

from config import EFGS_EF_COEF, EFGS_SWS_COEF


def estimate_ef(composition, sws):
    """估算该成分在给定 sws 下收敛后的 E_F（Ry，相对 muffin-tin 零点）。

    composition 是 {元素: 原子百分比}；sws 是该点的 Wigner-Seitz 半径（Bohr）。
    """
    if not composition:
        raise ValueError("composition must not be empty")
    total = sum(composition.values())
    if abs(total - 100.0) > 0.5:
        raise ValueError(f"concentrations sum to {total}, expected 100")
    ef_comp = sum((conc / 100.0) * EFGS_EF_COEF[elem]
                  for elem, conc in composition.items())
    return ef_comp + EFGS_SWS_COEF * sws


def calc_efgs(composition, sws):
    """该合金在该 sws 点应使用的 EFGS。

    直接取预测的 E_F 作为初值（不再乘余量系数）：新模型预测的就是收敛后的真实
    E_F，把费米搜索直接放到那里起步即可。
    """
    return estimate_ef(composition, sws)
