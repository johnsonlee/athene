import type { StockDetail } from '../../types';
import { formatScore, formatPercent, formatRatio } from '../../lib/formatters';

interface Props {
  detail: StockDetail;
}

interface Factor {
  name: string;
  score: number | null | undefined;
  weight: string;
  drivers: Driver[];
}

interface Driver {
  label: string;
  value: string;
  signal: 'bullish' | 'bearish' | 'neutral';
  explanation: string;
}

function signalColor(signal: string) {
  if (signal === 'bullish') return 'text-green-700 bg-green-50 dark:text-green-400 dark:bg-green-900/30';
  if (signal === 'bearish') return 'text-red-700 bg-red-50 dark:text-red-400 dark:bg-red-900/30';
  return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-700';
}

function scoreBar(score: number | null | undefined) {
  if (score == null) return null;
  // Map score roughly from -2..2 to 0..100%
  const pct = Math.max(0, Math.min(100, (score + 2) * 25));
  const color = score > 0.3 ? 'bg-green-500' : score < -0.3 ? 'bg-red-500' : 'bg-gray-400';
  return (
    <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-600">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function ScoreBreakdown({ detail }: Props) {
  const { fundamental: fund, technical: tech, sentiment: sent, ranking } = detail;
  if (!ranking) return null;

  const factors: Factor[] = [];

  // Fundamental breakdown
  const fundDrivers: Driver[] = [];
  if (fund) {
    if (fund.pe != null) {
      const signal = fund.pe < 20 ? 'bullish' : fund.pe > 35 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: 'P/E Ratio',
        value: formatRatio(fund.pe),
        signal,
        explanation: fund.pe < 20 ? 'Low valuation relative to earnings' :
          fund.pe > 35 ? 'High valuation relative to earnings' : 'Moderate valuation',
      });
    }
    if (fund.roe != null) {
      const signal = fund.roe > 0.20 ? 'bullish' : fund.roe < 0.10 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: 'ROE',
        value: formatPercent(fund.roe),
        signal,
        explanation: fund.roe > 0.20 ? 'Strong return on equity' :
          fund.roe < 0.10 ? 'Weak return on equity' : 'Average return on equity',
      });
    }
    if (fund.revenue_growth != null) {
      const signal = fund.revenue_growth > 0.10 ? 'bullish' : fund.revenue_growth < 0 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: 'Revenue Growth',
        value: formatPercent(fund.revenue_growth),
        signal,
        explanation: fund.revenue_growth > 0.10 ? 'Strong revenue growth' :
          fund.revenue_growth < 0 ? 'Revenue declining' : 'Modest revenue growth',
      });
    }
    if (fund.earnings_growth != null) {
      const signal = fund.earnings_growth > 0.10 ? 'bullish' : fund.earnings_growth < 0 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: 'Earnings Growth',
        value: formatPercent(fund.earnings_growth),
        signal,
        explanation: fund.earnings_growth > 0.10 ? 'Strong earnings growth' :
          fund.earnings_growth < 0 ? 'Earnings declining' : 'Modest earnings growth',
      });
    }
    if (fund.debt_to_equity != null) {
      const signal = fund.debt_to_equity < 50 ? 'bullish' : fund.debt_to_equity > 150 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: 'Debt/Equity',
        value: formatRatio(fund.debt_to_equity),
        signal,
        explanation: fund.debt_to_equity < 50 ? 'Low leverage, strong balance sheet' :
          fund.debt_to_equity > 150 ? 'High leverage, financial risk' : 'Moderate leverage',
      });
    }
    if (fund.profit_margin != null) {
      const signal = fund.profit_margin > 0.20 ? 'bullish' : fund.profit_margin < 0.05 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: 'Profit Margin',
        value: formatPercent(fund.profit_margin),
        signal,
        explanation: fund.profit_margin > 0.20 ? 'High profitability' :
          fund.profit_margin < 0.05 ? 'Low profitability' : 'Average profitability',
      });
    }
  }
  factors.push({
    name: 'Fundamental',
    score: ranking.fundamental_score,
    weight: '40%',
    drivers: fundDrivers,
  });

  // Technical breakdown
  const techDrivers: Driver[] = [];
  if (tech) {
    if (tech.trend_alignment != null) {
      const signal = tech.trend_alignment > 0.6 ? 'bullish' : tech.trend_alignment < 0.3 ? 'bearish' : 'neutral';
      techDrivers.push({
        label: 'Trend Alignment',
        value: formatPercent(tech.trend_alignment),
        signal,
        explanation: tech.trend_alignment > 0.6 ? 'Price above key moving averages (bullish trend)' :
          tech.trend_alignment < 0.3 ? 'Price below key moving averages (bearish trend)' :
            'Mixed trend signals',
      });
    }
    if (tech.rsi != null) {
      const signal = tech.rsi > 50 && tech.rsi < 70 ? 'bullish' :
        tech.rsi >= 70 ? 'bearish' : tech.rsi < 30 ? 'bullish' : 'neutral';
      techDrivers.push({
        label: 'RSI',
        value: formatRatio(tech.rsi),
        signal,
        explanation: tech.rsi >= 70 ? 'Overbought territory, potential pullback' :
          tech.rsi <= 30 ? 'Oversold territory, potential bounce' :
            tech.rsi > 50 ? 'Positive momentum' : 'Weak momentum',
      });
    }
    if (tech.macd_histogram != null) {
      const signal = tech.macd_histogram > 0 ? 'bullish' : 'bearish';
      techDrivers.push({
        label: 'MACD Histogram',
        value: formatRatio(tech.macd_histogram),
        signal,
        explanation: tech.macd_histogram > 0 ? 'Positive MACD momentum' : 'Negative MACD momentum',
      });
    }
    if (tech.bb_position != null) {
      const signal = tech.bb_position > 0.5 && tech.bb_position < 0.8 ? 'bullish' :
        tech.bb_position >= 0.8 ? 'bearish' : tech.bb_position < 0.2 ? 'bullish' : 'neutral';
      techDrivers.push({
        label: 'Bollinger Position',
        value: formatPercent(tech.bb_position),
        signal,
        explanation: tech.bb_position >= 0.8 ? 'Near upper band, potentially overextended' :
          tech.bb_position <= 0.2 ? 'Near lower band, potentially oversold' :
            'Within normal trading range',
      });
    }
    if (tech.volume_ratio != null) {
      const signal = tech.volume_ratio > 1.5 ? 'bullish' : tech.volume_ratio < 0.5 ? 'bearish' : 'neutral';
      techDrivers.push({
        label: 'Volume Ratio',
        value: `${tech.volume_ratio.toFixed(2)}x`,
        signal,
        explanation: tech.volume_ratio > 1.5 ? 'Above average volume, strong interest' :
          tech.volume_ratio < 0.5 ? 'Below average volume, low interest' : 'Normal volume',
      });
    }
  }
  factors.push({
    name: 'Technical',
    score: ranking.technical_score,
    weight: '35%',
    drivers: techDrivers,
  });

  // Sentiment breakdown
  const sentDrivers: Driver[] = [];
  if (sent) {
    const compound = sent.sentiment_compound;
    const signal = compound > 0.1 ? 'bullish' : compound < -0.1 ? 'bearish' : 'neutral';
    sentDrivers.push({
      label: 'News Sentiment',
      value: formatRatio(compound),
      signal,
      explanation: compound > 0.1 ? 'Positive news sentiment overall' :
        compound < -0.1 ? 'Negative news sentiment overall' : 'Neutral news sentiment',
    });
    sentDrivers.push({
      label: 'News Volume',
      value: `${sent.news_count} articles`,
      signal: sent.news_count >= 10 ? 'neutral' : 'neutral',
      explanation: `Based on ${sent.news_count} recent news articles`,
    });
  }
  factors.push({
    name: 'Sentiment',
    score: ranking.sentiment_score,
    weight: '25%',
    drivers: sentDrivers,
  });

  // Generate overall summary
  const bullishCount = factors.flatMap(f => f.drivers).filter(d => d.signal === 'bullish').length;
  const bearishCount = factors.flatMap(f => f.drivers).filter(d => d.signal === 'bearish').length;

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Rating Analysis</h2>

      {/* Summary */}
      <div className="mb-4 rounded-md bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-900 dark:text-gray-300">
        <strong>{detail.ticker}</strong> is rated <strong>{ranking.tier_label}</strong> (rank #{ranking.rank}, top {formatPercent(ranking.percentile)})
        with a composite score of <strong>{formatScore(ranking.composite_score)}</strong>.
        {' '}The analysis found <span className="font-medium text-green-700 dark:text-green-400">{bullishCount} bullish</span> and{' '}
        <span className="font-medium text-red-700 dark:text-red-400">{bearishCount} bearish</span> signals across{' '}
        {factors.flatMap(f => f.drivers).length} indicators.
      </div>

      {/* Factor breakdown */}
      <div className="space-y-4">
        {factors.map((factor) => (
          <div key={factor.name} className="border-t pt-3 first:border-0 first:pt-0 dark:border-gray-700">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900 dark:text-white">{factor.name}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">(Weight: {factor.weight})</span>
              </div>
              <span className="font-mono text-sm font-medium">
                {formatScore(factor.score)}
              </span>
            </div>
            {scoreBar(factor.score)}
            <div className="mt-2 space-y-1.5">
              {factor.drivers.map((driver) => (
                <div key={driver.label} className="flex items-start gap-2 text-sm">
                  <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${signalColor(driver.signal)}`}>
                    {driver.signal === 'bullish' ? '+' : driver.signal === 'bearish' ? '-' : '~'}
                  </span>
                  <div>
                    <span className="font-medium text-gray-800 dark:text-gray-200">{driver.label}: {driver.value}</span>
                    <span className="ml-1 text-gray-500 dark:text-gray-400">— {driver.explanation}</span>
                  </div>
                </div>
              ))}
              {factor.drivers.length === 0 && (
                <p className="text-xs text-gray-400 dark:text-gray-500">No data available for this factor</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
