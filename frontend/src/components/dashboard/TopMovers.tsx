import { Link } from 'react-router-dom';
import type { RankedStock } from '../../types';
import { ScoreBadge } from '../common/ScoreBadge';
import { formatScore } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

interface Props {
  rankings: RankedStock[];
}

export function TopMovers({ rankings }: Props) {
  const { t } = useI18n();
  const top10 = rankings.slice(0, 10);
  const bottom10 = [...rankings].sort((a, b) => a.composite_score - b.composite_score).slice(0, 10);

  return (
    <>
      <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.top10')}</h2>
        <div className="space-y-1">
          {top10.map((stock, i) => (
            <Link
              key={stock.ticker}
              to={`/stock/${stock.ticker}`}
              className="flex items-center justify-between rounded p-2 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <div className="flex items-center gap-2">
                <span className="w-5 text-right font-mono text-xs text-gray-400 dark:text-gray-500">{i + 1}</span>
                <span className="font-mono text-sm font-semibold text-gray-900 dark:text-white">{stock.ticker}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{stock.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-medium text-green-600 dark:text-green-400">{formatScore(stock.composite_score)}</span>
                <ScoreBadge tier={stock.tier} label={t(`tier.${stock.tier}` as any)} />
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.bottom10')}</h2>
        <div className="space-y-1">
          {bottom10.map((stock, i) => (
            <Link
              key={stock.ticker}
              to={`/stock/${stock.ticker}`}
              className="flex items-center justify-between rounded p-2 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <div className="flex items-center gap-2">
                <span className="w-5 text-right font-mono text-xs text-gray-400 dark:text-gray-500">{i + 1}</span>
                <span className="font-mono text-sm font-semibold text-gray-900 dark:text-white">{stock.ticker}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{stock.name}</span>
              </div>
              <div className="flex items-center gap-2">
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
