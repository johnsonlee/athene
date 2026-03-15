# Capital Flow Tracking — Credibility Assessment / 全球资金流向追踪可信度评估

**Date / 日期**: 2026-03-15
**Scope / 范围**: `engine/analyzers/capital_flow.py`, `engine/collectors/capital_flow.py`, backtest data

---

## 0. What Problem Does This Solve? / 这个系统到底解决什么问题？

### The intended purpose / 设计意图

The capital flow pipeline exists to answer one question: **"How much position should I hold right now?"**

资金流向管线的存在是为了回答一个问题：**"现在应该持有多少仓位？"**

The evidence is in the roadmap — Signal-to-Position Mapping directly consumes capital flow phases:

证据在 roadmap 中——Signal-to-Position Mapping 直接消费资金流向的阶段标签：

```
capital_flow risk_off phase = half (83% hit rate, +1.91% 22d — contrarian entry)
RFI panic → risk_on = heavy/full (100% hit rate, +2.51% 22d)
neutral → panic = heavy (100% hit rate, +5.50% 22d — post-panic rebound)
```

The system's design intent: **sector trends tell you WHAT to buy (stock selection); capital flows tell you HOW MUCH to buy (position sizing).**

系统的设计意图：**行业趋势告诉你买什么（选股），资金流向告诉你买多少（仓位）。**

### What it actually does / 它实际在做什么

The system produces three things:

系统实际输出三样东西：

1. **A flow diagram** (SVG arrows, risk ↔ safe nodes) — presentation, not decision / 一张流向图——展示，不是决策
2. **Phase labels** per time window (riskon / riskoff / deleverage / outflow / bottom / normal) — this is the actionable output / 每个时间窗口的阶段标签——这才是有决策价值的输出
3. **RFI index** — the driver behind phase labels / RFI 指数——阶段标签的底层驱动

### The gap between goal and method / 目标与手段之间的断层

If the goal is "position sizing", the required input is a binary judgment: **"Are institutions adding or reducing risk exposure?"** There are three paths to answer this:

如果目标是"仓位决策"，需要的输入是一个二元判断：**"机构在加仓还是减仓风险资产？"** 有三条路径：

| Path / 路径 | Method / 做法 | Current state / 现状 |
|---|---|---|
| A. Direct measurement / 直接测量 | ETF shares Δ = creation/redemption / ETF 份额变化 = 申购/赎回 | 6/9 ETFs have real data; SPY does not / 6/9 有真实数据，SPY 没有 |
| B. Price inference / 价格推断 | Risk assets outperform safe = risk-on / 风险资产跑赢避险 = risk-on | The proxy formula is essentially this / 代理公式本质就是这个 |
| C. Multi-signal voting / 综合投票 | VIX + credit spreads + breadth → vote / VIX + 信用利差 + 宽度 → 投票 | macro.py has regime detection, but not fused with RFI / macro.py 已有 regime，但未与 RFI 融合 |

The system claims path A but uses path B for the most important asset (SPY — the world's largest equity pool). **A system that claims to measure "fund flows" but uses "price proxy" for its most important input is self-contradictory.**

系统声称走路径 A，但对最重要的资产（SPY——全球最大的权益资金池）用的是路径 B。**一个声称测量"资金流"的系统，对最重要的输入用"价格代理"，在概念上就自相矛盾。**

### Two honest alternatives / 两条诚实的出路

**Option 1: Redefine as a risk-on/risk-off detector, not a flow meter.**
Drop the "precise dollar flow" narrative. Convert all ETFs (proxy and real) into directional signals (+1/0/-1). Use voting logic instead of summation. The frontend shows a signal dashboard, not dollar-denominated arrows.

**选择 1：重新定义为风险偏好检测器，而非资金流量计。**
放弃"精确美元流量"的叙事。将所有 ETF（代理和真实）统一为方向信号（+1/0/-1），用投票逻辑替代加总逻辑。前端展示信号仪表盘，不画带金额的箭头。

**Option 2: Use only the 6 ETFs with real shares data. Drop SPY/BIL/VGK.**
Sacrifice coverage for credibility. Missing the US equity signal is a real gap, but "no signal" is better than "wrong signal".

**选择 2：只用 6 个有真实份额数据的 ETF，砍掉 SPY/BIL/VGK。**
牺牲覆盖面换取可信度。缺少美股信号确实是硬伤，但"没有信号"比"错误信号"好。

**Regardless of which option is chosen**: the module's output is phase labels (riskon/riskoff/panic) serving position decisions — not dollar figures like "GLD inflow $2.3B". The frontend's precise dollar numbers (`flows.legendInflow5: 'Net inflow >$5B'`) create a false sense of precision when 3/9 of the data is guessed.

**无论选哪条路**：这个模块的输出是阶段标签（riskon/riskoff/panic），服务于仓位决策——而不是"GLD 流入 $2.3B"这样的数字。前端精确到小数点的美元流量（`flows.legendInflow5: '净流入 >$5B'`）在 3/9 数据是猜的情况下，制造了虚假的精确感。

---

## 1. Overall Rating / 总评: 6/10

Useful for **detecting risk appetite direction** (risk-on vs risk-off). Unreliable for **precise dollar quantification**. The core issue: 3 of 9 ETFs (including the most important — SPY) rely on proxy estimation instead of real shares outstanding data.

在**识别风险偏好方向**方面有实际价值。在**精确资金量化**方面不可靠。核心问题：9 个 ETF 中有 3 个（包括最重要的 SPY）依赖代理估算而非真实份额数据。

---

## 2. Data Source Credibility / 数据源可信度

### Real shares data (6/9 ETFs) — High confidence / 真实份额数据——高可信度

| ETF | Asset class / 资产类别 | Source / 数据源 | Reliability / 可靠性 |
|-----|----------------------|----------------|---------------------|
| EWJ | JP Equity / 日本股市 | iShares CSV (product 239665) | High / 高 |
| EEM | EM Equity / 新兴市场 | iShares CSV (product 239637) | High / 高 |
| IBIT | Crypto / 加密货币 | iShares CSV (product 333011) | High (newer, may have gaps) / 高（较新） |
| TLT | US Treasury / 美国国债 | iShares CSV (product 239454) | High / 高 |
| LQD | Corp Bond / 公司债 | iShares CSV (product 239566) | High / 高 |
| GLD | Gold / 黄金 | SPDR Gold Archive CSV | High / 高 |

**Formula (real)**: `daily_fund_flow = Δ(shares_outstanding) × close_price`

This directly measures ETF creation/redemption — real institutional capital allocation decisions.

这是 ETF 申购/赎回的直接衡量，反映真实的机构资金配置。

### Proxy estimation (3/9 ETFs) — Low confidence / 代理估算——低可信度

| ETF | Asset class / 资产类别 | Issue / 问题 |
|-----|----------------------|-------------|
| **SPY** | US Equity / 美国股市 | Most important equity signal has no real data / 最重要的权益信号无真实数据 |
| **BIL** | Cash / 现金 | Money market ETF, proxy only / 货币市场 ETF，仅代理 |
| **VGK** | EU Equity / 欧洲股市 | No free shares outstanding source / 无免费份额数据源 |

**Proxy formula**: `proxy_flow = daily_return × dollar_volume`, confidence = 0.6

**Critical flaws / 核心缺陷**:

- **Conflates price momentum with actual capital movement.** A stock rising 5% and falling 5% (same dollar volume) produce the same magnitude proxy signal — but carry opposite flow meanings.
- **该公式将价格动量与实际资金流动混淆。** 上涨 5% 和下跌 5%（同等成交额）产生同量级代理信号——但含义完全相反。

- **SPY is the world's largest equity pool.** Its proxy estimation directly contaminates risk_net accuracy.
- **SPY 占全球权益配置的核心地位。** 其代理估算直接污染 risk_net 的准确性。

- **Confidence = 0.6 is a label, not a weight.** It is not used in the RFI calculation (`engine/analyzers/capital_flow.py`). Proxy and real flows are summed equally.
- **0.6 置信度仅为标签，未在 RFI 计算中实际加权。** 代理与真实流量等权相加。

---

## 3. Analysis Methodology / 分析方法评估

### RFI (Risk Flow Index) — Sound design, noisy input / 设计合理，输入有噪声

```
RFI = tanh((risk_net - safe_net) / scale)    scale = 5.0
```

**Strengths / 优点**:
- Tanh normalization: smooth, bounded [-1, +1], avoids saturation / tanh 归一化平滑有界，避免饱和
- Both-negative flows (deleveraging) return 0.0 — semantically correct / 双向负流量返回 0.0，语义正确

**Weaknesses / 缺陷**:
- `scale = 5.0` is hand-tuned; no sensitivity analysis / scale = 5.0 手动校准，无敏感性分析
- Proxy and real flows are summed without confidence weighting / 代理与真实流量未按置信度加权
- When SPY proxy is wrong, it can dominate the RFI direction / SPY 代理错误时可能主导 RFI 方向

### Phase classification — Thresholds lack statistical basis / 阶段分类——阈值缺乏统计依据

```python
outflow:    risk_net < -0.5 AND safe_net < -0.5
deleverage: RFI < -0.8 (panic) or RFI < -0.3 AND risk_net < 0
riskon:     RFI > 0.3
bottom:     0 < RFI ≤ 0.3 AND risk_net > 0 AND safe_net < 0
normal:     default
```

Thresholds (-0.5, -0.8, 0.3) are empirical values without grid search or cross-validation.

阈值 (-0.5, -0.8, 0.3) 为经验值，无网格搜索或交叉验证支撑。

---

## 4. Backtest Evidence / 回测证据

### Signals with n > 10 / 样本量 > 10 的信号

| Signal / 信号 | Direction / 方向 | n | 5d hit / 胜率 | 22d hit / 胜率 | 22d avg return / 平均收益 | Max DD / 最大回撤 |
|--------------|-----------------|---|--------------|---------------|-------------------------|------------------|
| capital_flow_phase | risk_off | 16 | 68.8% | 80.0% | +3.11% | 13.72% |
| rfi_acceleration | strong_deteriorating | 15 | 46.7% | 84.6% | +3.67% | 6.33% |
| rfi_acceleration | strong_improving | 14 | 71.4% | 78.6% | +2.38% | 5.07% |
| capital_flow_phase | risk_on | 13 | 53.8% | 75.0% | +2.13% | 13.72% |

### Key findings / 关键发现

1. **22d is far more effective than 5d.** All major signals show 22d hit rate > 75% vs 5d at 50-70%. Capital flows are a **medium-term trend signal**, not suitable for short-term trading.
2. **22d 视角显著优于 5d。** 所有主要信号 22d 胜率 > 75%，5d 仅 50-70%。资金流向是**中期趋势信号**，不适合短线。

3. **Panic signals are most valuable.** `mild_risk_off → panic` (n=2): 22d avg +11.06%. `panic → risk_on` (n=1): 22d +10.05%. But sample sizes are tiny.
4. **恐慌信号最有价值。** `mild_risk_off → panic` (2 次) 22d +11.06%；`panic → risk_on` (1 次) 22d +10.05%。但样本极小。

5. **`risk_off → mild_risk_off` is a trap.** 2 events, 5d -5.49%, 22d -0.14%. Easing risk-off ≠ safe.
6. **`risk_off → mild_risk_off` 是陷阱。** 2 次信号，5d -5.49%，22d -0.14%。风险缓和 ≠ 安全。

7. **`risk_on → mild_risk_off` is also a trap.** 3 events, 22d hit rate 33.3%, avg -0.40%.
8. **`risk_on → mild_risk_off` 也是陷阱。** 3 次，22d 胜率 33.3%，-0.40%。

### Statistical reliability warnings / 统计可靠性警告

- **Severely insufficient sample sizes.** Largest group has only 16 events; most have < 5. None meet academic significance threshold (n ≥ 30).
- **样本量严重不足。** 最大组仅 16 个事件，多数 < 5 个，均不具备统计显著性 (n ≥ 30)。

- **No out-of-sample validation.** All results are in-sample backtests — overfitting risk.
- **无样本外验证。** 全部为回看测试，可能过拟合。

- **Circular validation.** Phase classification thresholds were set on the same dataset. The backtest naturally looks good.
- **循环验证。** 阶段分类阈值基于同一数据集设定，回测自然表现良好。

- **Single benchmark.** Only SPY forward returns tested. Predictive power for other assets unknown.
- **单一基准。** 仅测试 SPY 前瞻收益，未验证对其他资产的预测能力。

---

## 5. Structural Limitations / 结构性局限

### Incomplete coverage / 覆盖不完整

9 ETFs cover only a subset of global asset classes. Missing:
- Commodities beyond gold / 大宗商品（除黄金外）
- REITs / 房地产
- EM bonds / 新兴市场债券
- China/India standalone equity / 中国/印度单独权益

9 个 ETF 仅覆盖部分全球资产类别。

### ETF shares ≠ all capital flows / ETF 份额 ≠ 全部资金流

ETF creation/redemption only reflects capital allocation through the ETF channel. Institutions can allocate via:
- Futures/options / 期货/期权
- Direct stock holdings / 直接持股
- OTC swaps / 场外掉期
- Alternatives / 另类投资

ETF 申购/赎回仅反映 ETF 渠道的资金配置，不包含上述渠道。

### Theoretical flaws in proxy method / 代理方法的理论缺陷

`proxy_flow = return × dollar_volume` assumes "volume direction = capital direction", but:
- High-volatility days amplify volume without implying net inflows / 高波动日成交量放大不代表净流入
- Short selling also generates volume / 做空同样产生成交量
- ETF market-maker arbitrage inflates volume without directional meaning / 做市商套利增加成交量但无方向含义

### Misleading frontend visualization / 前端可视化的误导性

SPY/BIL/VGK nodes appear **nearly identical** to real-data nodes (only dashed borders distinguish them). Arrows imply precise dollar flows, but for proxied ETFs the magnitudes are estimated. Average users are unlikely to notice the difference.

SPY/BIL/VGK 节点与真实数据节点**外观接近**（仅虚线边框区分），箭头暗示精确美元流量，但代理 ETF 的数值是估算的。普通用户很可能不会注意到差异。

---

## 6. Credible vs Non-Credible Uses / 可信 vs 不可信用途

### Credible (recommended) / 可信（推荐）

- Detecting extreme risk events (panic/deleverage phases) — small sample but strong signal
- 识别极端风险事件（恐慌/去杠杆阶段）——样本小但信号强

- Trend direction over 22d+ time horizons
- 22d+ 时间框架的趋势方向判断

- Relative flow comparison between real-shares ETFs (e.g. GLD vs TLT)
- 真实份额 ETF 之间的相对流量比较（如 GLD vs TLT）

- Confirming indicator alongside sector trends (not standalone)
- 与行业趋势组合使用的辅助确认信号（非独立信号）

### Not credible (avoid) / 不可信（应避免）

- Precise dollar flow numbers for SPY/BIL/VGK
- 基于 SPY/BIL/VGK 的精确美元流量数字

- 5d short-term trading decisions
- 5d 短线交易决策

- Standalone position sizing based solely on RFI
- 单独依赖 RFI 做仓位调整

- Transition signals `risk_off → mild_risk_off` and `risk_on → mild_risk_off` (backtested as traps)
- 过渡信号 `risk_off → mild_risk_off` 和 `risk_on → mild_risk_off`（回测显示为陷阱）

---

## 7. Recommendations / 改进建议

| Priority / 优先级 | Recommendation / 建议 | Impact / 预期影响 |
|---|---|---|
| **P0** | Resolve the identity crisis: decide whether this is a flow meter or a risk-appetite detector. Reframe the frontend accordingly. / 解决身份危机：明确这是资金流量计还是风险偏好检测器，相应调整前端叙事。 | Eliminates the core credibility gap / 消除核心可信度问题 |
| **P0** | Confidence-weight RFI inputs: `risk_net = Σ(flow_i × conf_i) / Σ(conf_i)` / RFI 按置信度加权 | Reduces proxy data contamination / 降低代理数据污染 |
| **P1** | Publish dual-tier signals: Tier 1 (6 real ETFs only) + Tier 2 (all 9) / 发布双层信号 | Lets users choose trust level / 让用户选择信任级别 |
| **P1** | Grid search RFI scale (2.0–10.0) optimizing 22d hit rate / RFI scale 网格搜索 | Validates threshold reliability / 验证阈值可靠性 |
| **P2** | Find free SPY/VGK shares outstanding sources (SEC filings, ETF.com API) / 寻找 SPY/VGK 免费份额数据源 | Closes the biggest data gap / 消除最大数据缺口 |
| **P2** | Out-of-sample validation: train on 2020–2023, test on 2024–2026 / 样本外验证 | Assesses overfitting / 评估过拟合程度 |
| **P3** | Add commodity ETFs (DBC/USO) and REITs (VNQ) / 添加大宗商品和 REIT ETF | Broadens coverage / 扩大覆盖面 |

---

## 8. Conclusion / 结论

The system's architecture is sound (tanh RFI, multi-window analysis, phase classification), but constrained by three fundamental issues:

系统的架构设计合理（tanh RFI、多窗口分析、阶段分类），但受限于三个根本问题：

1. **Identity crisis.** It claims to measure fund flows but uses price proxies for the most important asset. It needs to decide: is it a flow meter or a risk-appetite detector?
1. **身份危机。** 它声称测量资金流，却对最重要的资产使用价格代理。它需要决定：自己是资金流量计还是风险偏好检测器？

2. **Data mixing without weighting.** Real shares + proxy estimates are summed equally. SPY — the noisiest input — has the same weight as the cleanest.
2. **数据混合未加权。** 真实份额与代理估算等权相加。最嘈杂的输入（SPY）与最干净的权重相同。

3. **Insufficient evidence.** Maximum 16 backtest events — no statistically robust conclusions possible. Compare: sector trends have 1,134 events.
3. **证据不足。** 最多 16 个回测事件，无法得出统计稳健的结论。对比：行业趋势有 1,134 个事件。

**Recommended positioning / 建议定位**: Use capital flows as a **confirming indicator** (alongside sector trends), not a **standalone decision signal**. The phase labels (riskon/riskoff/panic) are the valuable output — not the dollar figures on the flow diagram.

将资金流向作为**辅助确认信号**（与行业趋势组合），而非**独立决策信号**。阶段标签（riskon/riskoff/panic）才是有价值的输出——不是流向图上的美元数字。
