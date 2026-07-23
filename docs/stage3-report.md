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
| C11 | 149 | 237 | 339 |
| C12 | 96 | 119 | 144 |
| C44 | 48 | 65 | 89 |
| B | 118 | 160 | 207 |
| G(VRH) | 41 | 61 | 88 |
| E | 109 | 161 | 229 |

ν 中位 0.33，B/G 中位 2.56。**Born 力学稳定 1586/1598（99.2%）**，12 个富 Ti/Hf/Zr 近 Bain 失稳（C′≲0，含 g118 下修 C44 后显现的 5 个软合金 0228/0711/0945/0998/1188）；**Pugh 韧性（B/G>1.75）1592/1598（≈100%）**——难熔 BCC HEA 的典型。（统计基于 g118 复核后的最终全库，见 §5.1。）

## 4.1 Born 失稳的成分规律（全库检验）

12 个 Born 失稳合金**全部是 C′≤0**（四方剪切/Bain 失稳；C44、C11+2C12 均正常）。对全库 1598 做了成分-弹性回归检验，结论分三层——一条经全库验证的主规律、一条对早期归纳的**纠正**、一条精修：

**① 主轴 C′–VEC：单调、无反例（强）。** C′ 中位随价电子浓度 VEC 单调上升（4.0–4.2 区 16 → 5.5–6.1 区 136 GPa），且**所有失稳都落在 VEC≤4.5**——VEC>4.5 的 1284 个合金**零失稳**，全库无反例。全库 C′ 最低的 10 个也全在 VEC≤4.48 的低-VEC 角。这直接印证 C′ 由 d 带成键-反键填充决定：低填充 → 四方剪切软 → BCC 沿 Bain 失稳。（VEC：Ti/Zr/Hf=4，V/Nb/Ta=5，Cr/Mo/W=6，Re=7。）

**② 纠正：「第 4 族富集」不是独立判据。** VEC≤4.5 是**必要非充分**——该池 250 个里仅 12 个（5%）失稳。池内对比失稳 vs 稳定，**第 4 族(Ti+Zr+Hf)占比 69% vs 67%，几乎不分**。低 VEC 里有大量很稳的第 4 族富集合金，比失稳的更低 VEC、更富第 4 族（如 Ti48Zr42Nb5Ta5：VEC4.10、第 4 族 90%、**C′=+11.9 稳**；对比 Hf40Ta45 系 VEC4.45 却 C′<0）。故不能用"第 4 族多"判失稳。

**③ 精修：真正的第二轴是 Hf 含量。** 低-VEC 池内逐元素看分离度，只有 **Hf 一枝独秀（失稳均值 39% vs 稳定 19%，唯一 2× 差）**；Ti 反而失稳组更少（15% vs 25%），Nb 是明显稳定剂（2% vs 12%，既抬 VEC 又稳 BCC）。**修正规律 = 低 VEC(≤4.5) 且 Hf 富集(常 Hf≥40) 才真正越过失稳边界**。物理上三种第 4 族均 HCP 基态、0 K BCC 亚稳，但 Hf 富集 BCC 的四方剪切最软（Hf/Zr 强 ω/β 失稳倾向 + Hf 5d²/4f 半芯）——此为数据驱动观察，微观机理待纯元素/二元 C′ 对照坐实。

**数据可信度**：12 个失稳全部 C′≤0、C44 正常、拟合 R² 高无异常剔除点 → **物理真实的单相 BCC 不稳信号，非坏数据**；其中 5 个（0228/0711/0945/0998/1188）是 §5.1 的 g118 基态修正把虚高 C44 拉回后才显现——纠正电子结构后浮现的是物理自洽的低-VEC/Hf 失稳，反证修正正确。这些合金 0 K 单相 BCC 不稳，实际可能多相/马氏体/高温亚稳，用作单相 BCC 弹性数据时应标注或剔除。

## 5. 收敛调参（本轮建立，config `_params_for` 分档）

弹性畸变**破坏立方对称、比 EOS 更难收敛**，逐合金存在狭窄的"畸变收敛窗口"。全库靠离群守卫 + 分档 depth/AMIX/IEX 达到 100%：

- **离群守卫**（`elastic_analysis`）：畸变 6 点里剔除落进伪电子态的离群点（绝对间隔 + 统计），≥4 点即拟合，接受负 C′。单此一项 84→92%。
- **depth 是收敛主杠杆，且非能量中性**（改 C′）：Ta+V 富集角要 depth0.70，一般含 Ta 要 0.80，纯难熔金属 0.95 即可。
- **⚠️ depth 与含 Hf 的 EOS 互斥**：depth≤0.90 腐蚀富 Hf 的 EOS（伪膨胀软态）。故含 Hf 走**混合 depth**：B0/sws0 用 depth0.95（正确 EOS），畸变用能收敛的最浅 depth（C'@浅 + B0@0.95，带注脚）。
- **AMIX 选电子 basin（能量中性）**：慢 AMIX 钉单一 basin。**高 Hf 散射角**用 **AMIX=0.01**（比 0.02 更慢）把 12 点钉进基态。但慢 AMIX **不是万能药**——对富 V 合金反而致命（§5.1）。
- **IEX（原子求解器 XC）**：DFT_0198(Hf2Ta90) 的 Hf 4f14 Dirac 原子解在默认 **IEX=4(PW92)** 下振荡发散（ATOMC "Too few iterations"，depth/dirac_niter/sofc/lmaxh 全无效；纯 Ta100 同参数收敛 → 病在痕量 Hf 的原子 XC 势）。换 **IEX=3(VWN)** 干净收敛（与 6=PZ 逐位相同，即 PW92 应给的 LDA 答案），与全库 LDA-SCF 方法学一致，无需改成分。

分档（`_params_for` 优先级从高到低）：`D70_ALLOYS`(18,depth0.70) · `HF_SCATTER_A01_ALLOYS`(4,depth0.80+AMIX0.01) · Ta≥30/`DEEP_TA_ALLOYS`(depth0.80) · `HF_D80_ALLOYS`(33,depth0.80混合) · `MIXED_HF_ALLOYS`(60,depth0.90混合) · `AMIX_ONLY_ALLOYS`(16,depth0.95) · `IEX_OVERRIDE={DFT_0198:3}`。

**KGRN IEX 取值表**（二进制 strings 提取，0 索引）：0 Barth-Hedin · 1 X-Alpha · 2 Barth-Hedin-Janak · 3 VWN · **4 Perdew-Wang PW92（默认，LDA）** · 5 Wigner · 6 Perdew-Zunger · **7 PBE（GGA）** · 8 Local-Airy-Gas · 9 PBEsol。pyemto 不把 xc 耦合到 iex：KGRN SCF 在 IEX(LDA) 下做，KFCD 再上 xc=PBE 修正。

## 5.1 AMIX 的两个作用与富 V 的收敛悖论

AMIX 是 SCF 迭代间的**线性电荷/势混合系数**：$n_{\text{in}}^{(k+1)}=(1-\text{AMIX})\,n_{\text{in}}^{(k)}+\text{AMIX}\,n_{\text{out}}^{(k)}$，每步只采纳新密度的一小部分。它有**两个独立作用**，哪个占主导取决于合金电子结构——这解释了一个悖论：**同样是「放慢 AMIX」，对 Hf 是解药、对富 V 却是毒药**。

- **作用一 · 选 basin（对 Hf 有利）**：Hf40 散射合金是**双稳**（基态 vs Hf 半芯激发态能量相近），SCF *本身能收敛*，只是会跳错坑。慢 AMIX = 每步只挪一点点 = **不离开初始猜测（重叠原子势≈基态）所在的 basin**，于是把 12 个畸变点全钉进基态。这里 AMIX 纯是"basin 选择器"，快慢都收敛。
- **作用二 · 能否在迭代预算内到达自洽（对富 V 致命）**：富 V 合金（V 26–40，常配 Ti/Zr）的 **E_F 正压在又高又陡的 d-态密度上**（BCC 群 5 的 V d 电子少，E_F 在 d 峰陡坡；掺 Ti/Zr 进一步把 E_F 推上峰）。势稍动，尖峰就在 E_F 两侧扫过 → 填充数剧烈振荡 = **charge sloshing**；畸变还会把尖峰**劈裂**（类能带 Jahn–Teller），使畸变胞的 E_F 定位比立方胞更难。这种刚性系统的 AMIX 有个 **Goldilocks 窗口**：太快→过冲发散；**太慢（0.01）→ 每步几乎不修正，在 NITER 迭代上限内根本走不到自洽点**，卡在半收敛、内部不自洽的密度上，E_F 附近 DOS 仍是锯齿状，矩方法费米搜索 `EFXMOM` 找不到自洽 E_F → 报 **"Fermi level not found"**。production 的**默认 AMIX**恰在此窗口内 → 12/12 收敛。

**为什么"更慢"不是万能**：线性混合收敛率 $\sim(1-\alpha J)$，尖 DOS 让 SCF 映射 Jacobian $J$ 的有效本征值很大；把 $\alpha$ 调小**不改善条件数**，只是把一切拖慢、在迭代耗尽前没收敛。对症的杠杆是 **Fermi 展宽/电子温度（`EFMIX`↑ 或 smearing）抹平尖峰**、或 **Kerker/Broyden 混合**，而非更小的线性 α。

**实证（2026-07-23，job 53541052 / `stage3_v9`）**：9 个富 V 合金在 depth0.95+AMIX0.01 下仅 6/108 点收敛（余皆 `EFXMOM: Fermi level not found`）。但它们**根本不需要重算**——production（默认 AMIX）的拟合 **R²=1.000、零剔除点、Born 稳定**；其原始"同-depth gap 0.2–3.4 Ry"只是**刚性能量零点平移**（12 点整体偏移但在同一 basin），对曲率 C′/C44 精确抵消。**由此确立健康判据 = 拟合质量（R²、剔除点数），而非原始 energy-gap**——raw gap 会把无害的刚性平移误报成病态；只有 Hf 那种*点依赖*的跳基（散射→剔除点↑/R²↓→C44 虚高）才真正污染弹性常数。9 个已按 production 值并入，全库达 **1598/1598 = 100%**。

## 6. 已知局限
- **含 Hf 合金 C′ 的 depth 失配**（C'@0.70/0.80/0.90 + B0@0.95）：源自价 d 带的小 depth 漂移，剪切里半芯基本抵消，量级可控但非零。
- 富 Nb 合金 stage2 的 B0 偏软 ~15%，传导到其 C11/C12（见 `stage2-summary-report.md` §5）。
- 12 个 C′≲0 为**低 VEC(≤4.5)+ Hf 富集**的近 Bain 失稳（成分规律与全库检验见 §4.1），物理合理（非坏拟合）；其中 5 个（0228/0711/0945/0998/1188）在 g118 把虚高 C44 下修到基态后才显现真实失稳。

---

[^fn1963]: G. A. Featherston and J. R. Neighbours, "Elastic Constants of Tantalum, Tungsten, and Molybdenum," *Phys. Rev.* **130**, 1324 (1963). W 单晶 298 K：C11 = 522.4, C12 = 204.4, C44 = 160.8 GPa。

[^hill]: R. Hill, "The Elastic Behaviour of a Crystalline Aggregate," *Proc. Phys. Soc. A* **65**, 349 (1952)（Voigt-Reuss-Hill 平均）。

[^pugh]: S. F. Pugh, "Relations between the elastic moduli and the plastic properties of polycrystalline pure metals," *Philos. Mag.* **45**, 823 (1954)（B/G > 1.75 判为韧性）。
