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

# Catalyst Timeline sub-composition (v8: added analyst revision momentum)
CT_WEIGHT_TREND = 0.25
CT_WEIGHT_MOMENTUM = 0.25
CT_WEIGHT_ANALYST = 0.20
CT_WEIGHT_SENTIMENT = 0.15
CT_WEIGHT_VOLUME = 0.15

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
SCORE_STRONG_BUY = 75
SCORE_BUY = 60
SCORE_HOLD_LOWER = 40
SCORE_SELL = 25
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
CAPITAL_FLOW_ETFS = {
    "SPY":     {"id": "usEquity",   "label_zh": "美股",   "label_en": "US Equity",   "type": "risk"},
    "VGK":     {"id": "euEquity",   "label_zh": "欧股",   "label_en": "EU Equity",   "type": "risk"},
    "EWJ":     {"id": "jpEquity",   "label_zh": "日股",   "label_en": "JP Equity",   "type": "risk"},
    "EEM":     {"id": "emEquity",   "label_zh": "新兴",   "label_en": "EM Equity",   "type": "risk"},
    "BTC-USD": {"id": "crypto",     "label_zh": "加密",   "label_en": "Crypto",      "type": "risk"},
    "GLD":     {"id": "gold",       "label_zh": "黄金",   "label_en": "Gold",        "type": "safe"},
    "TLT":     {"id": "usTreasury", "label_zh": "美债",   "label_en": "US Treasury", "type": "safe"},
    "BIL":     {"id": "cash",       "label_zh": "现金",   "label_en": "Cash",        "type": "safe"},
    "LQD":     {"id": "corpBond",   "label_zh": "公司债", "label_en": "Corp Bond",   "type": "safe"},
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

# Signal fusion weights (3 independent volume-price signals)
CF_WEIGHT_CMF = 0.40              # Chaikin Money Flow (close position × volume)
CF_WEIGHT_OBV = 0.30              # OBV slope (cumulative volume trend)
CF_WEIGHT_RDV = 0.30              # Return × Dollar Volume (raw price-volume flow)

# Cross-asset consistency: boost/penalize confidence
CF_CONSISTENCY_BOOST = 1.3        # multiplier when risk/safe signals agree
CF_CONSISTENCY_PENALTY = 0.7      # multiplier when signals are contradictory

# CFTC COT mapping: futures contract keywords → node IDs
CFTC_CONTRACT_MAP = {
    "E-MINI S&P 500":    "usEquity",
    "GOLD":              "gold",
    "U.S. TREASURY BONDS": "usTreasury",
    "EURO FX":           "euEquity",
    "JAPANESE YEN":      "jpEquity",
}
CFTC_REPORT_URL = "https://www.cftc.gov/dea/newcot/FinFutL.txt"

# ---------- Data collection ----------
PRICE_HISTORY_DAYS = 365         # 1 year of daily OHLCV
ETF_HISTORY_PERIOD = "max"       # yfinance period for sector ETF trend history (all available)
TREND_HISTORY_SAMPLE_INTERVAL = 1  # sample every N trading days (1 = daily)
NEWS_MAX_ARTICLES = 20           # max news articles per ticker
RATE_LIMIT_PAUSE = 0.1          # seconds between yfinance calls
BATCH_SIZE = 50                  # tickers per yf.download batch

# ---------- Z-score (legacy, kept for reference) ----------
WINSORIZE_LIMITS = (0.02, 0.02)  # 2% tails

# ---------- Output ----------
OUTPUT_DIR = "frontend/public/data"
