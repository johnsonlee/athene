# Athene

US stock screening engine powered by GitHub Actions. Runs daily after market close, analyzes ~550 stocks (S&P 500 + NASDAQ 100), and publishes results to GitHub Pages.

## Features

- **Multi-factor scoring**: Fundamental (40%) + Technical (35%) + Sentiment (25%)
- **Automated pipeline**: GitHub Actions runs daily at market close
- **Interactive frontend**: Sortable/filterable screener, candlestick charts, radar plots
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
                ├──> Financials ──> Fundamental Analysis ─┼──> Multi-Factor Score ──> Rankings ──> JSON
                └──> News ──────> Sentiment Analysis ────┘
```

## Rating Tiers

| Tier | Percentile | Description |
|------|-----------|-------------|
| Strong Buy | Top 10% | Highest composite scores |
| Buy | 10-30% | Above average |
| Hold | 30-70% | Average |
| Sell | 70-90% | Below average |
| Strong Sell | Bottom 10% | Lowest composite scores |

## Disclaimer

For educational purposes only. Not financial advice.
