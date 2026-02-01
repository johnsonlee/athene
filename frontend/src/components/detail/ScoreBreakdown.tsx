import type { StockDetail } from '../../types';
import { formatScore, formatPercent, formatPrice, formatLargeNumber, formatRatio } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

interface Props {
  detail: StockDetail;
}

interface Driver {
  label: string;
  value: string;
  signal: 'bullish' | 'bearish' | 'neutral';
  explanation: string;
}

type Signal = 'bullish' | 'bearish' | 'neutral';

function signalColor(signal: string) {
  if (signal === 'bullish') return 'text-green-700 bg-green-50 dark:text-green-400 dark:bg-green-900/30';
  if (signal === 'bearish') return 'text-red-700 bg-red-50 dark:text-red-400 dark:bg-red-900/30';
  return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-700';
}

function scoreBar(score: number | null | undefined) {
  if (score == null) return null;
  const pct = Math.max(0, Math.min(100, score));
  const color = score >= 60 ? 'bg-green-500' : score < 40 ? 'bg-red-500' : 'bg-gray-400';
  return (
    <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-600">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function sig(value: number | null | undefined, fn: (v: number) => Signal): Signal | undefined {
  return value != null ? fn(value) : undefined;
}

function Metric({ label, value, signal }: { label: string; value: string; signal?: Signal }) {
  const valueColor = signal === 'bullish'
    ? 'text-green-600 dark:text-green-400'
    : signal === 'bearish'
      ? 'text-red-600 dark:text-red-400'
      : 'text-gray-900 dark:text-white';
  const dotColor = signal === 'bullish' ? 'bg-green-500'
    : signal === 'bearish' ? 'bg-red-500'
      : signal === 'neutral' ? 'bg-gray-400 dark:bg-gray-500' : '';
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
        {signal && <span className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${dotColor}`} />}
        {label}
      </span>
      <span className={`font-mono text-xs font-medium ${valueColor}`}>{value}</span>
    </div>
  );
}

export function ScoreBreakdown({ detail }: Props) {
  const { t } = useI18n();
  const { fundamental: fund, technical: tech, sentiment: sent, ranking } = detail;
  if (!ranking) return null;

  // --- Fundamental drivers ---
  const fundDrivers: Driver[] = [];
  if (fund) {
    if (fund.pe != null) {
      const signal = fund.pe < 20 ? 'bullish' : fund.pe > 35 ? 'bearish' : 'neutral';
      fundDrivers.push({ label: t('metric.pe'), value: formatRatio(fund.pe), signal, explanation: t(`driver.pe.${signal}` as any) });
    }
    if (fund.roe != null) {
      const signal = fund.roe > 0.20 ? 'bullish' : fund.roe < 0.10 ? 'bearish' : 'neutral';
      fundDrivers.push({ label: t('metric.roe'), value: formatPercent(fund.roe), signal, explanation: t(`driver.roe.${signal}` as any) });
    }
    if (fund.revenue_growth != null) {
      const signal = fund.revenue_growth > 0.10 ? 'bullish' : fund.revenue_growth < 0 ? 'bearish' : 'neutral';
      fundDrivers.push({ label: t('metric.revGrowth'), value: formatPercent(fund.revenue_growth), signal, explanation: t(`driver.revGrowth.${signal}` as any) });
    }
    if (fund.earnings_growth != null) {
      const signal = fund.earnings_growth > 0.10 ? 'bullish' : fund.earnings_growth < 0 ? 'bearish' : 'neutral';
      fundDrivers.push({ label: t('metric.earnGrowth'), value: formatPercent(fund.earnings_growth), signal, explanation: t(`driver.earnGrowth.${signal}` as any) });
    }
    if (fund.debt_to_equity != null) {
      const signal = fund.debt_to_equity < 50 ? 'bullish' : fund.debt_to_equity > 150 ? 'bearish' : 'neutral';
      fundDrivers.push({ label: t('metric.debtEquity'), value: formatRatio(fund.debt_to_equity), signal, explanation: t(`driver.debt.${signal}` as any) });
    }
    if (fund.profit_margin != null) {
      const signal = fund.profit_margin > 0.20 ? 'bullish' : fund.profit_margin < 0.05 ? 'bearish' : 'neutral';
      fundDrivers.push({ label: t('metric.profitMargin'), value: formatPercent(fund.profit_margin), signal, explanation: t(`driver.margin.${signal}` as any) });
    }
  }

  // --- Technical drivers ---
  const techDrivers: Driver[] = [];
  if (tech) {
    if (tech.trend_alignment != null) {
      const signal = tech.trend_alignment > 0.6 ? 'bullish' : tech.trend_alignment < 0.3 ? 'bearish' : 'neutral';
      techDrivers.push({ label: t('metric.trendAlignment'), value: formatPercent(tech.trend_alignment), signal, explanation: t(`driver.trend.${signal}` as any) });
    }
    if (tech.rsi != null) {
      const signal = tech.rsi > 50 && tech.rsi < 70 ? 'bullish' : tech.rsi >= 70 ? 'bearish' : tech.rsi < 30 ? 'bullish' : 'neutral';
      const rsiKey = tech.rsi >= 70 ? 'overbought' : tech.rsi <= 30 ? 'oversold' : tech.rsi > 50 ? 'positive' : 'weak';
      techDrivers.push({ label: t('metric.rsi'), value: formatRatio(tech.rsi), signal, explanation: t(`driver.rsi.${rsiKey}` as any) });
    }
    if (tech.macd_histogram != null) {
      const signal = tech.macd_histogram > 0 ? 'bullish' : 'bearish';
      techDrivers.push({ label: t('metric.macdHist'), value: formatRatio(tech.macd_histogram), signal, explanation: t(`driver.macd.${signal}` as any) });
    }
    if (tech.bb_position != null) {
      const signal = tech.bb_position > 0.5 && tech.bb_position < 0.8 ? 'bullish' : tech.bb_position >= 0.8 ? 'bearish' : tech.bb_position < 0.2 ? 'bullish' : 'neutral';
      const bbKey = tech.bb_position >= 0.8 ? 'high' : tech.bb_position <= 0.2 ? 'low' : 'normal';
      techDrivers.push({ label: t('metric.bbPosition'), value: formatPercent(tech.bb_position), signal, explanation: t(`driver.bb.${bbKey}` as any) });
    }
    if (tech.volume_ratio != null) {
      const signal = tech.volume_ratio > 1.5 ? 'bullish' : tech.volume_ratio < 0.5 ? 'bearish' : 'neutral';
      const volKey = tech.volume_ratio > 1.5 ? 'high' : tech.volume_ratio < 0.5 ? 'low' : 'normal';
      techDrivers.push({ label: t('metric.volRatio'), value: `${tech.volume_ratio.toFixed(2)}x`, signal, explanation: t(`driver.vol.${volKey}` as any) });
    }
  }

  // --- Sentiment drivers ---
  const sentDrivers: Driver[] = [];
  if (sent) {
    const compound = sent.sentiment_compound;
    const signal = compound > 0.1 ? 'bullish' : compound < -0.1 ? 'bearish' : 'neutral';
    sentDrivers.push({ label: t('metric.newsSentiment'), value: formatRatio(compound), signal, explanation: t(`driver.sentiment.${signal}` as any) });
    sentDrivers.push({ label: t('metric.newsVolume'), value: t('detail.articles', { count: sent.news_count }), signal: 'neutral', explanation: t('driver.newsVolume', { count: sent.news_count }) });
  }

  const allDrivers = [...fundDrivers, ...techDrivers, ...sentDrivers];
  const bullishCount = allDrivers.filter(d => d.signal === 'bullish').length;
  const bearishCount = allDrivers.filter(d => d.signal === 'bearish').length;
  const keyBullish = allDrivers.filter(d => d.signal === 'bullish').slice(0, 3);
  const keyBearish = allDrivers.filter(d => d.signal === 'bearish').slice(0, 3);

  // Sort headlines by date desc
  const headlines = [...(detail.headlines || [])].sort((a, b) => (b.date || '').localeCompare(a.date || ''));

  const factors = [
    { name: t('detail.fundamentals'), score: ranking.fundamental_score, weight: '40%', drivers: fundDrivers },
    { name: t('detail.technical'), score: ranking.technical_score, weight: '35%', drivers: techDrivers },
    { name: t('detail.sentiment'), score: ranking.sentiment_score, weight: '25%', drivers: sentDrivers },
  ];

  // Determine strongest and weakest factor (by score)
  const validFactors = factors.filter(f => f.score != null);
  const strongestFactor = validFactors.length > 0 ? validFactors.reduce((a, b) => (a.score ?? 0) > (b.score ?? 0) ? a : b) : null;
  const weakestFactor = validFactors.length > 1 ? validFactors.reduce((a, b) => (a.score ?? 100) < (b.score ?? 100) ? a : b) : null;

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">{t('detail.ratingAnalysis')}</h2>

      {/* Summary */}
      <div className="mb-4 rounded-md bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-900 dark:text-gray-300">
        <p>
          {t('detail.ratedAs', {
            ticker: detail.ticker,
            tier: t(`tier.${ranking.tier}` as any),
            rank: ranking.rank,
            pct: formatPercent(ranking.percentile),
            score: formatScore(ranking.composite_score),
          })}
          {' '}{t('detail.signalSummary', { bullish: bullishCount, bearish: bearishCount, total: allDrivers.length })}
        </p>

        {/* Factor highlights */}
        {(strongestFactor || weakestFactor) && (
          <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
            {strongestFactor && t('detail.strongestFactor', { factor: strongestFactor.name, score: formatScore(strongestFactor.score) })}
            {strongestFactor && weakestFactor && ' · '}
            {weakestFactor && weakestFactor !== strongestFactor && t('detail.weakestFactor', { factor: weakestFactor.name, score: formatScore(weakestFactor.score) })}
          </p>
        )}

        {/* Key strengths & risks */}
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {keyBullish.length > 0 && (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-green-600 dark:text-green-400">{t('detail.keyStrengths')}</p>
              <ul className="space-y-0.5">
                {keyBullish.map(d => (
                  <li key={d.label} className="flex items-center gap-1 text-xs">
                    <span className="text-green-600 dark:text-green-400">+</span>
                    <span>{d.label}: {d.value}</span>
                    <span className="text-gray-400 dark:text-gray-500">— {d.explanation}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {keyBearish.length > 0 && (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-red-600 dark:text-red-400">{t('detail.keyRisks')}</p>
              <ul className="space-y-0.5">
                {keyBearish.map(d => (
                  <li key={d.label} className="flex items-center gap-1 text-xs">
                    <span className="text-red-600 dark:text-red-400">−</span>
                    <span>{d.label}: {d.value}</span>
                    <span className="text-gray-400 dark:text-gray-500">— {d.explanation}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Factor sections */}
      <div className="space-y-4">
        {factors.map((factor, fi) => (
          <div key={factor.name} className="border-t pt-3 first:border-0 first:pt-0 dark:border-gray-700">
            {/* Factor header + score */}
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

            {/* Key driver signals */}
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

            {/* Additional metrics per factor */}
            {fi === 0 && fund && (
              <div className="mt-3 grid grid-cols-2 gap-x-4 border-t pt-2 dark:border-gray-700">
                <Metric label={t('metric.fwdPe')} value={formatRatio(fund.forward_pe)}
                  signal={sig(fund.forward_pe, v => v < 18 ? 'bullish' : v > 30 ? 'bearish' : 'neutral')} />
                <Metric label={t('metric.pb')} value={formatRatio(fund.pb)}
                  signal={sig(fund.pb, v => v < 3 ? 'bullish' : v > 5 ? 'bearish' : 'neutral')} />
                <Metric label={t('metric.ps')} value={formatRatio(fund.ps)}
                  signal={sig(fund.ps, v => v < 3 ? 'bullish' : v > 10 ? 'bearish' : 'neutral')} />
                <Metric label={t('metric.roa')} value={formatPercent(fund.roa)}
                  signal={sig(fund.roa, v => v > 0.10 ? 'bullish' : v < 0.03 ? 'bearish' : 'neutral')} />
                <Metric label={t('metric.marketCap')} value={formatLargeNumber(fund.market_cap)} />
                <Metric label={t('metric.divYield')} value={formatPercent(fund.dividend_yield)} />
                <Metric label={t('metric.beta')} value={formatRatio(fund.beta)} />
                <Metric label={t('metric.52wHigh')} value={formatPrice(fund.high_52w)} />
                <Metric label={t('metric.52wLow')} value={formatPrice(fund.low_52w)} />
              </div>
            )}

            {fi === 1 && tech && (
              <div className="mt-3 grid grid-cols-2 gap-x-4 border-t pt-2 dark:border-gray-700">
                <Metric label={t('metric.sma20')} value={formatPrice(tech.sma_20)}
                  signal={tech.close != null && tech.sma_20 != null ? (tech.close > tech.sma_20 ? 'bullish' : 'bearish') : undefined} />
                <Metric label={t('metric.sma50')} value={formatPrice(tech.sma_50)}
                  signal={tech.close != null && tech.sma_50 != null ? (tech.close > tech.sma_50 ? 'bullish' : 'bearish') : undefined} />
                <Metric label={t('metric.sma200')} value={formatPrice(tech.sma_200)}
                  signal={tech.close != null && tech.sma_200 != null ? (tech.close > tech.sma_200 ? 'bullish' : 'bearish') : undefined} />
                <Metric label={t('metric.macd')} value={formatRatio(tech.macd_line)}
                  signal={sig(tech.macd_line, v => v > 0 ? 'bullish' : 'bearish')} />
                <Metric label={t('metric.stochK')} value={formatRatio(tech.stoch_k)}
                  signal={sig(tech.stoch_k, v => v >= 80 ? 'bearish' : v <= 20 ? 'bullish' : 'neutral')} />
                <Metric label={t('metric.stochD')} value={formatRatio(tech.stoch_d)} />
              </div>
            )}

            {fi === 2 && sent && (
              <div className="mt-3 border-t pt-2 dark:border-gray-700">
                <div className="mb-2">
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">{t('group.sentimentBreakdown')}</p>
                  <SentimentBar pos={sent.sentiment_pos} neg={sent.sentiment_neg} neu={sent.sentiment_neu} />
                </div>
                {headlines.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">{t('detail.recentNews')}</p>
                    <ul className="space-y-1.5">
                      {headlines.map((h, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-sm">
                          <span className={`mt-0.5 shrink-0 rounded px-1 py-0.5 text-[10px] font-bold leading-none ${
                            h.sentiment === 'positive' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : h.sentiment === 'negative' ? 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              : 'bg-gray-50 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                          }`}>{h.sentiment === 'positive' ? '+' : h.sentiment === 'negative' ? '−' : '~'}</span>
                          <span>
                            {h.date && <span className="mr-1.5 font-mono text-[10px] text-gray-400 dark:text-gray-500">{h.date}</span>}
                            {h.url ? (
                              <a href={h.url} target="_blank" rel="noopener noreferrer"
                                className="text-blue-600 hover:underline dark:text-blue-400">{h.title}</a>
                            ) : (
                              <span className="text-gray-700 dark:text-gray-300">{h.title}</span>
                            )}
                            {h.publisher && (
                              <span className="ml-1 text-xs text-gray-400 dark:text-gray-500">— {h.publisher}</span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function SentimentBar({ pos, neg, neu }: { pos: number; neg: number; neu: number }) {
  const total = pos + neg + neu || 1;
  const pPos = (pos / total) * 100;
  const pNeg = (neg / total) * 100;
  const pNeu = (neu / total) * 100;
  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full">
        <div className="bg-green-500" style={{ width: `${pPos}%` }} />
        <div className="bg-gray-400 dark:bg-gray-500" style={{ width: `${pNeu}%` }} />
        <div className="bg-red-500" style={{ width: `${pNeg}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-[10px]">
        <span className="text-green-600 dark:text-green-400">{pPos.toFixed(0)}% +</span>
        <span className="text-gray-500 dark:text-gray-400">{pNeu.toFixed(0)}% ~</span>
        <span className="text-red-600 dark:text-red-400">{pNeg.toFixed(0)}% -</span>
      </div>
    </div>
  );
}
