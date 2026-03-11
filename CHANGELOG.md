# Changelog

### v20: Alpha Model (Three-Factor Multiplicative)

Parallel alpha scoring model based on three investment axioms: (1) past trends predict future via cycle position, (2) capital is zero-sum, (3) cycles are continuous. Replaces additive weighted-sum approach with multiplicative `Score = VM × EV × Timing / K` where any zero factor kills the score.

**Key changes from v19:**
- **Multiplicative three-factor model**: `alpha_score = (VM × EV × Timing) / K` where K=5000. All three factors must be present — multiplicative structure means a zero in any factor produces zero score, unlike additive models where weak factors get averaged away.
- **Growth-adjusted VM**: `vm = pe_base × growth_adj × 0.6 + fcf_yield_score × 0.4`. Uses forward PE with trailing PE fallback. Growth adjustment `growth_adj = 0.5 + earn_growth_score / 100` ∈ [0.5, 1.5] — high-growth stocks get PE premium, declining earnings get PE discount. PB removed (anti-signal for tech, IR -0.17 for growth stocks).
- **Direction-multiplied EV**: `ev = visibility × direction_multiplier` where `visibility = 0.30 × quality + 0.70 × growth` (same as legacy EV). Direction multiplier `= 0.85 + 0.65 × (0.5 × analyst_revision + 0.5 × growth_direction)` ∈ [0.2, 1.5]. Positive analyst revisions + improving growth → EV amplified up to 1.5×. Negative revisions + declining growth → EV suppressed to 0.2×.
- **Reversal-gated timing**: `timing = reversal × (α + (1-α) × cycle_upside / 100)` where `cycle_upside = 100 - trend_score` (strong uptrend = late cycle = LESS future upside). Reversal=0 → timing=0 regardless of cycle position, preventing value traps. α=0.5 (to be calibrated from IC).
- **Reversal signal detection**: Four technical reversal signals computed in `technical.py`: MACD histogram rate-of-change (35%), KDJ golden cross (30%), RSI oversold recovery (25%), pullback proximity to SMA support (10%). Composite `reversal_score` (0-100) used by alpha model timing factor.
- **Parallel architecture**: Alpha model runs alongside legacy additive model — NOT a replacement. Both `composite_score` (legacy) and `alpha_score` (new) exported for comparison and IC validation. Legacy model unchanged.
- **K=5000 normalization**: Calibrated to realistic joint max (~500K) not theoretical max (1.5M). Produces scores in practical [0, 100] range.
- **Alpha threshold**: Scores below 30 considered not worth holding (to be calibrated from backtest).

**Model design principles:**
- **Multiplicative = AND logic**: Stock must have attractive valuation AND visible earnings AND favorable timing. Additive models allow a strong CT to compensate for terrible VM — multiplicative doesn't.
- **Cycle inversion**: `cycle_upside = 100 - trend` means the model is contrarian on timing — it looks for cycle upside in beaten-down sectors, not momentum continuation. But reversal gate prevents catching falling knives.
- **DC excluded from scoring**: Downside Control is a position-sizing factor, not a stock quality factor. A volatile biotech with great VM/EV/Timing should score high but be sized small. Legacy model conflated quality with risk.

**Files**: `engine/scorer/alpha_model.py` (new), `engine/analyzers/technical.py`, `engine/config.py`, `engine/scorer/factor_model.py` (unchanged), `engine/analyze.py`, `engine/main.py`, `engine/exporters/json_exporter.py`

### v19: Market Timing Integration (current)

Synthesize timing signals into a `market_timing_score` (0-100) that influences stock scoring via dimension weight adjustment and composite penalty in unfavorable markets. Addresses the problem where rich market timing signals (RFI, leading indicators, macro regime) barely influenced stock scores — only a ±5% CT/DC shift from macro regime existed.

**Key changes from v18:**
- **Market timing module**: New `engine/analyzers/market_timing.py` combines 5 signals: RFI level (35%), macro regime (25%), credit spread velocity (20%), breadth thrust (15%), VIX term structure (5%). Each signal mapped to 0-100 via `metric_score()` breakpoints, then weighted-averaged into `market_timing_score`.
- **Timing zones**: favorable (≥62), neutral (≥45), unfavorable (≥30), adverse (<30). Zone determines weight shift magnitude and penalty level.
- **Timing-adjusted weights**: Replaces old ±5% `REGIME_WEIGHT_SHIFT` with up to ±10% CT/DC shift based on timing score. Favorable → CT 44%/DC 26%, adverse → CT 34%/DC 36%. `TimingResult.weight_adjustments` supersedes `weight_overrides` in `compute_composite()`.
- **Per-stock composite penalty**: In unfavorable/adverse markets, base penalty up to 8 points. Modulated by DC score: defensive stocks (DC > 50) get up to 40% penalty reduction. Aggressive growth stock (DC=35) gets full penalty, defensive utility (DC=75) gets ~60% of penalty.
- **Trap signal avoidance**: When RFI is in mild_risk_off zone (-0.3 < RFI < 0) AND rfi_acceleration shows "improving", RFI contribution capped at 45. Based on v13 backtest: mild_risk_off→risk_on had 50% hit rate with -3.42% avg return.
- **Pipeline reordering**: Trend, capital flow, and leading indicator pipelines now run before stock scoring (were after). CF exported early so `compute_leading_indicators()` can read from disk. Market timing step inserted between leading indicators and stock scoring.
- **IC tracking extended**: Added `timing_penalty` to 28-factor IC tracker (varies per stock due to DC modulation, so cross-sectional IC is meaningful).
- **Meta export extended**: `meta.json` now includes `timing` section with score, zone, signal contributions, and weight adjustments.

**Files**: `engine/analyzers/market_timing.py` (new), `engine/config.py`, `engine/scorer/factor_model.py`, `engine/main.py`, `engine/analyze.py`, `engine/exporters/json_exporter.py`, `engine/analyzers/ic_tracker.py`, `frontend/src/components/About.tsx`, `frontend/src/lib/i18n.tsx`

### v18: IC-Driven Rebalance

Comprehensive scoring restructure based on forward-return IC evidence. Addresses the fundamental problem where 55% of composite weight went to dimensions with zero or negative predictive power (EV IR -0.11, VM IR +0.01), while the only predictive dimension (CT IR +1.02) had only 20% weight.

**Key changes from v17:**
- **Dimension weight rebalance**: CT 20%→40% (IR +1.02, 86% hit rate — best signal). EV 30%→15% (IR -0.11). VM 25%→15% (IR +0.01). DC 25%→30% (volatility IR +0.58).
- **EV restructured growth-led**: Growth weight 40%→70%, quality 60%→30%. Growth sub-scores (rev_growth IR +0.88, earn_growth IR +0.46) are the only positive-IC fundamental factors. Quality (IR -0.40) retained at reduced weight for long-term grounding.
- **CT simplified to trend + momentum**: Analyst removed (IR -0.19, was diluting signal). Trend 55% + momentum 45%. Both verified predictive (trend IR +0.95, momentum IR +0.30).
- **DC restructured volatility-led**: Volatility 40%→65% (IR +0.58), safety 60%→35% (safety_score IR -0.27). Within safety, simplified to debt_equity only (IR +0.50) — removed fcf_yield (IR -0.99) and current_ratio (IR -0.47).
- **Anti-signal factors purged from value_score**: Removed forward_pe (IR -2.36, 0% hit rate) and ps_score (IR -0.99, 22% hit rate). Value now uses PE + PB only (PB IR +0.17).
- **Trend gate (anti-value-trap)**: Stocks with trend_score < 35 (clear downtrend) receive up to 8-point composite penalty. Soft penalty zone 35-45 applies up to 3 points. Prevents cheap-but-falling stocks from ranking high.
- **Tier threshold recalibration**: Strong Buy 63→65, Buy 56→57, Hold lower 46→45, Sell 39→38. Adjusted for new CT-dominant distribution.
- **Cyclical DC rebalanced**: For cyclical sectors: safety 50%→25%, volatility 30%→50%, cyclical_risk 20%→25%.

**IC evidence (5-day forward returns, 9-15 observations):**
| Factor | IR | Hit Rate | Action |
|--------|-----|----------|--------|
| catalyst_timeline | +1.02 | 86% | Weight 20%→40% |
| trend_score | +0.95 | 85% | Dominant CT component |
| rev_growth_score | +0.88 | 89% | EV growth-led |
| volatility_score | +0.58 | 77% | DC volatility-led |
| debt_equity_score | +0.50 | 67% | Sole safety metric |
| forward_pe_score | -2.36 | 0% | Removed from value |
| ps_score | -0.99 | 22% | Removed from value |
| fcf_yield_score | -0.99 | 22% | Removed from safety |
| quality_score | -0.40 | 38% | Reduced in EV |
| analyst_score | -0.19 | 42% | Removed from CT |

**Files**: `engine/config.py`, `engine/scorer/factor_model.py`, `engine/analyzers/fundamental.py`, `engine/main.py`, `engine/analyze.py`, `frontend/src/components/About.tsx`, `frontend/src/lib/i18n.tsx`

### v17: Cyclical Risk Analysis

Cyclical risk scoring for commodity/materials sectors. Addresses the fundamental blind spot where the framework treated cyclical-stock characteristics (low PE at earnings peak, high structural volatility, commodity-driven earnings swings) as positive signals instead of risk indicators.

**Key changes from v16:**
- **Materials sector breakpoints**: New `_SECTOR_OVERRIDES["Materials"]` for PE, forward PE, earnings growth, and revenue growth. Low PE (e.g., 5) now scores 55 (was 90) — recognizes that low PE in commodity stocks often signals peak earnings, not deep value. Negative earnings growth scored more neutrally (-20% → 35 vs default 10) since it's a normal cycle feature.
- **Cyclical risk factor**: New `engine/analyzers/cyclical_risk.py` computes `cyclical_risk_score` (0-100) for cyclical sectors. Two signals: (1) Earnings direction (60%): `forward_pe / trailing_pe` ratio — ratio >1.2 means market expects earnings decline (cycle peak risk), <0.8 means earnings improving (cycle trough, safer). (2) Margin deviation (40%): current operating margin vs sector mid-cycle reference — above-normal margins signal peak cycle.
- **DC dimension expansion for cyclical stocks**: For tickers in `CYCLICAL_SECTORS` (Materials, Energy): `DC = 0.50×safety + 0.30×volatility + 0.20×cyclical_risk`. Non-cyclical stocks retain original DC formula (0.60×safety + 0.40×volatility).
- **Commodity-specific DC penalty**: New `TICKER_COMMODITY_RISK` mapping (like `TICKER_JURISDICTION`). CF/NTR/MOS: -8 DC points for China fertilizer export policy risk. IPI: -5 DC points for potash supply concentration risk.
- **Cyclical sector config**: New `CYCLICAL_SECTORS` (Materials, Energy) and `CYCLICAL_MARGIN_REFS` (mid-cycle operating margin references per sector) in config.
- **IC tracking extended**: Added `cyclical_risk_score` to the 27-factor IC tracker (was 26 factors).

**Files**: `engine/analyzers/cyclical_risk.py` (new), `engine/scorer/absolute.py`, `engine/scorer/factor_model.py`, `engine/config.py`, `engine/analyzers/ic_tracker.py`, `engine/main.py`, `engine/analyze.py`, `frontend/src/components/About.tsx`, `frontend/src/lib/i18n.tsx`

### v16: IC-Weighted Scoring

IC-weighted scoring infrastructure that auto-activates once IC data accumulates. Fixes score distribution compression (Hold 85.7% → 64.5%) through trimmed mean aggregation, tier recalibration, sub-score debiasing, and spread amplification.

**Key changes from v15:**
- **IC-weighted averaging**: New `engine/scorer/ic_weights.py` provides `ic_weighted_avg()` and `trimmed_ic_weighted_avg()`. Weights derived from `|mean IC|` with floor 0.1. Falls back to equal weights when IC data insufficient (<20 observations).
- **IC blend-in**: Linear transition from equal-weight to IC-weight over observations 20→40, preventing ranking jumps when IC data first becomes available.
- **IC shrinkage**: Bayesian shrinkage pulls raw IC values toward grand mean IC. Shrinkage coefficient = `min(1, min_obs/n_obs)`, reducing noise from small sample sizes.
- **Trimmed mean**: For sub-scores with ≥3 metrics (value, quality, safety), drops the worst-scoring metric per ticker before averaging. Prevents single bad metric from dragging sub-score to neutral.
- **Metric-level IC tracking**: Extended IC tracker from 14 to 26 factors. Added 12 per-metric scores (pe_score, roe_score, etc.) to history.json for forward-return correlation.
- **Tier threshold recalibration**: Strong Buy 75→63, Buy 60→56, Hold lower 40→46, Sell 25→39. Calibrated to actual score distribution (mean ~54, std ~5).
- **CT dimension reform**: Catalyst Timeline reduced from 5 to 3 components — trend (1/3), momentum (1/3), analyst (1/3). Removed sentiment (std=5.5, noise) and volume (std=13.2, low signal). CT std improved from 6.5 to 7.1.
- **Safety pool-aware centering**: Subtracts pool median and adds 50 to recenter safety_score distribution. Fixes S&P 500 structural bias where large-cap safety metrics are uniformly good (median was ~62, now 50).
- **Analyst breakpoint left-shift**: Consensus rating breakpoints shifted left — consensus=2.0 now scores 58 (was 70). Corrects sell-side optimism bias.
- **Spread amplification**: `composite = median + 1.3 × (raw - median)`, applied after EMA smoothing. Expands score distribution around median. Composite std 5.2→6.8.
- **IC-weighted dimension aggregation**: EV, CT, DC dimensions use `ic_weighted_avg()` for sub-score combination. Falls back to equal weight within each dimension when IC data unavailable.

**Files**: `engine/scorer/ic_weights.py` (new), `engine/analyzers/ic_tracker.py`, `engine/analyzers/fundamental.py`, `engine/scorer/factor_model.py`, `engine/scorer/absolute.py`, `engine/exporters/json_exporter.py`, `engine/config.py`, `engine/analyze.py`, `engine/main.py`, `frontend/src/components/About.tsx`, `frontend/src/lib/i18n.tsx`

### v15: Direct ETF Fund Flows

Hybrid capital flow model: 6 ETFs use real shares outstanding from ETF provider endpoints, 3 ETFs use volume-price proxy as fallback. Replaces broken yfinance shares data with direct iShares/SPDR CSV sources. Fixes fundamental issues from v11-v12: bimodal RFI distribution (33% saturated at ±1), 216 regime transitions in 523 days (noise), uncorrelated risk/safe nets (r=0.041).

**Key changes from v14:**
- **Hybrid fund flows**: 6 ETFs (EWJ, EEM, IBIT, TLT, LQD, GLD) use `daily_flow = Δ(shares_outstanding) × close_price` — real ETF creation/redemption. 3 ETFs (SPY, BIL, VGK) use `daily_return × dollar_volume` as proxy fallback (no free shares outstanding source available).
- **iShares shares outstanding**: New `_fetch_ishares_shares()` fetches shares outstanding from iShares AJAX CSV endpoint (product ID + slug). Covers EWJ, EEM, IBIT, TLT, LQD.
- **SPDR Gold shares outstanding**: New `_fetch_gld_shares()` fetches from SPDR Gold Shares archive CSV (`GLD_US_archive_EN.csv`). Session-level cache avoids re-downloading.
- **Shares source dispatch**: `_fetch_shares_for_ticker()` routes to correct fetcher based on `shares_source` field in config. `None` → proxy-only (no shares fetched).
- **Proxy fallback in analyzer**: New `_compute_proxy_daily_flows()` computes `return × dollar_volume` for SPY/BIL/VGK. Merged into main flow pipeline. Proxy nodes get `confidence: 0.6` (informational).
- **Shares backfill**: `backfill_shares_outstanding()` uses iShares/SPDR fetchers for historical dates, skips proxy-only tickers, rate-limits iShares requests (0.5s delay).
- **BTC-USD → IBIT**: Replaced BTC-USD with IBIT (iShares Bitcoin Trust ETF). Standard ETF with shares outstanding via iShares endpoint.
- **Tanh RFI normalization**: `RFI = tanh((risk_net - safe_net) / scale)`. Smooth, bounded [-1, +1].
- **Simplified analyzer**: Removed CMF, OBV slope, direction voting, cross-asset consistency, CFTC/ICI dependencies. Hybrid pipeline: real shares flows + proxy flows → merge → rolling sum → nodes → RFI → phase → arrows.

**Files**: `engine/config.py`, `engine/collectors/capital_flow.py`, `engine/collect.py`, `engine/analyzers/capital_flow.py`, `engine/capital_flow_pipeline.py`, `engine/main.py`, `engine/exporters/capital_flow_exporter.py`, `.github/workflows/backfill-pipeline.yml`, `frontend/src/lib/i18n.tsx`, `frontend/src/components/About.tsx`

### v14: Leading Indicators

Four forward-looking market turn signals computed from existing collected data. Designed to detect market turns before they happen, complementing the reactive signals in v13.

**Key changes from v13:**
- **VIX Term Structure**: `^VIX / ^VIX3M` ratio — backwardation (>1.05) signals peak fear, deep contango (<0.85) signals complacency. Added `^VIX3M` to macro collector; historical data will accumulate over time.
- **Credit Spread Velocity**: LQD/TLT ratio rate-of-change at 5d/10d windows. Rising = credit tightening (bearish for equities). Falling = credit easing (bullish). 1,018 historical data points from capital flow ETF archives.
- **RFI Acceleration**: Second derivative of Risk Flow Index from `capital_flows.json` phase timeline. Detects bottoming (deceleration of outflow) and topping (deceleration of inflow) signals that precede direction changes. 50 data points.
- **Breadth Thrust**: Rate of sectors flipping from downtrend to uptrend over a 22-day rolling window. Computed from `trend_history.json`. Thrust ≥18% = bullish, ≤-18% = bearish. 1,462 data points.
- **Backtest integration**: All three active indicators added to the backtest framework — 178 credit spread events, 280 breadth thrust events, 38 RFI acceleration events with forward return validation.
- **Pipeline integration**: `compute_leading_indicators()` runs automatically in the main pipeline after capital flows. Exports `leading_indicators.json`.
- **Frontend**: New `/indicators` page with per-indicator cards showing latest signal, mini sparklines, and recent signal history. Filter by individual indicator.

**Files**: `engine/analyzers/leading_indicators.py`, `engine/collectors/macro.py`, `engine/backtest.py`, `engine/main.py`, `frontend/src/components/indicators/LeadingIndicatorsPage.tsx`, `frontend/src/hooks/useLeadingIndicators.ts`, `frontend/src/types/index.ts`, `frontend/src/lib/dataLoader.ts`, `frontend/src/routes.tsx`, `frontend/src/components/layout/Header.tsx`, `frontend/src/lib/i18n.tsx`, `frontend/src/components/About.tsx`

### v13: Signal Backtesting

Backtest framework for historical signal validation. Reads from stored trend_history.json, capital_flows.json, and collected/ ETF price archives to compute forward returns after signal events.

**Key changes from v12:**
- **Backtest engine**: New `engine/backtest.py` — standalone CLI (`python -m engine.backtest`) that runs all backtests and exports `backtest.json`. Pure Python, no new dependencies. Reads from existing `collected/` archives (1,775 daily snapshots from 2020-01-02 to 2026-02-07) and frontend JSON data.
- **4 signal types tested**:
  - **Sector trend transitions** (2,241 events): Detects when a sector's trend state changes (e.g., neutral → uptrend). Forward returns computed from sector ETF prices. Per-sector breakdown included.
  - **Capital flow phase transitions** (27 events): Detects phase changes (normal/riskon/deleverage/bottom/outflow) from capital_flows.json. SPY forward returns as benchmark.
  - **RFI level crossings** (40 events): Tracks Risk Flow Index zone transitions (panic/risk_off/mild_risk_off/neutral/risk_on). SPY forward returns.
  - **Macro regime transitions** (0 events currently — macro collector only started recently, framework ready for future data).
- **Per-signal statistics**: Hit rate, average/median return, expectancy, standard deviation, max drawdown at 5d/10d/22d horizons. Per-sector breakdown for sector trend signals.
- **Backtest report page**: New `/backtest` route with interactive signal cards — filter by signal type, drill-down into horizons/sectors/recent events. Summary cards show top-level metrics.
- **Frontend**: Added nav item, i18n (EN/ZH), TypeScript types, data loader, hook.

**Files**: `engine/backtest.py`, `frontend/src/components/backtest/BacktestPage.tsx`, `frontend/src/hooks/useBacktest.ts`, `frontend/src/types/index.ts`, `frontend/src/lib/dataLoader.ts`, `frontend/src/routes.tsx`, `frontend/src/components/layout/Header.tsx`, `frontend/src/lib/i18n.tsx`, `frontend/src/components/About.tsx`

**Key findings** (2020-01-02 ~ 2026-02-07, 2,308 events):

1. **Sector trend transitions lack standalone alpha.** Both upgrades (n=1126, 22d +1.89%) and downgrades (n=1115, 22d +2.24%) produce positive forward returns — the market's upward beta drowns out signal directionality. Sector trends need conditional filtering (RFI direction or macro regime) to generate alpha.
2. **RFI panic → risk_on is the strongest signal.** 22d: 100% hit rate, +2.51% avg return, only 2.98% max drawdown (n=5). The neutral → panic signal is similarly strong (22d: 100% hit rate, +5.50%). Both confirm that post-panic periods are the highest-conviction buying opportunity.
3. **Capital flow Risk-Off is a contrarian signal.** Phase transitions to risk_off show 83% hit rate at 22d (+1.91%) — fear-driven exits lead to rebounds. Risk-On transitions show 69% hit rate (+1.67%).
4. **mild_risk_off → risk_on is a trap.** Only 50% hit rate at 22d with -3.42% avg return — likely false breakouts where the recovery attempt fails.
5. **Sector performance dispersion matters.** On upgrades, Energy (22d +2.77%, 66% hit) and Industrials (+2.59%, 70% hit) consistently outperform Consumer Staples (+0.70%, 58% hit). Cyclical sectors respond more strongly to trend shifts.
6. **Macro regime data is too sparse.** Only 4 daily snapshots exist (macro collector started recently). Framework ready — will produce actionable signals as data accumulates.

### v12: Flow Normalization

Dollar-volume normalization for cross-asset comparability. Fixes three issues from v11: distorted flow magnitudes, missing phase detection, and phantom flow arrows.

**Key changes from v11:**
- **Dollar-volume normalization**: Raw flows are divided by each asset's weekly dollar volume to get dimensionless "flow intensity", then scaled to the median weekly dollar volume across all 9 assets. This makes BTC ($35B/day volume) and EWJ ($0.3B/day volume) produce comparable flow numbers instead of a 100× distortion.
- **Broad Outflow phase**: New `outflow` phase detected when both risk_net < -3 AND safe_net < -1 (both sides declining simultaneously). Previously misclassified as "normal rotation". Label: "全面流出" / "Broad Outflow" with explanation that capital is exiting to money markets / deposits outside the tracked universe.
- **Zero-sum flow arrows**: Flow arrow total volume capped at `min(total_outflow, total_inflow)`. Each source contributes proportionally to its share of total outflow, each sink proportionally to its share of total inflow. Prevents phantom arrows (e.g., $171B arrows when only $2B actually flowed into sinks).
- **Untracked flow tracking**: Each phase now includes an `untracked` field = `total_outflow - total_inflow`, representing capital that left the tracked ETF universe (likely money market funds, bank deposits, etc.). Displayed in frontend when > $1B with orange highlight.

**Files**: `engine/analyzers/capital_flow.py`, `frontend/src/components/flows/CapitalFlowViz.tsx`, `frontend/src/types/index.ts`, `frontend/src/lib/i18n.tsx`, `frontend/src/components/About.tsx`

### v11: Capital Flow Tracking

Track global capital rotation across 9 asset classes (5 risk, 4 safe) using ETF volume-price signals. Visualize fund flows as an interactive SVG diagram.

**Key changes from v10:**
- **Capital flow ETF collector**: New `engine/collectors/capital_flow.py` fetches daily OHLCV for 9 ETFs — risk assets (SPY, VGK, EWJ, EEM, BTC-USD) and safe havens (GLD, TLT, BIL, LQD). Supports daily snapshots, historical backfill, and reconstruction from stored daily slices.
- **Multi-signal fusion analyzer**: New `engine/analyzers/capital_flow.py` computes per-asset flow estimates using CMF (40%) + OBV slope (30%) + Return×DollarVolume (30%). Direction voting (2/3 agreement → boost, outlier → penalize), cross-asset consistency checks (risk↑ safe↓ → ×1.3, same direction → ×0.7).
- **Optional institutional data**: CFTC COT futures positioning (`engine/collectors/cftc.py`) for directional confirmation (±15-25%). ICI fund flows (`engine/collectors/ici.py`) for magnitude calibration (scale factor [0.2, 5.0]).
- **Multi-window analysis**: Analyzes capital flows across 1W/2W/1M windows simultaneously. Each window produces independent phase detection and flow arrow computation.
- **Phase detection**: Classifies market state — deleverage (risk_net < -3, safe_net > 1), risk-on (risk_net > 3, safe_net < -1), bottom (risk_net ∈ (0, 3], safe_net < 0), normal (default).
- **Flow arrow computation**: Sources (net < 0) → sinks (net > 0) with proportional allocation, minimum ≥0.1B threshold, max 10 arrows per window.
- **Capital flow exporter**: New `engine/exporters/capital_flow_exporter.py` exports `capital_flows.json` with multi-window structure: `{date, default_window, windows: {1W/2W/1M: {phases[]}}}`.
- **Standalone pipeline**: `engine/capital_flow_pipeline.py` — independent CLI for capital flow collection + analysis, runnable separately from the main stock scoring pipeline.
- **SVG visualization**: New `frontend/src/components/flows/CapitalFlowViz.tsx` renders interactive SVG diagram with risk assets on the left, safe havens on the right, animated flow arrows between them. Includes interval selector (1W/2W/1M), phase indicator, and net flow summary.

**Files**: `engine/collectors/capital_flow.py`, `engine/collectors/cftc.py`, `engine/collectors/ici.py`, `engine/analyzers/capital_flow.py`, `engine/exporters/capital_flow_exporter.py`, `engine/capital_flow_pipeline.py`, `engine/config.py`, `frontend/src/components/flows/CapitalFlowViz.tsx`

### v10: Trend Dashboard

Reposition from stock screener to trend identification tool. Build sector-level trend analysis with interactive frontend.

**Key changes from v9:**
- **Sector ETF collector**: New `engine/collectors/sector_etf.py` fetches OHLCV for 11 SPDR Select Sector ETFs (XLK/XLF/XLE/XLV/XLY/XLP/XLRE/XLI/XLU/XLB/XLC) + SPY benchmark.
- **Sector trend analyzer**: New `engine/analyzers/sector_trend.py` computes per-sector trend signals: relative strength (35%), breadth (25%), analyst revisions (15%), momentum (15%), volume (10%). Also computes historical RS/momentum from ETF price data via `compute_trend_history()`.
- **Trend scorer**: New `engine/analyzers/trend_scorer.py` produces composite trend strength (0-100) and trend state classification: Strong Uptrend (>=70), Uptrend (>=55), Neutral (>=40), Downtrend (>=25), Strong Downtrend (<25).
- **Trend exporter**: New `engine/exporters/trend_exporter.py` exports `trends.json` (current sector trends) and `trend_history.json` (historical RS/momentum scores for charting).
- **Trend line chart**: `frontend/src/components/trends/TrendLineChart.tsx` — multi-line chart (recharts) showing 11 sector trend lines over time. Signal toggle (Rel. Strength / Momentum), range selector (3M/6M/1Y/All), interval selector (W/M/Q) with period-based resampling.
- **Sector selection + stock list**: Legend click selects a sector — highlights that line, dims others, and filters a stock table below the chart to show only that sector's stocks. Default shows all stocks.
- **Regime banner**: `RegimeBanner` displays current macro regime (Risk On / Neutral / Risk Off) from `meta.json`.
- **Trend history**: Engine computes weekly-sampled historical RS and momentum scores from ETF price data. Frontend renders these as interactive time-series.
- **Version history timeline**: About page now includes a visual timeline of all versions (v1-v10) with current/deprecated badges.

**Files**: `engine/collectors/sector_etf.py`, `engine/analyzers/sector_trend.py`, `engine/analyzers/trend_scorer.py`, `engine/exporters/trend_exporter.py`, `engine/config.py`, `engine/main.py`, `frontend/src/components/trends/TrendDashboard.tsx`, `frontend/src/components/trends/TrendLineChart.tsx`, `frontend/src/components/trends/RegimeBanner.tsx`, `frontend/src/hooks/useTrends.ts`, `frontend/src/hooks/useTrendHistory.ts`, `frontend/src/lib/dataLoader.ts`, `frontend/src/lib/i18n.tsx`, `frontend/src/types/index.ts`, `frontend/src/routes.tsx`, `frontend/src/components/About.tsx`

### v9: Intelligence Upgrade

Two-part intelligence upgrade: better sentiment NLP and macro regime awareness.

**Key changes from v8:**
- **Sentiment time decay**: Headlines weighted by exponential decay with 7-day half-life (`w = exp(-ln2/7 × days_old)`). Recent headlines contribute more to the average than stale ones.
- **Source credibility weighting**: Three-tier publisher credibility system. Tier 1 (1.5×): Reuters, Bloomberg, WSJ, FT, CNBC, AP, Barron's, MarketWatch. Tier 2 (1.0×): default. Tier 3 (0.7×): Benzinga, Seeking Alpha, Motley Fool, InvestorPlace. Combined weight = `time_decay × source_weight`.
- **Headline count normalization**: `sentiment_confidence = min(1.0, news_count / 10)`. Low-confidence scores pulled toward neutral: `score = 50 + confidence × (raw - 50)`. Prevents stocks with 1-2 headlines from getting extreme sentiment scores.
- **Macro data collector**: New `engine/collectors/macro.py` fetches VIX (`^VIX`), S&P 500 (`^GSPC`) with SMA200, 10Y Treasury yield (`^TNX`), and 13W T-Bill yield (`^IRX`).
- **Market regime detection**: New `engine/analyzers/macro.py` classifies market as risk_on, neutral, or risk_off based on three signals: VIX level (<15 risk-on, >25 risk-off), S&P 500 vs SMA200 (>5% above risk-on, >5% below risk-off), yield curve slope (>1pp normal, <0 inverted). Regime score = average of available signals.
- **Regime-conditional dimension weights**: In risk-on: CT 25%, DC 20% (+5% to catalysts). In risk-off: CT 15%, DC 30% (+5% to defense). Neutral: default weights. EV and VM stay constant across regimes.
- **Macro data export**: Regime info (regime, signals, VIX, spread, etc.) exported in `meta.json` for frontend consumption.

**Files**: `engine/analyzers/sentiment.py`, `engine/collectors/macro.py`, `engine/analyzers/macro.py`, `engine/scorer/factor_model.py`, `engine/config.py`, `engine/exporters/json_exporter.py`, `engine/main.py`

### v8: Analyst Revision Momentum

Adds sell-side analyst revision momentum as a dedicated signal within Catalyst Timeline, separating institutional-quality analyst actions from general news sentiment.

**Key changes from v7:**
- **Analyst data collector**: New `engine/collectors/analyst.py` fetches analyst consensus (recommendation mean, target prices, number of analysts) and upgrade/downgrade history (90-day lookback) from yfinance per ticker.
- **Analyst revision momentum analyzer**: New `engine/analyzers/analyst.py` computes three sub-metrics:
  - **Revision momentum** (40%): `(upgrades - downgrades) / total_revisions` mapped to 0-100 via piecewise breakpoints.
  - **Target price upside** (35%): `(target_median - current_price) / current_price` mapped to 0-100.
  - **Consensus rating** (25%): yfinance `recommendationMean` (1=Strong Buy to 5=Strong Sell) inverted and mapped to 0-100.
- **Catalyst Timeline reweighting**: Added `analyst_score` as a new component. Reweighted: trend 25% + momentum 25% + analyst 20% + sentiment 15% + volume 15% (was: trend 30% + momentum 30% + sentiment 25% + volume 15%).
- **IC tracking extended**: `analyst_score` added to the 14-factor IC tracker (was 13 factors).
- **Missing data default**: Analyst score defaults to 50 (neutral) when no analyst data is available — no directional bias since lack of coverage is ambiguous.

**Files**: `engine/collectors/analyst.py`, `engine/analyzers/analyst.py`, `engine/scorer/absolute.py`, `engine/scorer/factor_model.py`, `engine/config.py`, `engine/analyzers/ic_tracker.py`, `engine/exporters/json_exporter.py`, `engine/main.py`

### v7: Signal Validation & Data Quality

Validates scoring rules via IC tracking, handles missing data honestly, and introduces data completeness scoring.

**Key changes from v6:**
- **Per-metric IC tracking**: Extended IC computation from 5 factors (composite + 4 dimensions) to 13 factors (+ 8 sub-scores: value, quality, growth, safety, trend, momentum, volatility, volume). Sub-scores are now stored in `history.json` for forward-return correlation. Enables detection of which individual scoring rules are predictive.
- **Directional missing-data defaults**: Missing metrics no longer universally default to 50 (neutral). Metrics with known directional bias when missing use below-neutral defaults: FCF yield → 35, profit margin → 35, earnings growth → 38, ROA → 40, current ratio → 42. Other metrics remain at 50.
- **Data completeness tracking**: Each ticker gets a `data_completeness` score (0-1) measuring the fraction of scored metrics with real data. Computed as weighted average of fundamental completeness (12 metrics, 67% weight) and technical completeness (6 metrics, 33% weight).
- **Composite score penalty**: When `data_completeness < 0.50`, a linear penalty of up to 5 points is applied to composite_score. This prevents stocks with very sparse data from getting inflated neutral scores.

**Files**: `engine/scorer/absolute.py`, `engine/scorer/factor_model.py`, `engine/analyzers/fundamental.py`, `engine/analyzers/technical.py`, `engine/analyzers/ic_tracker.py`, `engine/exporters/json_exporter.py`, `engine/main.py`

### v6: Technical Scoring Overhaul

Comprehensive upgrade to technical indicator scoring: price normalization, directional context, true volatility measurement, margin-weighted trend, and math-consistent EMA smoothing.

**Key changes from v5:**
- **MACD histogram price normalization**: `macd_histogram_pct = (histogram / close) * 100`. Removes absolute ±0.5 threshold that favored low-price stocks. Breakpoints now use percentage-of-price values.
- **Direction-aware volume**: `signed_volume_ratio = volume_ratio * sign(daily_return)`. High volume on a down day scores bearish (distribution); high volume on an up day scores bullish (confirmation). Replaces magnitude-only scoring.
- **True volatility measurement**: Replaced BB position (%B) with two proper volatility measures: `bb_width = (upper - lower) / middle` (Bollinger bandwidth) and `hist_volatility` (annualized std of 20-day returns). `volatility_score = avg(bb_width_score, hist_vol_score)`. Removes mean-reversion bias.
- **Margin-weighted trend alignment**: Each SMA alignment check now scores on a continuous 0-1 scale based on percentage distance from the SMA, instead of a binary pass/fail. Price 20% above SMA200 gets a stronger signal than price 0.1% above.
- **Per-dimension EMA smoothing**: EMA smoothing (α=0.3) now applied to each of the four dimensions individually. Composite is then recomputed from smoothed dimensions, ensuring `composite = Σ(weight_i × smoothed_dim_i)`. Fixes the math inconsistency where displayed dimension scores didn't add up to the displayed composite.

**Files**: `engine/analyzers/technical.py`, `engine/scorer/absolute.py`, `engine/main.py`

### v5: Fundamental Scoring Overhaul

Comprehensive upgrade to fundamental scoring: expanded sector awareness, deeper safety evaluation, and forward-looking valuation.

**Key changes from v4:**
- **Sector-aware scoring for 6 sectors**: Generalized `_is_financial()` to a `_SECTOR_OVERRIDES` lookup table covering Financial, Technology, Healthcare, Utilities, Real Estate, Energy. Each sector has tailored breakpoints for PE, PB, PS, D/E, and growth metrics where structural norms differ.
- **Expanded safety dimension**: `safety_score` upgraded from a single metric (D/E) to `avg(debt_equity_score, fcf_yield_score, current_ratio_score)`. Added FCF yield breakpoints and current ratio breakpoints. Collector now fetches `totalDebt`, `totalCash`, `ebitda`, `currentRatio`.
- **Forward PE scoring**: Added `score_forward_pe()` with sector-aware breakpoints. `value_score` now `avg(pe, forward_pe, pb, ps)` instead of `avg(pe, pb, ps)`.
- **Sector-aware growth scoring**: Utilities use adjusted growth expectations (3% revenue growth = good, not mediocre).

### v4: Sector-Aware Breakpoints

Added financial-sector-specific breakpoints to fix systematic over-scoring of banks and insurers.

**Key changes from v3:**
- Financial PE 8 now scores 60 (was 90) — low PE is structural for financials, not deep value.
- Financial PB 1.5 scores 52 (was ~70) — book value dynamics differ from non-financial sectors.
- Financial D/E scored near-neutral (~50) — leverage is the business model, not a risk signal.
- Generalized sector-detection pattern (`_is_financial()`) for future sector expansions.

### v3: Qualitative 4-Dimension Model

Replaced the flat 3-factor aggregation (fundamental/technical/sentiment) with four investment-analysis dimensions, each with clear semantic meaning.

**Key changes from v2:**
- **Earnings Visibility (30%)** = 0.60×quality + 0.40×growth — "Can we reliably forecast earnings?"
- **Valuation Margin (25%)** = value — "Are we buying at a discount?"
- **Catalyst Timeline (20%)** = 0.30×trend + 0.30×momentum + 0.25×sentiment + 0.15×volume — "Will momentum carry forward?"
- **Downside Control (25%)** = 0.60×safety + 0.40×volatility — "How much do we lose if wrong?"
- Added EMA smoothing (α=0.3) on composite score to reduce noise.
- Added hysteresis (±2 pts) at tier boundaries to prevent oscillation.
- Added change attribution: when a rating changes, identify the primary driving dimension.

### v2: Absolute Rating + Relative Ranking

Replaced z-score with piecewise linear breakpoints for absolute 0-100 metric scoring. Separated **Rating** (absolute quality tier) from **Ranking** (relative position).

**Key changes from v1:**
- Each metric scored via domain-specific breakpoints, not cross-sectional statistics.
- Rating based on fixed thresholds (≥75 Strong Buy, ≥60 Buy, etc.) — independent of other stocks.
- Ranking remains relative by design, used only for comparison within the same tier.
- Financial sector gets adjusted breakpoints (PE, PB, D/E) to avoid structural bias.

**Key principle**: A stock's rating reflects its own quality. Ranking is for comparison.

### v1: Z-score + Percentile Ranking (deprecated)

Scoring: z-score normalization (`z = (x - mean) / std`) + percentile-based tier assignment.

**Why deprecated:**
1. **Fixed distribution**: Percentile tiers guarantee exactly 10% Strong Buy, 10% Strong Sell regardless of actual stock quality. Bull market where everything is good → 10% still labeled "Strong Sell".
2. **Rating = Ranking confusion**: Tier and rank conflated into one system. Tier was just a label for rank position, not an independent quality assessment.
3. **Unstable ratings**: Z-scores recomputed daily from cross-section. A stock's z-score changes because *other stocks* changed, not because it changed. Minor data fluctuations → position shifts → tier flips.
4. **No attribution**: When a rating changed, no way to identify which factor drove it.
