"""Configuration constants for the Athene scoring engine."""

# ---------- Qualitative dimension weights (v18: IC-driven rebalance) ----------
# v18: Reweighted based on IC evidence. CT (IR +1.02) gets dominant weight;
# EV/VM (IR -0.11/+0.01) dramatically reduced. DC kept moderate (volatility works).
# Composite = EV*0.15 + VM*0.15 + CT*0.40 + DC*0.30
WEIGHT_EARNINGS_VISIBILITY = 0.15
WEIGHT_VALUATION_MARGIN = 0.15
WEIGHT_CATALYST_TIMELINE = 0.40
WEIGHT_DOWNSIDE_CONTROL = 0.30

# Earnings Visibility sub-composition (v18: flip to growth-led)
# Growth (IR +0.17) is the only positive-IC component; quality (IR -0.40) is anti-signal.
# Keep quality at reduced weight for long-term fundamental grounding.
EV_WEIGHT_QUALITY = 0.30
EV_WEIGHT_GROWTH = 0.70

# Valuation Margin sub-composition
VM_WEIGHT_VALUE = 1.00

# Catalyst Timeline sub-composition (v18: trend-dominant, remove analyst)
# Trend IR +0.95, momentum IR +0.30 — both verified predictive.
# Analyst IR -0.19 — removed, was diluting signal.
CT_WEIGHT_TREND = 0.55
CT_WEIGHT_MOMENTUM = 0.45
CT_WEIGHT_ANALYST = 0.00
CT_WEIGHT_SENTIMENT = 0.00
CT_WEIGHT_VOLUME = 0.00

# Downside Control sub-composition (v18: volatility-led)
# Volatility IR +0.58 (strong), safety IR -0.27 (anti-signal).
# Keep safety at reduced weight for balance sheet grounding.
DC_WEIGHT_SAFETY = 0.35
DC_WEIGHT_VOLATILITY = 0.65

# Legacy factor weights (kept for backward-compat display)
WEIGHT_FUNDAMENTAL = 0.50
WEIGHT_TECHNICAL = 0.30
WEIGHT_SENTIMENT = 0.20

# Fundamental sub-factor weights (used to compute building-block sub-scores)
FUND_WEIGHT_VALUE = 0.25
FUND_WEIGHT_QUALITY = 0.30
FUND_WEIGHT_GROWTH = 0.25
FUND_WEIGHT_SAFETY = 0.20

# Technical sub-factor weights (used to compute building-block sub-scores)
TECH_WEIGHT_TREND = 0.30
TECH_WEIGHT_MOMENTUM = 0.30
TECH_WEIGHT_VOLATILITY = 0.20
TECH_WEIGHT_VOLUME = 0.20

# ---------- Rating thresholds (absolute, 0-100 scale) ----------
# v18: Recalibrated for new weight structure. CT-dominant scoring produces
# wider spread. Thresholds shifted to reflect new distribution.
SCORE_STRONG_BUY = 65
SCORE_BUY = 57
SCORE_HOLD_LOWER = 45
SCORE_SELL = 38
TIER_HYSTERESIS = 2        # ±2 points buffer to prevent oscillation

# Score smoothing (EMA on composite_score)
SMOOTH_ALPHA = 0.3         # smoothed = alpha * raw + (1-alpha) * prev

TIER_LABELS = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "hold": "Hold",
    "sell": "Sell",
    "strong_sell": "Strong Sell",
}

TIER_COLORS = {
    "strong_buy": "#15803d",   # deep green
    "buy": "#4ade80",          # light green
    "hold": "#9ca3af",         # gray
    "sell": "#fb923c",         # orange
    "strong_sell": "#ef4444",  # red
}

# ---------- Technical indicator parameters ----------
SMA_PERIODS = [20, 50, 200]
EMA_PERIODS = [12, 26]
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2
KDJ_PERIOD = 14

# ---------- Extra tickers (not in S&P 500 / NASDAQ 100) ----------
EXTRA_TICKERS = [
    {"ticker": "CPNG", "name": "Coupang", "sector": "Consumer Cyclical", "industry": "Internet Retail"},
    {"ticker": "BABA", "name": "Alibaba Group", "sector": "Consumer Cyclical", "industry": "Internet Retail"},
    {"ticker": "XBI", "name": "SPDR S&P Biotech ETF", "sector": "Healthcare", "industry": "Biotechnology"},
    {"ticker": "SAN", "name": "Banco Santander, S.A. Sponsored", "sector": "Financial Services", "industry": "Banks - Diversified"},
    {"ticker": "CCJ", "name": "Cameco Corporation", "sector": "Energy", "industry": "Uranium"},
    {"ticker": "VKTX", "name": "Viking Therapeutics, Inc.", "sector": "Healthcare", "industry": "Biotechnology"},
    {"ticker": "NBIS", "name": "Nebius Group N.V.", "sector": "Communication Services", "industry": "Internet Content & Information"},
    {"ticker": "CRWV", "name": "CoreWeave, Inc.", "sector": "Technology", "industry": "Software - Infrastructure"},
    {"ticker": "SE", "name": "Sea Limited", "sector": "Consumer Cyclical", "industry": "Internet Retail"},
    {"ticker": "RBLX", "name": "Roblox Corporation", "sector": "Communication Services", "industry": "Electronic Gaming & Multimedia"},
    {"ticker": "OKLO", "name": "Oklo Inc.", "sector": "Utilities", "industry": "Utilities - Independent Power Producers"},
    {"ticker": "CRCL", "name": "Circle Internet Group, Inc.", "sector": "Financial Services", "industry": "Capital Markets"},
]

# ---------- v9: Sentiment analysis ----------
SENTIMENT_HALF_LIFE_DAYS = 7     # time decay half-life for news headlines
SENTIMENT_CONFIDENCE_N = 10      # headlines needed for full confidence (1.0)

# ---------- v9: Macro regime ----------
REGIME_WEIGHT_SHIFT = 0.05       # ± shift to CT/DC in risk_on/risk_off

# ---------- Sector ETFs (v10: trend pipeline) ----------
SECTOR_ETFS = {
    "XLK": "Information Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLC": "Communication Services",
}
SPY_TICKER = "SPY"

# Trend signal weights
TREND_WEIGHT_RELATIVE_STRENGTH = 0.35
TREND_WEIGHT_BREADTH = 0.25
TREND_WEIGHT_ANALYST_REVISIONS = 0.15
TREND_WEIGHT_MOMENTUM = 0.15
TREND_WEIGHT_VOLUME = 0.10

# Trend state thresholds (0-100 scale)
TREND_STRONG_UPTREND = 70
TREND_UPTREND = 55
TREND_NEUTRAL = 40
TREND_DOWNTREND = 25
# < 25 = Strong Downtrend

# ---------- Capital Flow ETFs (global asset class tracking) ----------
# shares_source: "ishares" | "spdr_gold" | None (proxy-only)
CAPITAL_FLOW_ETFS = {
    "SPY":     {"id": "usEquity",   "label_zh": "美股",   "label_en": "US Equity",   "type": "risk", "shares_source": None},
    "VGK":     {"id": "euEquity",   "label_zh": "欧股",   "label_en": "EU Equity",   "type": "risk", "shares_source": None},
    "EWJ":     {"id": "jpEquity",   "label_zh": "日股",   "label_en": "JP Equity",   "type": "risk", "shares_source": "ishares", "ishares_id": 239665, "ishares_slug": "ishares-msci-japan-etf"},
    "EEM":     {"id": "emEquity",   "label_zh": "新兴",   "label_en": "EM Equity",   "type": "risk", "shares_source": "ishares", "ishares_id": 239637, "ishares_slug": "ishares-msci-emerging-markets-etf"},
    "IBIT":    {"id": "crypto",     "label_zh": "加密",   "label_en": "Crypto",      "type": "risk", "shares_source": "ishares", "ishares_id": 333011, "ishares_slug": "ishares-bitcoin-trust-etf"},
    "GLD":     {"id": "gold",       "label_zh": "黄金",   "label_en": "Gold",        "type": "safe", "shares_source": "spdr_gold"},
    "TLT":     {"id": "usTreasury", "label_zh": "美债",   "label_en": "US Treasury", "type": "safe", "shares_source": "ishares", "ishares_id": 239454, "ishares_slug": "ishares-20-plus-year-treasury-bond-etf"},
    "BIL":     {"id": "cash",       "label_zh": "现金",   "label_en": "Cash",        "type": "safe", "shares_source": None},
    "LQD":     {"id": "corpBond",   "label_zh": "公司债", "label_en": "Corp Bond",   "type": "safe", "shares_source": "ishares", "ishares_id": 239566, "ishares_slug": "ishares-iboxx-investment-grade-corporate-bond-etf"},
}
CAPITAL_FLOW_LOOKBACK_WEEKS = 52  # snapshots per window in timeline (~1 year)
CAPITAL_FLOW_WINDOW_DAYS = 5      # default trading days per window
CAPITAL_FLOW_MIN_FLOW = 0.1       # minimum flow ($B proxy) to draw an arrow
CAPITAL_FLOW_MAX_ARROWS = 10      # max flow arrows per phase
# Multi-window presets: label → trading days
CAPITAL_FLOW_WINDOWS = {
    "1W": 5,    # 1 week (5 trading days)
    "2W": 10,   # 2 weeks
    "1M": 22,   # 1 month (~22 trading days)
}

# RFI tanh normalization scale (calibrated for real fund flows in $B).
# Typical |risk_net - safe_net| is 1-10$B.  Scale=5 maps median (~2$B) to
# RFI ±0.38 and extremes (~10$B) to ±0.96, making all thresholds reachable.
RFI_TANH_SCALE = 5.0              # tanh((risk_net - safe_net) / scale)

# Risk Flow Index (RFI) thresholds: tanh-normalized, range [-1, +1]
RFI_RISK_ON = 0.3                 # RFI >  0.3 → Risk-On (capital flooding risk assets)
RFI_MILD_RISK_OFF = -0.3          # RFI -0.3 ~ 0 → Mild risk-off
RFI_RISK_OFF = -0.6               # RFI < -0.6 → Risk-Off (capital fleeing risk assets)
RFI_PANIC = -0.8                  # RFI < -0.8 → Panic deleveraging

# ---------- Data collection ----------
PRICE_HISTORY_DAYS = 365         # 1 year of daily OHLCV
ETF_HISTORY_PERIOD = "max"       # yfinance period for sector ETF trend history (all available)
TREND_HISTORY_SAMPLE_INTERVAL = 1  # sample every N trading days (1 = daily)
NEWS_MAX_ARTICLES = 20           # max news articles per ticker
RATE_LIMIT_PAUSE = 0.1          # seconds between yfinance calls
BATCH_SIZE = 50                  # tickers per yf.download batch

# ---------- Z-score (legacy, kept for reference) ----------
WINSORIZE_LIMITS = (0.02, 0.02)  # 2% tails

# ---------- Cyclical sector configuration (v17) ----------
# Sectors where earnings are structurally cyclical (commodity-driven).
# These sectors receive cyclical risk scoring instead of neutral (50).
CYCLICAL_SECTORS = {
    "Basic Materials",  # yfinance sector name
    "Materials",        # alias
    "Energy",
}

# Reference operating margins by sector — the "mid-cycle" normal.
# Current margin relative to this reference indicates cycle position.
CYCLICAL_MARGIN_REFS = {
    "Basic Materials": 0.15,  # Materials mid-cycle ~15% operating margin
    "Materials": 0.15,
    "Energy": 0.12,           # Energy mid-cycle ~12% operating margin
}

# Downside Control sub-composition (v17: adds cyclical risk)
# v18: Rebalanced — volatility gets more weight, safety less
DC_WEIGHT_SAFETY_V17 = 0.25
DC_WEIGHT_VOLATILITY_V17 = 0.50
DC_WEIGHT_CYCLICAL_RISK = 0.25

# ---------- Commodity-specific risk (DC penalty, like jurisdiction risk) ----------
# Ticker-level adjustments for commodity exposure risks that the quantitative
# model cannot capture (e.g., policy risk, sanction risk).
COMMODITY_RISK = {
    "FERTILIZER_CN_EXPORT": {"dc_penalty": -8, "label": "China fertilizer export policy risk"},
    "FERTILIZER_POTASH": {"dc_penalty": -5, "label": "Potash supply concentration risk"},
}

TICKER_COMMODITY_RISK = {
    "CF": "FERTILIZER_CN_EXPORT",
    "NTR": "FERTILIZER_CN_EXPORT",
    "MOS": "FERTILIZER_CN_EXPORT",
    "IPI": "FERTILIZER_POTASH",
}

# ---------- Jurisdiction risk (DC penalty) ----------
# Two-layer structure: risk type defines penalty, ticker mapping classifies stocks.
JURISDICTION_RISK = {
    "CN_VIE": {"dc_penalty": -12, "label": "VIE structure, China ops"},
    "CN_ADR": {"dc_penalty": -8,  "label": "ADR, China ops"},
}

TICKER_JURISDICTION = {
    "PDD": "CN_VIE",
    "BABA": "CN_VIE",
}

# ---------- v18: Trend gate (anti-value-trap) ----------
# Penalize stocks in clear downtrends regardless of valuation attractiveness.
# Prevents cheap-but-falling stocks from ranking high (value trap avoidance).
TREND_GATE_THRESHOLD = 35       # trend_score below this triggers penalty
TREND_GATE_MAX_PENALTY = 8.0    # max composite penalty for deep downtrend
TREND_GATE_SOFT_THRESHOLD = 45  # partial penalty starts here
TREND_GATE_SOFT_PENALTY = 3.0   # partial penalty for weak trend

# ---------- v19: Market timing ----------
# Signal weights for composite market timing score
TIMING_WEIGHT_RFI = 0.35
TIMING_WEIGHT_MACRO = 0.25
TIMING_WEIGHT_CREDIT = 0.20
TIMING_WEIGHT_BREADTH = 0.15
TIMING_WEIGHT_VIX_TS = 0.05

# Timing zone thresholds (0-100 scale)
TIMING_ZONE_FAVORABLE = 62
TIMING_ZONE_NEUTRAL = 45
TIMING_ZONE_UNFAVORABLE = 30

# Weight adjustment: max CT/DC shift based on timing (replaces REGIME_WEIGHT_SHIFT)
TIMING_MAX_WEIGHT_SHIFT = 0.10

# Composite penalty in unfavorable/adverse markets
TIMING_PENALTY_THRESHOLD = 45      # penalty starts below this score
TIMING_MAX_PENALTY = 8.0           # max composite penalty in adverse markets
TIMING_DC_MODULATION = 0.40        # max penalty reduction for defensive stocks (DC>50)

# ---------- v20: Alpha Model (three-factor multiplicative) ----------
# Score = (VM% × EV% × Timing% / ALPHA_SCORE_NORM) × 100
# Each factor normalized to [0, 100] by its theoretical max (VM_MAX=130, EV_MAX=150,
# TIMING_MAX=100). Then the raw product (theoretical [0, 100], practical [0, ~29])
# is rescaled by ALPHA_SCORE_NORM so top stocks naturally reach ~90+ instead of ~27.
# Runs in parallel with legacy additive model for validation.
ALPHA_SCORE_NORM = 30.0                 # historical max of VM%×EV%×T% product is ~29 (50d × 534 tickers)
ALPHA_MODEL_TIMING_ALPHA = 0.5          # reversal vs cycle_upside weight (calibrate from IC)
ALPHA_MODEL_DIRECTION_CENTER = 0.85     # multiplier at neutral direction
ALPHA_MODEL_DIRECTION_RANGE = 0.65      # multiplier half-range: [0.85-0.65, 0.85+0.65] = [0.2, 1.5]
ALPHA_MODEL_EV_QUALITY_WEIGHT = 0.30    # quality contribution to visibility
ALPHA_MODEL_EV_GROWTH_WEIGHT = 0.70     # growth contribution to visibility
ALPHA_MODEL_THRESHOLD = 30              # score below this → not worth holding (calibrate from backtest)

# ---------- Output ----------
OUTPUT_DIR = "frontend/public/data"
