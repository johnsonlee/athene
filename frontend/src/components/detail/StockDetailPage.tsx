import { useParams, Link } from 'react-router-dom';
import { useStockDetail } from '../../hooks/useStockDetail';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ScoreBadge } from '../common/ScoreBadge';
import { PriceChart } from './PriceChart';
import { IndicatorCharts } from './IndicatorCharts';
import { ScoreBreakdown } from './ScoreBreakdown';
import { formatScore, formatPrice } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

export function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const { data, loading, error } = useStockDetail(ticker);
  const { t } = useI18n();

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return <p className="text-center text-red-600 dark:text-red-400">{t('common.error', { message: error })}</p>;
  if (!data) return <p className="text-center text-gray-500 dark:text-gray-400">{t('common.noDataFound')}</p>;

  const { fundamental, technical, ranking } = data;

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

      {/* Score Breakdown */}
      <ScoreBreakdown detail={data} />
    </div>
  );
}
