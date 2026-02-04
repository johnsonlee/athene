# Athene

Trend identification tool for U.S. equity markets. Analyzes sector-level capital flows, breadth, and momentum to help investors identify which sectors are gaining institutional interest and which are losing it.

Runs daily after market close via GitHub Actions, analyzes ~550 stocks (S&P 500 + NASDAQ 100) and 11 SPDR Select Sector ETFs, and publishes results to GitHub Pages.

## Strategy

1. **Monitor institutional movements** — track sector ETF relative strength, volume, and analyst revision patterns to see where capital is flowing.
2. **Understand trends** — classify each sector's trend state (strong uptrend to strong downtrend) using a composite of breadth, momentum, and revision signals.
3. **Find optimal expression** — within trending sectors, identify leading stocks with the best combination of relative strength and fundamental quality.

## Architecture

```
                            ┌─ Sector ETFs ─── Sector Trend ─── Trend Scorer ─── trend_exporter ──┐
Wikipedia ─> universe.py ──>│                                                                      ├──> frontend/public/data/
                            └─ Tickers ─── [price, fundamental, news, analyst, macro] ──           │
                                           [analyzers + scoring] ── factor_model ── ranker ────────┘
```

### Dual Pipeline

- **Trend pipeline** (sector-centric): 11 SPDR ETFs (XLK/XLF/XLE/XLV/XLY/XLP/XLRE/XLI/XLU/XLB/XLC) + SPY benchmark → relative strength, breadth, analyst revisions, momentum, volume → composite trend strength (0-100) and trend state classification.
- **Stock scoring pipeline** (stock-centric): Per-ticker fundamental, technical, sentiment, and analyst analysis → 4-dimension absolute scoring → EMA-smoothed rating and ranking.

## Scoring

Each metric is mapped to 0-100 via piecewise linear breakpoints (not z-scores). Four investment dimensions:

| Dimension | Weight | Components |
|-----------|--------|------------|
| Earnings Visibility | 30% | Quality 60% + Growth 40% |
| Valuation Margin | 25% | Value (PE, Forward PE, PB, PS) |
| Catalyst Timeline | 20% | Trend 25% + Momentum 25% + Analyst 20% + Sentiment 15% + Volume 15% |
| Downside Control | 25% | Safety 60% + Volatility 40% |

Dimension weights shift with market regime: risk-on boosts Catalyst Timeline (+5%), risk-off boosts Downside Control (+5%).

### Rating Tiers

| Tier | Score |
|------|-------|
| Strong Buy | >= 75 |
| Buy | >= 60 |
| Hold | >= 40 |
| Sell | >= 25 |
| Strong Sell | < 25 |

Tier boundaries have +/- 2 point hysteresis. Composite scores are EMA-smoothed per dimension (`0.3 * raw + 0.7 * previous`).

## Quick Start

### Engine
```bash
pip install -r requirements.txt
python -m engine.main AAPL MSFT GOOGL    # Test with specific tickers
python -m engine.main                     # Full universe (~550 tickers)
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Dev server at localhost:5173
npm run build    # Production build
```

## Data Sources

- Price data & fundamentals: Yahoo Finance (via yfinance)
- News headlines: Yahoo Finance / Finviz
- Stock universe: Wikipedia (S&P 500 + NASDAQ 100 lists)
- Sector ETFs: 11 SPDR Select Sector ETFs + SPY benchmark
- Macro signals: VIX, S&P 500 vs SMA200, yield curve slope

## Tech Stack

- **Engine**: Python (pandas, yfinance, vaderSentiment)
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + recharts
- **CI/CD**: GitHub Actions (daily pipeline) + GitHub Pages
- **Cost**: Zero — free data, free compute, free hosting

## Disclaimer

For educational and informational purposes only. Not financial advice.
