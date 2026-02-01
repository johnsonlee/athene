import type { StockDetail } from '../../types';
import { formatScore, formatPercent, formatRatio } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

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
  const { t } = useI18n();
  const { fundamental: fund, technical: tech, sentiment: sent, ranking } = detail;
  if (!ranking) return null;

  const factors: Factor[] = [];

  // Fundamental breakdown
  const fundDrivers: Driver[] = [];
  if (fund) {
    if (fund.pe != null) {
      const signal = fund.pe < 20 ? 'bullish' : fund.pe > 35 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: t('metric.pe'),
        value: formatRatio(fund.pe),
        signal,
        explanation: t(`driver.pe.${signal}` as any),
      });
    }
    if (fund.roe != null) {
      const signal = fund.roe > 0.20 ? 'bullish' : fund.roe < 0.10 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: t('metric.roe'),
        value: formatPercent(fund.roe),
        signal,
        explanation: t(`driver.roe.${signal}` as any),
      });
    }
    if (fund.revenue_growth != null) {
      const signal = fund.revenue_growth > 0.10 ? 'bullish' : fund.revenue_growth < 0 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: t('metric.revGrowth'),
        value: formatPercent(fund.revenue_growth),
        signal,
        explanation: t(`driver.revGrowth.${signal}` as any),
      });
    }
    if (fund.earnings_growth != null) {
      const signal = fund.earnings_growth > 0.10 ? 'bullish' : fund.earnings_growth < 0 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: t('metric.earnGrowth'),
        value: formatPercent(fund.earnings_growth),
        signal,
        explanation: t(`driver.earnGrowth.${signal}` as any),
      });
    }
    if (fund.debt_to_equity != null) {
      const signal = fund.debt_to_equity < 50 ? 'bullish' : fund.debt_to_equity > 150 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: t('metric.debtEquity'),
        value: formatRatio(fund.debt_to_equity),
        signal,
        explanation: t(`driver.debt.${signal}` as any),
      });
    }
    if (fund.profit_margin != null) {
      const signal = fund.profit_margin > 0.20 ? 'bullish' : fund.profit_margin < 0.05 ? 'bearish' : 'neutral';
      fundDrivers.push({
        label: t('metric.profitMargin'),
        value: formatPercent(fund.profit_margin),
        signal,
        explanation: t(`driver.margin.${signal}` as any),
      });
    }
  }
  factors.push({
    name: t('detail.fundamentals'),
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
        label: t('metric.trendAlignment'),
        value: formatPercent(tech.trend_alignment),
        signal,
        explanation: t(`driver.trend.${signal}` as any),
      });
    }
    if (tech.rsi != null) {
      const signal = tech.rsi > 50 && tech.rsi < 70 ? 'bullish' :
        tech.rsi >= 70 ? 'bearish' : tech.rsi < 30 ? 'bullish' : 'neutral';
      const rsiKey = tech.rsi >= 70 ? 'overbought' : tech.rsi <= 30 ? 'oversold' :
        tech.rsi > 50 ? 'positive' : 'weak';
      techDrivers.push({
        label: t('metric.rsi'),
        value: formatRatio(tech.rsi),
        signal,
        explanation: t(`driver.rsi.${rsiKey}` as any),
      });
    }
    if (tech.macd_histogram != null) {
      const signal = tech.macd_histogram > 0 ? 'bullish' : 'bearish';
      techDrivers.push({
        label: t('metric.macdHist'),
        value: formatRatio(tech.macd_histogram),
        signal,
        explanation: t(`driver.macd.${signal}` as any),
      });
    }
    if (tech.bb_position != null) {
      const signal = tech.bb_position > 0.5 && tech.bb_position < 0.8 ? 'bullish' :
        tech.bb_position >= 0.8 ? 'bearish' : tech.bb_position < 0.2 ? 'bullish' : 'neutral';
      const bbKey = tech.bb_position >= 0.8 ? 'high' : tech.bb_position <= 0.2 ? 'low' : 'normal';
      techDrivers.push({
        label: t('metric.bbPosition'),
        value: formatPercent(tech.bb_position),
        signal,
        explanation: t(`driver.bb.${bbKey}` as any),
      });
    }
    if (tech.volume_ratio != null) {
      const signal = tech.volume_ratio > 1.5 ? 'bullish' : tech.volume_ratio < 0.5 ? 'bearish' : 'neutral';
      const volKey = tech.volume_ratio > 1.5 ? 'high' : tech.volume_ratio < 0.5 ? 'low' : 'normal';
      techDrivers.push({
        label: t('metric.volRatio'),
        value: `${tech.volume_ratio.toFixed(2)}x`,
        signal,
        explanation: t(`driver.vol.${volKey}` as any),
      });
    }
  }
  factors.push({
    name: t('detail.technical'),
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
      label: t('metric.newsSentiment'),
      value: formatRatio(compound),
      signal,
      explanation: t(`driver.sentiment.${signal}` as any),
    });
    sentDrivers.push({
      label: t('metric.newsVolume'),
      value: t('detail.articles', { count: sent.news_count }),
      signal: 'neutral',
      explanation: t('driver.newsVolume', { count: sent.news_count }),
    });
  }
  factors.push({
    name: t('detail.sentiment'),
    score: ranking.sentiment_score,
    weight: '25%',
    drivers: sentDrivers,
  });

  // Generate overall summary
  const bullishCount = factors.flatMap(f => f.drivers).filter(d => d.signal === 'bullish').length;
  const bearishCount = factors.flatMap(f => f.drivers).filter(d => d.signal === 'bearish').length;
  const totalIndicators = factors.flatMap(f => f.drivers).length;

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">{t('detail.ratingAnalysis')}</h2>

      {/* Summary */}
      <div className="mb-4 rounded-md bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-900 dark:text-gray-300">
        {t('detail.ratedAs', {
          ticker: detail.ticker,
          tier: t(`tier.${ranking.tier}` as any),
          rank: ranking.rank,
          pct: formatPercent(ranking.percentile),
          score: formatScore(ranking.composite_score),
        })}
        {' '}{t('detail.signalSummary', { bullish: bullishCount, bearish: bearishCount, total: totalIndicators })}
      </div>

      {/* Factor breakdown */}
      <div className="space-y-4">
        {factors.map((factor) => (
          <div key={factor.name} className="border-t pt-3 first:border-0 first:pt-0 dark:border-gray-700">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900 dark:text-white">{factor.name}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">({t('detail.weight', { weight: factor.weight })})</span>
              </div>
              <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
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
                <p className="text-xs text-gray-400 dark:text-gray-500">{t('detail.noFactorData')}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
