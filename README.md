# Athene

Quantitative stock selection and trend identification tool for U.S. equity markets. Scores ~550 stocks using a three-factor multiplicative alpha model, tracks capital flows across 9 global asset classes, and analyzes sector-level trends across 11 GICS sectors.

Runs daily after market close via GitHub Actions and publishes results to GitHub Pages.

## Strategy

1. **Score individual stocks** — three-factor multiplicative model (VM x EV x Timing) ensures all conditions must align: reasonable valuation, visible earnings improvement, and favorable timing.
2. **Monitor institutional movements** — track sector ETF relative strength, breadth, and capital flows across risk/safe-haven assets to see where money is moving.
3. **Detect market turns** — leading indicators (credit spread velocity, breadth thrust, RFI acceleration) provide early warnings of direction changes.

## Architecture

```
                            ┌─ Sector ETFs ─── Sector Trend ─── Trend Scorer ─── trend_exporter ──┐
Wikipedia ─> universe.py ──>│                                                                      ├──> frontend/public/data/
                            ├─ Tickers ─── [price, fundamental, news, analyst, macro] ──           │
                            │               [analyzers + scoring] ── alpha_model ── ranker ────────┤
                            └─ Capital Flow ETFs ─── Capital Flow Analyzer ─── cf_exporter ────────┘
```

### Triple Pipeline

- **Stock scoring pipeline** (stock-centric): Per-ticker fundamental, technical, sentiment, and analyst analysis. Primary: alpha model (`Score = VM x EV x Timing / K`). Legacy composite model runs in parallel for IC validation.
- **Trend pipeline** (sector-centric): 11 SPDR ETFs + SPY benchmark. Five signals: relative strength (35%), breadth (25%), analyst revisions (15%), momentum (15%), volume (10%) -> composite trend strength (0-100) and trend state classification.
- **Capital flow pipeline** (macro): 9 ETFs across risk assets (SPY, VGK, EWJ, EEM, IBIT) and safe havens (GLD, TLT, BIL, LQD). Hybrid fund flows from shares outstanding (6 ETFs) + volume-price proxy (3 ETFs). Risk Flow Index, phase detection, and flow arrow visualization.

## Scoring

### Alpha Model (Primary)

Three-factor multiplicative model — all factors must be present. Any zero kills the score.

```
alpha_score = (VM x EV x Timing) / K    where K = 5000
```

| Factor | Formula | Measures |
|--------|---------|----------|
| Valuation Margin (VM) | `pe_base x growth_adj x 0.6 + fcf_yield x 0.4` | Mispricing — is the price reasonable? |
| Earnings Visibility (EV) | `visibility x direction_multiplier` | Fundamental support — is the opportunity real? |
| Timing | `reversal x (a + (1-a) x cycle_upside / 100)` | Cycle position + reversal — when to act? |

Each raw metric is mapped to 0-100 via piecewise linear breakpoints (not z-scores). Alpha model uses continuous scores (0-100). Higher = better risk-adjusted opportunity. See [CLAUDE.md](CLAUDE.md) for full scoring details.

## Quick Start

### Engine
```bash
pip install -r requirements.txt
python -m engine.main AAPL MSFT GOOGL    # Test with specific tickers
python -m engine.main                     # Full universe (~550 tickers)
python -m engine.add_ticker CPNG SE       # Add new tickers to universe
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
- Capital flow ETFs: 9 asset class ETFs — direct fund flows from shares outstanding
- Macro signals: VIX, S&P 500 vs SMA200, yield curve slope, credit spreads

## Tech Stack

- **Engine**: Python (pandas, yfinance, vaderSentiment)
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Lightweight Charts + recharts
- **CI/CD**: GitHub Actions (daily pipeline) + GitHub Pages
- **Cost**: Zero — free data, free compute, free hosting

## Disclaimer

For educational and informational purposes only. Not financial advice.
