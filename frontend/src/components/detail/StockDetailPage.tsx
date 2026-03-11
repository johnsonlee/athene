import { useParams, Link } from 'react-router-dom';
import { useStockDetail } from '../../hooks/useStockDetail';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { CompanyProfile } from './CompanyProfile';
import { AnalystConsensus } from './AnalystConsensus';
import { PriceChart } from './PriceChart';

import { ScoreBreakdown } from './ScoreBreakdown';
import { formatScore, formatPrice } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

export function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const { data, loading, error } = useStockDetail(ticker);
  const { t, tIndustry } = useI18n();

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return <p className="text-center text-red-600 dark:text-red-400">{t('common.error', { message: error })}</p>;
  if (!data) return <p className="text-center text-gray-500 dark:text-gray-400">{t('common.noDataFound')}</p>;

  const { fundamental, ranking } = data;

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <Link to="/screener" className="inline-block py-1 text-sm text-blue-600 hover:underline dark:text-cyan-400">&larr; {t('detail.backToScreener')}</Link>
        <div className="mt-1 flex items-start justify-between">
          <div>
            <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">{ticker}</h1>
            {(ranking?.industry || ranking?.sector) && (
              <p className="text-xs text-gray-500 dark:text-gray-500">{ranking.industry ? tIndustry(ranking.industry) : (ranking.sector ? t(`sector.${ranking.sector}` as any) : '')}</p>
            )}
            {fundamental?.current_price && (
              <p className="font-mono text-lg font-semibold text-gray-700 sm:text-xl dark:text-gray-300">
                {formatPrice(fundamental.current_price)}
              </p>
            )}
          </div>
          {ranking && (
            <div className="ml-3 text-right">
              <p className="font-mono text-base font-bold text-gray-900 sm:text-lg dark:text-white">{formatScore(ranking.alpha_score)}</p>
              <p className="font-mono text-xs text-gray-500 dark:text-gray-500">
                #{ranking.rank} · Top {((1 - ranking.percentile) * 100).toFixed(0)}%
              </p>
              <div className="mt-1 flex gap-2 text-[10px]">
                <span className="text-gray-400 dark:text-gray-600">VM <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(ranking.alpha_vm)}</span></span>
                <span className="text-gray-400 dark:text-gray-600">EV <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(ranking.alpha_ev)}</span></span>
                <span className="text-gray-400 dark:text-gray-600">T <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(ranking.alpha_timing)}</span></span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Company Profile */}
      <CompanyProfile profile={data.profile} ranking={data.ranking} />

      {/* Price Chart + Indicators */}
      <PriceChart prices={data.prices} ticker={ticker!} />

      {/* Analyst Consensus */}
      <AnalystConsensus analyst={data.analyst ?? null} />

      {/* Score Breakdown */}
      <ScoreBreakdown detail={data} />
    </div>
  );
}
