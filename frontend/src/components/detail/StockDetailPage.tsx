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
  if (error) return <p className="text-center text-red-600">{t('common.error', { message: error })}</p>;
  if (!data) return <p className="text-center text-gray-500 dark:text-gray-400">{t('common.noDataFound')}</p>;

  const { fundamental, technical, sentiment, ranking } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/screener" className="text-sm text-blue-600 hover:underline">&larr; {t('detail.backToScreener')}</Link>
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
            <p className="text-lg font-bold">{formatScore(ranking.composite_score)}</p>
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
            <dl className="space-y-1 text-sm">
              <MetricRow label={t('metric.pe')} value={formatRatio(fundamental.pe)} />
              <MetricRow label={t('metric.fwdPe')} value={formatRatio(fundamental.forward_pe)} />
              <MetricRow label={t('metric.pb')} value={formatRatio(fundamental.pb)} />
              <MetricRow label={t('metric.ps')} value={formatRatio(fundamental.ps)} />
              <MetricRow label={t('metric.roe')} value={formatPercent(fundamental.roe)} />
              <MetricRow label={t('metric.roa')} value={formatPercent(fundamental.roa)} />
              <MetricRow label={t('metric.revGrowth')} value={formatPercent(fundamental.revenue_growth)} />
              <MetricRow label={t('metric.earnGrowth')} value={formatPercent(fundamental.earnings_growth)} />
              <MetricRow label={t('metric.debtEquity')} value={formatRatio(fundamental.debt_to_equity)} />
              <MetricRow label={t('metric.marketCap')} value={formatLargeNumber(fundamental.market_cap)} />
              <MetricRow label={t('metric.profitMargin')} value={formatPercent(fundamental.profit_margin)} />
              <MetricRow label={t('metric.divYield')} value={formatPercent(fundamental.dividend_yield)} />
              <MetricRow label={t('metric.beta')} value={formatRatio(fundamental.beta)} />
              <MetricRow label={t('metric.52wHigh')} value={formatPrice(fundamental.high_52w)} />
              <MetricRow label={t('metric.52wLow')} value={formatPrice(fundamental.low_52w)} />
            </dl>
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500">{t('detail.noData')}</p>
          )}
        </div>

        {/* Sentiment + Technical card */}
        <div className="space-y-4">
          <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
            <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">{t('detail.technical')}</h3>
            {technical ? (
              <dl className="space-y-1 text-sm">
                <MetricRow label={t('metric.rsi')} value={formatRatio(technical.rsi)} />
                <MetricRow label={t('metric.macd')} value={formatRatio(technical.macd_line)} />
                <MetricRow label={t('metric.macdHist')} value={formatRatio(technical.macd_histogram)} />
                <MetricRow label={t('metric.sma20')} value={formatPrice(technical.sma_20)} />
                <MetricRow label={t('metric.sma50')} value={formatPrice(technical.sma_50)} />
                <MetricRow label={t('metric.sma200')} value={formatPrice(technical.sma_200)} />
                <MetricRow label={t('metric.bbPosition')} value={formatRatio(technical.bb_position)} />
                <MetricRow label={t('metric.volRatio')} value={formatRatio(technical.volume_ratio)} />
                <MetricRow label={t('metric.stochK')} value={formatRatio(technical.stoch_k)} />
                <MetricRow label={t('metric.stochD')} value={formatRatio(technical.stoch_d)} />
              </dl>
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500">{t('detail.noData')}</p>
            )}
          </div>

          <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
            <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">{t('detail.sentiment')}</h3>
            {sentiment ? (
              <dl className="space-y-1 text-sm">
                <MetricRow label={t('metric.compound')} value={formatRatio(sentiment.sentiment_compound)} />
                <MetricRow label={t('metric.positive')} value={formatPercent(sentiment.sentiment_pos)} />
                <MetricRow label={t('metric.negative')} value={formatPercent(sentiment.sentiment_neg)} />
                <MetricRow label={t('metric.neutral')} value={formatPercent(sentiment.sentiment_neu)} />
                <MetricRow label={t('metric.newsCount')} value={String(sentiment.news_count)} />
              </dl>
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

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-gray-500 dark:text-gray-400">{label}</dt>
      <dd className="font-mono font-medium text-gray-900 dark:text-white">{value}</dd>
    </div>
  );
}
