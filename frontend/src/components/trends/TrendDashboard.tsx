import { useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTrends } from '../../hooks/useTrends';
import { useTrendHistory } from '../../hooks/useTrendHistory';
import { useRankings } from '../../hooks/useRankings';
import { useMeta } from '../../hooks/useMeta';
import { useI18n } from '../../lib/i18n';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { RegimeBanner } from './RegimeBanner';
import { TrendLineChart } from './TrendLineChart';
import type { MacroRegime } from '../../types';

export function TrendDashboard() {
  const { data: trends, loading, error } = useTrends();
  const { data: trendHistory } = useTrendHistory();
  const { data: rankings } = useRankings();
  const { data: meta } = useMeta();
  const { t, tIndustry } = useI18n();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const etfToSector = useMemo(
    () => trends ? Object.fromEntries(trends.sectors.map((s) => [s.etf, s.sector])) : {},
    [trends],
  );
  const sectorToEtf = useMemo(
    () => trends ? Object.fromEntries(trends.sectors.map((s) => [s.sector, s.etf])) : {},
    [trends],
  );

  const sectorParam = searchParams.get('sector') || null;
  const selectedSector = sectorParam ? (etfToSector[sectorParam] || null) : null;

  const setSelectedSector = useCallback((sector: string | null) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (sector) next.set('sector', sectorToEtf[sector] || sector);
      else next.delete('sector');
      return next;
    }, { replace: true });
  }, [setSearchParams, sectorToEtf]);

  const filteredStocks = useMemo(() => {
    if (!rankings.length) return [];
    const list = selectedSector
      ? rankings.filter((s) => s.sector === selectedSector)
      : rankings;
    return list.slice(0, 50);
  }, [rankings, selectedSector]);

  if (loading) return <LoadingSpinner message={t('common.loading')} />;

  if (error || !trends) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
        <p className="text-sm text-gray-500 dark:text-gray-400">{t('trends.noData')}</p>
      </div>
    );
  }

  const macro = (meta?.macro ?? trends.regime) as MacroRegime | undefined;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">
          {t('trends.title')}
        </h1>
        <p className="mt-1 font-mono text-sm text-gray-500 dark:text-gray-400">
          {trends.date}
        </p>
      </div>

      {macro && <RegimeBanner macro={macro} />}

      <TrendLineChart
        sectors={trends.sectors}
        history={trendHistory}
        selectedSector={selectedSector}
        onSectorSelect={setSelectedSector}
      />

      {/* Stock list */}
      {rankings.length > 0 && (
        <div className="tech-card overflow-x-auto">
          <div className="mb-2 flex items-center justify-between px-3 pt-3">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              {selectedSector
                ? t(`sector.${selectedSector}` as any)
                : t('screener.allSectors' as any)}
            </h2>
            <span className="font-mono text-xs text-gray-400 dark:text-gray-500">
              {filteredStocks.length}{selectedSector ? '' : ' / ' + rankings.length}
            </span>
          </div>

          {/* Desktop table */}
          <table className="hidden w-full text-left text-sm md:table">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 dark:border-cyan-500/10 dark:bg-slate-900/50">
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">
                  {t('table.rank')}
                </th>
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">
                  {t('table.ticker')}
                </th>
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">
                  {t('table.name')}
                </th>
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">
                  {selectedSector ? t('table.industry') : t('table.sectorIndustry')}
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">
                  {t('table.alphaScore')}
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">VM</th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">EV</th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-500">Timing</th>
              </tr>
            </thead>
            <tbody>
              {filteredStocks.map((stock) => (
                <tr
                  key={stock.ticker}
                  onClick={() => navigate(`/stock/${stock.ticker}`)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(`/stock/${stock.ticker}`); } }}
                  tabIndex={0}
                  role="link"
                  className="tech-row cursor-pointer border-b border-gray-100 transition-colors last:border-0 hover:bg-gray-50 dark:border-slate-700/50 dark:hover:bg-transparent"
                >
                  <td className="px-3 py-2 font-mono text-xs text-gray-400 dark:text-gray-600">
                    {stock.rank}
                  </td>
                  <td className="px-3 py-2 font-mono text-sm font-bold text-blue-600 dark:text-cyan-400">
                    {stock.ticker}
                  </td>
                  <td className="max-w-[200px] truncate px-3 py-2 text-gray-700 dark:text-gray-300">
                    {stock.name}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-500">
                    {selectedSector
                      ? (stock.industry ? tIndustry(stock.industry) : '\u2014')
                      : <>
                          {stock.sector ? (t(`sector.${stock.sector}` as any) || stock.sector) : ''}
                          {stock.sector && stock.industry ? <span className="mx-1 text-gray-300 dark:text-gray-700">&middot;</span> : ''}
                          {stock.industry ? tIndustry(stock.industry) : ''}
                        </>
                    }
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-medium text-gray-900 dark:text-white">
                    {(stock.alpha_score ?? stock.composite_score)?.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-sm text-gray-700 dark:text-gray-400">{stock.alpha_vm?.toFixed(1) ?? '\u2014'}</td>
                  <td className="px-3 py-2 text-right font-mono text-sm text-gray-700 dark:text-gray-400">{stock.alpha_ev?.toFixed(1) ?? '\u2014'}</td>
                  <td className="px-3 py-2 text-right font-mono text-sm text-gray-700 dark:text-gray-400">{stock.alpha_timing?.toFixed(1) ?? '\u2014'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Mobile cards */}
          <div className="space-y-2 px-3 pb-3 md:hidden">
            {filteredStocks.map((stock) => (
              <div
                key={stock.ticker}
                onClick={() => navigate(`/stock/${stock.ticker}`)}
                className="tech-card block cursor-pointer p-3 transition-all active:scale-[0.99]"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-400 dark:text-gray-600">
                      {stock.rank}
                    </span>
                    <span className="font-mono text-sm font-bold text-blue-600 dark:text-cyan-400">
                      {stock.ticker}
                    </span>
                    <span className="max-w-[120px] truncate text-xs text-gray-500">
                      {stock.name}
                    </span>
                  </div>
                  <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
                    {(stock.alpha_score ?? stock.composite_score)?.toFixed(1)}
                  </span>
                </div>
                <div className="mt-1.5 grid grid-cols-3 gap-2 text-[10px]">
                  <div>
                    <span className="text-gray-400 dark:text-gray-600">VM</span>
                    <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{stock.alpha_vm?.toFixed(1) ?? '\u2014'}</p>
                  </div>
                  <div>
                    <span className="text-gray-400 dark:text-gray-600">EV</span>
                    <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{stock.alpha_ev?.toFixed(1) ?? '\u2014'}</p>
                  </div>
                  <div>
                    <span className="text-gray-400 dark:text-gray-600">Timing</span>
                    <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{stock.alpha_timing?.toFixed(1) ?? '\u2014'}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
