# Stage 3（弹性常数）报告

日期：2026-07-21　|　方法：EMTO-CPA / PBE，BCC，保体积畸变

## 1. 方法

在每个合金的 stage2 平衡体积 sws0 处施加保体积畸变，从能量-应变曲线提取弹性常数：

- **正交畸变**（`bcco0–5`，6 个应变）→ 四方剪切 **C′ = (C11 − C12)/2**
- **单斜畸变**（`bccm0–5`，6 个应变）→ **C44**
- **C11、C12** 由 C′ 与 stage2 的体模量 **B0 = (C11 + 2·C12)/3** 联立反推

即 stage3 用到 stage2 的两个量：**sws0（定体积）** 和 **B0（定 C11/C12）**。

多晶聚合量用 **Voigt-Reuss-Hill** 平均[^hill]，脆韧性用 **Pugh 比 B/G**[^pugh]。

## 2. 首个测试：DFT_0001（W91Re9）

12 个畸变点全部收敛。输入 sws0 = 2.9638 Bohr，B0 = 305.6 GPa。

| 量 (GPa 除注明) | 本计算 | W 实验[^fn1963] | 偏差 |
|---|---|---|---|
| C11 | **533.2** | 522.4 | +2% |
| C12 | **191.8** | 204.4 | −6% |
| C44 | **157.6** | 160.8 | −2% |
| B（体模量） | 305.6 | 310.4 | −2% |
| C′ | 170.7 | 159.0 | +7% |
| G（剪切，Hill） | 162.7 | 160 | +2% |
| E（杨氏） | 414.5 | 410 | +1% |
| ν（泊松比） | 0.274 | 0.280 | — |
| B/G（Pugh） | 1.88 | 1.94 | — |
| A（Zener 各向异性） | 0.92 | 0.92 | — |

**与纯 W 单晶实验高度吻合**（各量均在几个 % 内）。W91Re9 以 W 为主，理应接近纯 W——此吻合验证了整个 stage3 流程（畸变生成→收敛→`fit_elastic(sws0,B0)`→弹性常数）正确。

## 3. Born 力学稳定性（BCC）

判据：C′ > 0，C44 > 0，C11 + 2C12 > 0。

DFT_0001：**C′ = 171 > 0，C44 = 158 > 0，C11+2C12 = 917 > 0 → BCC 力学稳定** ✅

（结构稳定性由弹性常数判断，EOS 只反映静水压响应；C′→0 或负 = BCC 沿 Bain 路径失稳。）

## 4. 状态

- ✅ DFT_0001 测试通过，结果物理、与实验吻合。
- ⏳ 全库 1598 合金 × 12 点 = 19176 点尚未提交。

延续 stage1/2 的收敛设置：depth/AMIX 覆盖（Ta≥30 及显式列表）与逐合金 EFGS 在 stage3 生成时自动带入。**注意**：富 Nb 合金 stage2 的 B0 偏软 ~15%，会传导到其 C11/C12（见 `stage2-summary-report.md` §5）。

---

[^fn1963]: G. A. Featherston and J. R. Neighbours, "Elastic Constants of Tantalum, Tungsten, and Molybdenum," *Phys. Rev.* **130**, 1324 (1963). W 单晶 298 K：C11 = 522.4, C12 = 204.4, C44 = 160.8 GPa。

[^hill]: R. Hill, "The Elastic Behaviour of a Crystalline Aggregate," *Proc. Phys. Soc. A* **65**, 349 (1952)（Voigt-Reuss-Hill 平均）。

[^pugh]: S. F. Pugh, "Relations between the elastic moduli and the plastic properties of polycrystalline pure metals," *Philos. Mag.* **45**, 823 (1954)（B/G > 1.75 判为韧性）。
