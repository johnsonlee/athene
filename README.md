# Athene

US stock screening engine powered by GitHub Actions. Runs daily after market close, analyzes ~550 stocks (S&P 500 + NASDAQ 100), and publishes results to GitHub Pages.

## Features

- **Multi-factor scoring**: Fundamental (50%) + Technical (30%) + Sentiment (20%), absolute 0-100 scale
- **Absolute rating**: Ratings based on a stock's own metrics, not relative ranking — multiple stocks can share the same tier
- **Automated pipeline**: GitHub Actions runs daily at market close (with EMA smoothing and hysteresis)
- **Interactive frontend**: Sortable/filterable screener, candlestick charts with RSI/MACD/KDJ, sector treemap
- **Bilingual**: English and Chinese (i18n)
- **Zero cost**: Free data (Yahoo Finance), free compute (GitHub Actions), free hosting (GitHub Pages)

## Quick Start

### Run the engine locally
```bash
pip install -r requirements.txt
python -m engine.main AAPL MSFT GOOGL AMZN TSLA  # Test with 5 stocks
```

### Run the frontend locally
```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
Wikipedia ──> universe (550 tickers)
                │
                ├──> Price Data ──> Technical Analysis ──┐
                ├──> Financials ──> Fundamental Analysis ─┼──> Absolute Scoring ──> EMA Smoothing ──> Rating + Ranking ──> JSON
                └──> News ──────> Sentiment Analysis ────┘
```

## Scoring

Each metric is mapped to 0-100 via piecewise linear breakpoints (not z-scores). Sub-factors are aggregated with fixed weights:

- **Fundamental (50%)**: Value 25% + Quality 30% + Growth 25% + Safety 20%
- **Technical (30%)**: Trend 30% + Momentum 30% + Volatility 20% + Volume 20%
- **Sentiment (20%)**: VADER compound score mapped to 0-100

Composite scores are EMA-smoothed (`0.3 * raw + 0.7 * previous`) to reduce daily noise.

## Rating Tiers

| Tier | Score | Description |
|------|-------|-------------|
| Strong Buy | >= 75 | Excellent across all factors |
| Buy | >= 60 | Above average quality |
| Hold | >= 40 | Average |
| Sell | >= 25 | Below average |
| Strong Sell | < 25 | Poor across all factors |

Tier boundaries have +/- 2 point hysteresis to prevent oscillation.

## Disclaimer

For educational purposes only. Not financial advice.
