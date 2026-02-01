import { useParams, Link } from 'react-router-dom';
import { useStockDetail } from '../../hooks/useStockDetail';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ScoreBadge } from '../common/ScoreBadge';
import { PriceChart } from './PriceChart';
import { IndicatorCharts } from './IndicatorCharts';
import { ScoreRadar } from './ScoreRadar';
import { ScoreBreakdown } from './ScoreBreakdown';
import { formatScore, formatPrice, formatPercent, formatLargeNumber, formatRatio } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

export function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const { data, loading, error } = useStockDetail(ticker);
  const { t } = useI18n();

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return <p className="text-center text-red-600 dark:text-red-400">{t('common.error', { message: error })}</p>;
  if (!data) return <p className="text-center text-gray-500 dark:text-gray-400">{t('common.noDataFound')}</p>;

  const { fundamental, technical, sentiment, ranking } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/screener" className="text-sm text-blue-600 hover:underline dark:text-blue-400">&larr; {t('detail.backToScreener')}</Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{ticker}</h1>
          {fundamental?.current_price && (
            <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">
              {formatPrice(fundamental.current_price)}
            </p>
          )}
        </div>
        {ranking && (
          <div className="text-right">
            <p className="text-sm text-gray-500 dark:text-gray-400">{t('detail.rank', { rank: ranking.rank })}</p>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{formatScore(ranking.composite_score)}</p>
            <ScoreBadge tier={ranking.tier} label={t(`tier.${ranking.tier}` as any)} />
          </div>
        )}
      </div>

      {/* Price Chart */}
      <PriceChart prices={data.prices} ticker={ticker!} />

      {/* Indicator Sub-charts */}
      <IndicatorCharts prices={data.prices} technical={technical} />

      {/* Score Breakdown - WHY this rating */}
      <ScoreBreakdown detail={data} />

      {/* Score Radar + Cards */}
      <div className="grid gap-6 lg:grid-cols-3">
        <ScoreRadar ranking={ranking} />

        {/* Fundamental card */}
        <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
          <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">{t('detail.fundamentals')}</h3>
          {fundamental ? (
            <dl className="space-y-0.5 text-sm">
              <GroupLabel text={t('group.valuation')} />
              <MetricRow label={t('metric.pe')} value={formatRatio(fundamental.pe)}
                signal={sig(fundamental.pe, v => v < 20 ? 'bullish' : v > 35 ? 'bearish' : 'neutral')} />
              <MetricRow label={t('metric.fwdPe')} value={formatRatio(fundamental.forward_pe)}
                signal={sig(fundamental.forward_pe, v => v < 18 ? 'bullish' : v > 30 ? 'bearish' : 'neutral')} />
              <MetricRow label={t('metric.pb')} value={formatRatio(fundamental.pb)}
                signal={sig(fundamental.pb, v => v < 3 ? 'bullish' : v > 5 ? 'bearish' : 'neutral')} />
              <MetricRow label={t('metric.ps')} value={formatRatio(fundamental.ps)}
                signal={sig(fundamental.ps, v => v < 3 ? 'bullish' : v > 10 ? 'bearish' : 'neutral')} />

              <GroupLabel text={t('group.profitability')} />
              <MetricRow label={t('metric.roe')} value={formatPercent(fundamental.roe)}
                signal={sig(fundamental.roe, v => v > 0.20 ? 'bullish' : v < 0.10 ? 'bearish' : 'neutral')} />
              <MetricRow label={t('metric.roa')} value={formatPercent(fundamental.roa)}
                signal={sig(fundamental.roa, v => v > 0.10 ? 'bullish' : v < 0.03 ? 'bearish' : 'neutral')} />
              <MetricRow label={t('metric.profitMargin')} value={formatPercent(fundamental.profit_margin)}
                signal={sig(fundamental.profit_margin, v => v > 0.20 ? 'bullish' : v < 0.05 ? 'bearish' : 'neutral')} />

              <GroupLabel text={t('group.growth')} />
              <MetricRow label={t('metric.revGrowth')} value={formatPercent(fundamental.revenue_growth)}
                signal={sig(fundamental.revenue_growth, v => v > 0.10 ? 'bullish' : v < 0 ? 'bearish' : 'neutral')} />
              <MetricRow label={t('metric.earnGrowth')} value={formatPercent(fundamental.earnings_growth)}
                signal={sig(fundamental.earnings_growth, v => v > 0.10 ? 'bullish' : v < 0 ? 'bearish' : 'neutral')} />

              <GroupLabel text={t('group.balanceSheet')} />
              <MetricRow label={t('metric.debtEquity')} value={formatRatio(fundamental.debt_to_equity)}
                signal={sig(fundamental.debt_to_equity, v => v < 50 ? 'bullish' : v > 150 ? 'bearish' : 'neutral')} />
              <MetricRow label={t('metric.marketCap')} value={formatLargeNumber(fundamental.market_cap)} />

              <GroupLabel text={t('group.market')} />
              <MetricRow label={t('metric.divYield')} value={formatPercent(fundamental.dividend_yield)} />
              <MetricRow label={t('metric.beta')} value={formatRatio(fundamental.beta)} />
              <MetricRow label={t('metric.52wHigh')} value={formatPrice(fundamental.high_52w)} />
              <MetricRow label={t('metric.52wLow')} value={formatPrice(fundamental.low_52w)} />
            </dl>
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500">{t('detail.noData')}</p>
          )}
        </div>

        {/* Technical + Sentiment card */}
        <div className="space-y-4">
          <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
            <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">{t('detail.technical')}</h3>
            {technical ? (
              <dl className="space-y-0.5 text-sm">
                <GroupLabel text={t('group.trend')} />
                <MetricRow label={t('metric.sma20')} value={formatPrice(technical.sma_20)} />
                <MetricRow label={t('metric.sma50')} value={formatPrice(technical.sma_50)} />
                <MetricRow label={t('metric.sma200')} value={formatPrice(technical.sma_200)} />

                <GroupLabel text={t('group.momentum')} />
                <MetricRow label={t('metric.rsi')} value={formatRatio(technical.rsi)}
                  signal={sig(technical.rsi, v => v >= 70 ? 'bearish' : v <= 30 ? 'bullish' : v > 50 ? 'bullish' : 'neutral')}
                  bar={technical.rsi != null ? { value: technical.rsi, min: 0, max: 100 } : undefined} />
                <MetricRow label={t('metric.macd')} value={formatRatio(technical.macd_line)}
                  signal={sig(technical.macd_line, v => v > 0 ? 'bullish' : 'bearish')} />
                <MetricRow label={t('metric.macdHist')} value={formatRatio(technical.macd_histogram)}
                  signal={sig(technical.macd_histogram, v => v > 0 ? 'bullish' : 'bearish')} />

                <GroupLabel text={t('group.volatility')} />
                <MetricRow label={t('metric.bbPosition')} value={formatRatio(technical.bb_position)}
                  signal={sig(technical.bb_position, v => v >= 0.8 ? 'bearish' : v <= 0.2 ? 'bullish' : 'neutral')}
                  bar={technical.bb_position != null ? { value: technical.bb_position, min: 0, max: 1 } : undefined} />
                <MetricRow label={t('metric.stochK')} value={formatRatio(technical.stoch_k)}
                  signal={sig(technical.stoch_k, v => v >= 80 ? 'bearish' : v <= 20 ? 'bullish' : 'neutral')} />
                <MetricRow label={t('metric.stochD')} value={formatRatio(technical.stoch_d)} />

                <GroupLabel text={t('group.volumeActivity')} />
                <MetricRow label={t('metric.volRatio')} value={technical.volume_ratio != null ? `${technical.volume_ratio.toFixed(2)}x` : 'N/A'}
                  signal={sig(technical.volume_ratio, v => v > 1.5 ? 'bullish' : v < 0.5 ? 'bearish' : 'neutral')} />
              </dl>
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500">{t('detail.noData')}</p>
            )}
          </div>

          <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
            <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">{t('detail.sentiment')}</h3>
            {sentiment ? (
              <>
                <dl className="space-y-0.5 text-sm">
                  <MetricRow label={t('metric.compound')} value={formatRatio(sentiment.sentiment_compound)}
                    signal={sentiment.sentiment_compound > 0.1 ? 'bullish' : sentiment.sentiment_compound < -0.1 ? 'bearish' : 'neutral'} />
                  <MetricRow label={t('metric.newsCount')} value={String(sentiment.news_count)} />
                </dl>
                <div className="mt-3">
                  <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">{t('group.sentimentBreakdown')}</p>
                  <SentimentBar pos={sentiment.sentiment_pos} neg={sentiment.sentiment_neg} neu={sentiment.sentiment_neu} />
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500">{t('detail.noData')}</p>
            )}
            {data.headlines && data.headlines.length > 0 && (
              <div className="mt-3 border-t pt-3 dark:border-gray-700">
                <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">{t('detail.recentNews')}</h4>
                <ul className="space-y-1.5">
                  {data.headlines.map((h, i) => (
                    <li key={i} className="text-sm">
                      {h.url ? (
                        <a href={h.url} target="_blank" rel="noopener noreferrer"
                          className="text-blue-600 hover:underline dark:text-blue-400">
                          {h.title}
                        </a>
                      ) : (
                        <span className="text-gray-700 dark:text-gray-300">{h.title}</span>
                      )}
                      {h.publisher && (
                        <span className="ml-1 text-xs text-gray-400 dark:text-gray-500">— {h.publisher}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

type Signal = 'bullish' | 'bearish' | 'neutral';

/** Compute signal from a nullable value */
function sig(value: number | null | undefined, fn: (v: number) => Signal): Signal | undefined {
  return value != null ? fn(value) : undefined;
}

function GroupLabel({ text }: { text: string }) {
  return (
    <div className="pb-0.5 pt-2 first:pt-0">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">{text}</span>
    </div>
  );
}

function MetricRow({ label, value, signal, bar }: {
  label: string;
  value: string;
  signal?: Signal;
  bar?: { value: number; min: number; max: number };
}) {
  const valueColor = signal === 'bullish'
    ? 'text-green-600 dark:text-green-400'
    : signal === 'bearish'
      ? 'text-red-600 dark:text-red-400'
      : 'text-gray-900 dark:text-white';
  const dotColor = signal === 'bullish'
    ? 'bg-green-500'
    : signal === 'bearish'
      ? 'bg-red-500'
      : signal === 'neutral'
        ? 'bg-gray-400 dark:bg-gray-500'
        : '';

  return (
    <div>
      <div className="flex items-center justify-between py-0.5">
        <dt className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
          {signal && <span className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${dotColor}`} />}
          {label}
        </dt>
        <dd className={`font-mono text-xs font-medium ${valueColor}`}>{value}</dd>
      </div>
      {bar && (
        <div className="mb-0.5 ml-3 h-1 rounded-full bg-gray-200 dark:bg-gray-600">
          <div
            className={`h-1 rounded-full ${signal === 'bullish' ? 'bg-green-500' : signal === 'bearish' ? 'bg-red-500' : 'bg-blue-400'}`}
            style={{ width: `${Math.max(0, Math.min(100, ((bar.value - bar.min) / (bar.max - bar.min)) * 100))}%` }}
          />
        </div>
      )}
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
        <span className="text-green-600 dark:text-green-400">{(pPos).toFixed(0)}% +</span>
        <span className="text-gray-500 dark:text-gray-400">{(pNeu).toFixed(0)}% ~</span>
        <span className="text-red-600 dark:text-red-400">{(pNeg).toFixed(0)}% -</span>
      </div>
    </div>
  );
}
