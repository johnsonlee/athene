import { useParams, Link } from 'react-router-dom';
import { useStockDetail } from '../../hooks/useStockDetail';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ScoreBadge } from '../common/ScoreBadge';
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
              <p className="font-mono text-xs text-gray-500 sm:text-sm dark:text-gray-500">{t('detail.rank', { rank: ranking.rank })}</p>
              <p className="font-mono text-base font-bold text-gray-900 sm:text-lg dark:text-white">{formatScore(ranking.composite_score)}</p>
              <ScoreBadge tier={ranking.tier} label={t(`tier.${ranking.tier}` as any)} />
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
