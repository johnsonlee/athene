import { useState } from 'react';
import { useBacktest } from '../../hooks/useBacktest';
import { useI18n } from '../../lib/i18n';
import type { BacktestSignal } from '../../types';

const SIGNAL_ORDER = ['sector_trend_transition', 'capital_flow_phase', 'rfi_crossing', 'macro_regime'];

function pct(v: number | null | undefined, digits = 2): string {
  if (v == null) return '-';
  return (v * 100).toFixed(digits) + '%';
}

function hitColor(rate: number | null | undefined): string {
  if (rate == null) return '';
  if (rate >= 0.65) return 'text-green-600 dark:text-green-400';
  if (rate >= 0.5) return 'text-gray-600 dark:text-gray-400';
  return 'text-red-500 dark:text-red-400';
}

function retColor(ret: number | null | undefined): string {
  if (ret == null) return '';
  if (ret > 0) return 'text-green-600 dark:text-green-400';
  if (ret < 0) return 'text-red-500 dark:text-red-400';
  return '';
}

function SignalCard({ signal, t }: { signal: BacktestSignal; t: (k: string) => string }) {
  const [expanded, setExpanded] = useState(false);
  const [tab, setTab] = useState<'horizons' | 'sectors' | 'events'>('horizons');

  const signalLabel = t(`backtest.signal.${signal.signal}`) || signal.signal;
  const dirLabel = t(`backtest.dir.${signal.direction}`) || signal.direction;

  const h22 = signal.horizons['22d'];
  const h5 = signal.horizons['5d'];

  return (
    <div className="tech-card overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900 dark:text-white">{signalLabel}</span>
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {dirLabel}
            </span>
            <span className="text-xs text-gray-400">n={signal.count}</span>
          </div>
          <div className="mt-1 flex gap-4 text-xs">
            <span>
              {t('backtest.hitRate')} 5d: <span className={hitColor(h5?.hit_rate)}>{pct(h5?.hit_rate, 1)}</span>
            </span>
            <span>
              22d: <span className={hitColor(h22?.hit_rate)}>{pct(h22?.hit_rate, 1)}</span>
            </span>
            <span>
              {t('backtest.avgReturn')} 22d: <span className={retColor(h22?.avg_return)}>{pct(h22?.avg_return)}</span>
            </span>
            <span>
              {t('backtest.maxDD')}: <span className="text-red-500 dark:text-red-400">{pct(signal.max_drawdown.worst)}</span>
            </span>
          </div>
        </div>
        <svg className={`h-4 w-4 flex-shrink-0 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 p-4 dark:border-gray-700">
          {/* Tabs */}
          <div className="mb-3 flex gap-1">
            {(['horizons', ...(signal.sectors ? ['sectors'] : []), 'events'] as const).map((t_) => (
              <button
                key={t_}
                onClick={() => setTab(t_ as typeof tab)}
                className={`rounded px-2 py-1 text-xs font-medium ${
                  tab === t_
                    ? 'bg-gray-900 text-white dark:bg-gray-600'
                    : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
                }`}
              >
                {t(`backtest.tab.${t_}`)}
              </button>
            ))}
          </div>

          {/* Horizon stats table */}
          {tab === 'horizons' && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 dark:text-gray-400">
                    <th className="pb-2 pr-3 font-medium">{t('backtest.horizon')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.samples')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.hitRate')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.avgReturn')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.medianReturn')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.expectancy')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.std')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.best')}</th>
                    <th className="pb-2 font-medium">{t('backtest.worst')}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(signal.horizons).map(([horizon, stats]) => (
                    <tr key={horizon} className="border-t border-gray-50 dark:border-gray-800">
                      <td className="py-1.5 pr-3 font-medium text-gray-900 dark:text-white">{horizon}</td>
                      <td className="py-1.5 pr-3 text-gray-600 dark:text-gray-400">{stats.count}</td>
                      <td className={`py-1.5 pr-3 font-medium ${hitColor(stats.hit_rate)}`}>{pct(stats.hit_rate, 1)}</td>
                      <td className={`py-1.5 pr-3 ${retColor(stats.avg_return)}`}>{pct(stats.avg_return)}</td>
                      <td className={`py-1.5 pr-3 ${retColor(stats.median_return)}`}>{pct(stats.median_return)}</td>
                      <td className={`py-1.5 pr-3 ${retColor(stats.expectancy)}`}>{pct(stats.expectancy)}</td>
                      <td className="py-1.5 pr-3 text-gray-500 dark:text-gray-400">{pct(stats.std)}</td>
                      <td className="py-1.5 pr-3 text-green-600 dark:text-green-400">{pct(stats.max_return)}</td>
                      <td className="py-1.5 text-red-500 dark:text-red-400">{pct(stats.min_return)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Transition breakdown */}
              {Object.keys(signal.transitions).length > 1 && (
                <div className="mt-3">
                  <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">{t('backtest.transitions')}</h4>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(signal.transitions).map(([transition, count]) => (
                      <span key={transition} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                        {transition} ({count})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Sector breakdown */}
          {tab === 'sectors' && signal.sectors && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 dark:text-gray-400">
                    <th className="pb-2 pr-3 font-medium">{t('backtest.sector')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.samples')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.hitRate')} 5d</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.avgReturn')} 5d</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.hitRate')} 22d</th>
                    <th className="pb-2 font-medium">{t('backtest.avgReturn')} 22d</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(signal.sectors)
                    .sort(([, a], [, b]) => (b.avg_return_22d ?? 0) - (a.avg_return_22d ?? 0))
                    .map(([sector, stats]) => (
                      <tr key={sector} className="border-t border-gray-50 dark:border-gray-800">
                        <td className="py-1.5 pr-3 font-medium text-gray-900 dark:text-white">{sector}</td>
                        <td className="py-1.5 pr-3 text-gray-600 dark:text-gray-400">{stats.count}</td>
                        <td className={`py-1.5 pr-3 ${hitColor(stats.hit_rate_5d)}`}>{pct(stats.hit_rate_5d, 1)}</td>
                        <td className={`py-1.5 pr-3 ${retColor(stats.avg_return_5d)}`}>{pct(stats.avg_return_5d)}</td>
                        <td className={`py-1.5 pr-3 ${hitColor(stats.hit_rate_22d)}`}>{pct(stats.hit_rate_22d, 1)}</td>
                        <td className={`py-1.5 ${retColor(stats.avg_return_22d)}`}>{pct(stats.avg_return_22d)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Recent events */}
          {tab === 'events' && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 dark:text-gray-400">
                    <th className="pb-2 pr-3 font-medium">{t('backtest.date')}</th>
                    <th className="pb-2 pr-3 font-medium">{t('backtest.transition')}</th>
                    {signal.signal === 'sector_trend_transition' && <th className="pb-2 pr-3 font-medium">{t('backtest.sector')}</th>}
                    <th className="pb-2 pr-3 font-medium">5d</th>
                    <th className="pb-2 pr-3 font-medium">10d</th>
                    <th className="pb-2 pr-3 font-medium">22d</th>
                    <th className="pb-2 font-medium">{t('backtest.maxDD')}</th>
                  </tr>
                </thead>
                <tbody>
                  {signal.recent_events.map((ev, i) => (
                    <tr key={i} className="border-t border-gray-50 dark:border-gray-800">
                      <td className="py-1.5 pr-3 text-gray-600 dark:text-gray-400">{ev.date}</td>
                      <td className="py-1.5 pr-3 text-gray-900 dark:text-white">{ev.transition}</td>
                      {signal.signal === 'sector_trend_transition' && (
                        <td className="py-1.5 pr-3 text-gray-600 dark:text-gray-400">{ev.sector}</td>
                      )}
                      <td className={`py-1.5 pr-3 ${retColor(ev.fwd_5d)}`}>{pct(ev.fwd_5d)}</td>
                      <td className={`py-1.5 pr-3 ${retColor(ev.fwd_10d)}`}>{pct(ev.fwd_10d)}</td>
                      <td className={`py-1.5 pr-3 ${retColor(ev.fwd_22d)}`}>{pct(ev.fwd_22d)}</td>
                      <td className="py-1.5 text-red-500 dark:text-red-400">{pct(ev.max_drawdown_22d)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Date range */}
          <div className="mt-3 text-[10px] text-gray-400">
            {signal.date_range.first} ~ {signal.date_range.last}
          </div>
        </div>
      )}
    </div>
  );
}

export function BacktestPage() {
  const { data, loading, error } = useBacktest();
  const { t } = useI18n();
  const [filter, setFilter] = useState<string>('all');

  if (loading) return <div className="py-12 text-center text-gray-400">{t('common.loading')}</div>;
  if (error) return <div className="py-12 text-center text-red-500">{t('common.error').replace('{message}', error)}</div>;
  if (!data) return <div className="py-12 text-center text-gray-400">{t('backtest.noData')}</div>;

  const signalTypes = [...new Set(data.signals.map((s) => s.signal))];
  const filtered = filter === 'all' ? data.signals : data.signals.filter((s) => s.signal === filter);

  // Group by signal type for display
  const grouped: Record<string, BacktestSignal[]> = {};
  for (const sig of filtered) {
    const key = sig.signal;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(sig);
  }

  const sortedGroups = SIGNAL_ORDER
    .filter((s) => grouped[s])
    .map((s) => [s, grouped[s]] as const);

  // Add any unrecognized signal types
  for (const [key, sigs] of Object.entries(grouped)) {
    if (!SIGNAL_ORDER.includes(key)) {
      sortedGroups.push([key, sigs] as const);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">
            {t('backtest.title')}
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {t('backtest.subtitle')} &middot; {data.total_events.toLocaleString()} {t('backtest.events')} &middot; {t('backtest.updated')} {data.date}
          </p>
        </div>

        {/* Filter */}
        <div className="flex gap-1">
          <button
            onClick={() => setFilter('all')}
            className={`rounded px-2.5 py-1 text-xs font-medium ${
              filter === 'all'
                ? 'bg-gray-900 text-white dark:bg-gray-600'
                : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
            }`}
          >
            {t('backtest.all')}
          </button>
          {signalTypes.map((st) => (
            <button
              key={st}
              onClick={() => setFilter(st)}
              className={`rounded px-2.5 py-1 text-xs font-medium ${
                filter === st
                  ? 'bg-gray-900 text-white dark:bg-gray-600'
                  : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              {t(`backtest.signal.${st}` as any) || st}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="tech-card p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400">{t('backtest.totalSignals')}</div>
          <div className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{data.signals.length}</div>
        </div>
        <div className="tech-card p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400">{t('backtest.totalEvents')}</div>
          <div className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{data.total_events.toLocaleString()}</div>
        </div>
        <div className="tech-card p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400">{t('backtest.bestHitRate')}</div>
          <div className="mt-1 text-lg font-bold text-green-600 dark:text-green-400">
            {pct(
              Math.max(...data.signals.filter((s) => s.count >= 5).map((s) => s.horizons['22d']?.hit_rate ?? 0)),
              1,
            )}
          </div>
        </div>
        <div className="tech-card p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400">{t('backtest.bestExpectancy')}</div>
          <div className="mt-1 text-lg font-bold text-green-600 dark:text-green-400">
            {pct(
              Math.max(...data.signals.filter((s) => s.count >= 5).map((s) => s.horizons['22d']?.expectancy ?? 0)),
            )}
          </div>
        </div>
      </div>

      {/* Signal groups */}
      {sortedGroups.map(([groupKey, signals]) => (
        <section key={groupKey}>
          <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
            {t(`backtest.signal.${groupKey}` as any) || groupKey}
          </h2>
          <div className="space-y-2">
            {signals.map((sig, i) => (
              <SignalCard key={`${sig.signal}-${sig.direction}-${i}`} signal={sig} t={t as (k: string) => string} />
            ))}
          </div>
        </section>
      ))}

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 dark:text-gray-500">
        {t('backtest.disclaimer')}
      </p>
    </div>
  );
}
