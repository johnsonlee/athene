"""Configuration constants for the Athene scoring engine."""

# ---------- Qualitative dimension weights (v3) ----------
# Composite = EV*0.30 + VM*0.25 + CT*0.20 + DC*0.25
WEIGHT_EARNINGS_VISIBILITY = 0.30
WEIGHT_VALUATION_MARGIN = 0.25
WEIGHT_CATALYST_TIMELINE = 0.20
WEIGHT_DOWNSIDE_CONTROL = 0.25

# Earnings Visibility sub-composition
EV_WEIGHT_QUALITY = 0.60
EV_WEIGHT_GROWTH = 0.40

# Valuation Margin sub-composition
VM_WEIGHT_VALUE = 1.00

# Catalyst Timeline sub-composition (v16: concentrate on high-spread factors)
CT_WEIGHT_TREND = 0.40
CT_WEIGHT_MOMENTUM = 0.35
CT_WEIGHT_ANALYST = 0.25
CT_WEIGHT_SENTIMENT = 0.00
CT_WEIGHT_VOLUME = 0.00

# Downside Control sub-composition
DC_WEIGHT_SAFETY = 0.60
DC_WEIGHT_VOLATILITY = 0.40

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
# Calibrated to actual score distribution (mean ~54, std ~5, range 35-69).
# SB ~3%, B ~36%, H ~55%, S ~5%, SS ~2%.
SCORE_STRONG_BUY = 63
SCORE_BUY = 56
SCORE_HOLD_LOWER = 46
SCORE_SELL = 39
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

# ---------- Output ----------
OUTPUT_DIR = "frontend/public/data"
