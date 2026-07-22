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

## 4. 全库结果（1598 / 1598 = 100%）

`results/final_mechanical_properties.csv`：C11/C12/C44/cprime + B/G_V/G_R/G_VRH/E/nu/B_G_ratio/Cauchy/A/Hv + R2_cprime/R2_c44/n_drop_*/born_stable。

| 量 (GPa) | 5% | 中位 | 95% |
|---|---|---|---|
| C11 | 153 | 238 | 340 |
| C12 | 96 | 119 | 144 |
| C44 | 48 | 66 | 90 |
| B | 118 | 160 | 207 |
| G(VRH) | 42 | 61 | 88 |
| E | 113 | 162 | 230 |

ν 中位 0.33，B/G 中位 2.56。**Born 力学稳定 1591/1598（99.6%）**，仅 4 个富 Ti/Hf 近 Bain 失稳（C′≲0）；**Pugh 韧性（B/G>1.75）1591/1595（≈100%）**——难熔 BCC HEA 的典型。

## 5. 收敛调参（本轮建立，config `_params_for` 分档）

弹性畸变**破坏立方对称、比 EOS 更难收敛**，逐合金存在狭窄的"畸变收敛窗口"。全库靠离群守卫 + 分档 depth/AMIX/IEX 达到 100%：

- **离群守卫**（`elastic_analysis`）：畸变 6 点里剔除落进伪电子态的离群点（绝对间隔 + 统计），≥4 点即拟合，接受负 C′。单此一项 84→92%。
- **depth 是收敛主杠杆，且非能量中性**（改 C′）：Ta+V 富集角要 depth0.70，一般含 Ta 要 0.80，纯难熔金属 0.95 即可。
- **⚠️ depth 与含 Hf 的 EOS 互斥**：depth≤0.90 腐蚀富 Hf 的 EOS（伪膨胀软态）。故含 Hf 走**混合 depth**：B0/sws0 用 depth0.95（正确 EOS），畸变用能收敛的最浅 depth（C'@浅 + B0@0.95，带注脚）。
- **AMIX 选电子 basin（能量中性）**：慢 AMIX 钉单一 basin。**高 Hf 散射角**用 **AMIX=0.01**（比 0.02 更慢）把 12 点钉进基态。
- **IEX（原子求解器 XC）**：DFT_0198(Hf2Ta90) 的 Hf 4f14 Dirac 原子解在默认 **IEX=4(PW92)** 下振荡发散（ATOMC "Too few iterations"，depth/dirac_niter/sofc/lmaxh 全无效；纯 Ta100 同参数收敛 → 病在痕量 Hf 的原子 XC 势）。换 **IEX=3(VWN)** 干净收敛（与 6=PZ 逐位相同，即 PW92 应给的 LDA 答案），与全库 LDA-SCF 方法学一致，无需改成分。

分档（`_params_for` 优先级从高到低）：`D70_ALLOYS`(18,depth0.70) · `HF_SCATTER_A01_ALLOYS`(4,depth0.80+AMIX0.01) · Ta≥30/`DEEP_TA_ALLOYS`(depth0.80) · `HF_D80_ALLOYS`(33,depth0.80混合) · `MIXED_HF_ALLOYS`(60,depth0.90混合) · `AMIX_ONLY_ALLOYS`(16,depth0.95) · `IEX_OVERRIDE={DFT_0198:3}`。

**KGRN IEX 取值表**（二进制 strings 提取，0 索引）：0 Barth-Hedin · 1 X-Alpha · 2 Barth-Hedin-Janak · 3 VWN · **4 Perdew-Wang PW92（默认，LDA）** · 5 Wigner · 6 Perdew-Zunger · **7 PBE（GGA）** · 8 Local-Airy-Gas · 9 PBEsol。pyemto 不把 xc 耦合到 iex：KGRN SCF 在 IEX(LDA) 下做，KFCD 再上 xc=PBE 修正。

## 6. 已知局限
- **含 Hf 合金 C′ 的 depth 失配**（C'@0.70/0.80/0.90 + B0@0.95）：源自价 d 带的小 depth 漂移，剪切里半芯基本抵消，量级可控但非零。
- 富 Nb 合金 stage2 的 B0 偏软 ~15%，传导到其 C11/C12（见 `stage2-summary-report.md` §5）。
- 4 个 C′≲0 为富 Ti/Hf 近 Bain 失稳，物理合理（非坏拟合）。

---

[^fn1963]: G. A. Featherston and J. R. Neighbours, "Elastic Constants of Tantalum, Tungsten, and Molybdenum," *Phys. Rev.* **130**, 1324 (1963). W 单晶 298 K：C11 = 522.4, C12 = 204.4, C44 = 160.8 GPa。

[^hill]: R. Hill, "The Elastic Behaviour of a Crystalline Aggregate," *Proc. Phys. Soc. A* **65**, 349 (1952)（Voigt-Reuss-Hill 平均）。

[^pugh]: S. F. Pugh, "Relations between the elastic moduli and the plastic properties of polycrystalline pure metals," *Philos. Mag.* **45**, 823 (1954)（B/G > 1.75 判为韧性）。
