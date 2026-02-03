import { Link } from 'react-router-dom';
import type { RankedStock } from '../../types';
import { ScoreBadge } from '../common/ScoreBadge';
import { formatScore } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

interface Props {
  rankings: RankedStock[];
}

export function TopMovers({ rankings }: Props) {
  const { t, tIndustry } = useI18n();
  const top10 = rankings.slice(0, 10);
  const bottom10 = [...rankings].sort((a, b) => a.composite_score - b.composite_score).slice(0, 10);

  return (
    <>
      <div className="tech-card p-4">
        <h2 className="tech-heading mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.top10')}</h2>
        <div className="space-y-1">
          {top10.map((stock, i) => (
            <Link
              key={stock.ticker}
              to={`/stock/${stock.ticker}`}
              className="tech-row flex items-center justify-between rounded p-2 transition-colors hover:bg-gray-50 active:bg-gray-100 dark:hover:bg-transparent dark:active:bg-transparent"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="w-5 shrink-0 text-right font-mono text-xs text-gray-400 dark:text-gray-600">{i + 1}</span>
                  <span className="shrink-0 font-mono text-sm font-semibold text-gray-900 dark:text-white">{stock.ticker}</span>
                  <span className="hidden truncate text-xs text-gray-500 sm:inline dark:text-gray-500">{stock.name}</span>
                </div>
                {stock.industry && (
                  <p className="ml-7 truncate text-[10px] text-gray-400 dark:text-gray-600">{tIndustry(stock.industry)}</p>
                )}
              </div>
              <div className="ml-2 flex shrink-0 items-center gap-2">
                <span className="font-mono text-sm font-medium text-emerald-600 dark:text-emerald-400">{formatScore(stock.composite_score)}</span>
                <ScoreBadge tier={stock.tier} label={t(`tier.${stock.tier}` as any)} />
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div className="tech-card p-4">
        <h2 className="tech-heading mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.bottom10')}</h2>
        <div className="space-y-1">
          {bottom10.map((stock, i) => (
            <Link
              key={stock.ticker}
              to={`/stock/${stock.ticker}`}
              className="tech-row flex items-center justify-between rounded p-2 transition-colors hover:bg-gray-50 active:bg-gray-100 dark:hover:bg-transparent dark:active:bg-transparent"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="w-5 shrink-0 text-right font-mono text-xs text-gray-400 dark:text-gray-600">{i + 1}</span>
                  <span className="shrink-0 font-mono text-sm font-semibold text-gray-900 dark:text-white">{stock.ticker}</span>
                  <span className="hidden truncate text-xs text-gray-500 sm:inline dark:text-gray-500">{stock.name}</span>
                </div>
                {stock.industry && (
                  <p className="ml-7 truncate text-[10px] text-gray-400 dark:text-gray-600">{tIndustry(stock.industry)}</p>
                )}
              </div>
              <div className="ml-2 flex shrink-0 items-center gap-2">
                <span className="font-mono text-sm font-medium text-red-600 dark:text-red-400">{formatScore(stock.composite_score)}</span>
                <ScoreBadge tier={stock.tier} label={t(`tier.${stock.tier}` as any)} />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
