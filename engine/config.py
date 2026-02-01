"""Configuration constants for the Athene scoring engine."""

# ---------- Factor weights ----------
WEIGHT_FUNDAMENTAL = 0.40
WEIGHT_TECHNICAL = 0.35
WEIGHT_SENTIMENT = 0.25

# Fundamental sub-factor weights
FUND_WEIGHT_VALUE = 0.30
FUND_WEIGHT_QUALITY = 0.30
FUND_WEIGHT_GROWTH = 0.25
FUND_WEIGHT_SAFETY = 0.15

# Technical sub-factor weights
TECH_WEIGHT_TREND = 0.40
TECH_WEIGHT_MOMENTUM = 0.30
TECH_WEIGHT_VOLATILITY = 0.15
TECH_WEIGHT_VOLUME = 0.15

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

# ---------- Data collection ----------
PRICE_HISTORY_DAYS = 365         # 1 year of daily OHLCV
NEWS_MAX_ARTICLES = 20           # max news articles per ticker
RATE_LIMIT_PAUSE = 0.1          # seconds between yfinance calls
BATCH_SIZE = 50                  # tickers per yf.download batch

# ---------- Z-score (legacy, kept for reference) ----------
WINSORIZE_LIMITS = (0.02, 0.02)  # 2% tails

# ---------- Output ----------
OUTPUT_DIR = "frontend/public/data"
