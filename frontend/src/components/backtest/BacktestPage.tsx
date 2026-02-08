import { useState, useMemo } from 'react';
import { useBacktest } from '../../hooks/useBacktest';
import { useI18n } from '../../lib/i18n';
import type { BacktestSignal } from '../../types';

// Minimum sample size to show by default
const MIN_SAMPLES = 5;

function pct(v: number | null | undefined, digits = 2): string {
  if (v == null) return '-';
  return (v * 100).toFixed(digits) + '%';
}

function hitColor(rate: number | null | undefined): string {
  if (rate == null) return 'text-gray-400';
  if (rate >= 0.75) return 'text-green-600 dark:text-green-400';
  if (rate >= 0.6) return 'text-emerald-600 dark:text-emerald-400';
  if (rate >= 0.5) return 'text-gray-600 dark:text-gray-400';
  return 'text-red-500 dark:text-red-400';
}

function retColor(ret: number | null | undefined): string {
  if (ret == null) return 'text-gray-400';
  if (ret > 0.01) return 'text-green-600 dark:text-green-400';
  if (ret > 0) return 'text-emerald-600 dark:text-emerald-400';
  if (ret < -0.01) return 'text-red-500 dark:text-red-400';
  if (ret < 0) return 'text-orange-500 dark:text-orange-400';
  return '';
}

/** Signal quality badge based on sample size and hit rate */
function QualityBadge({ signal }: { signal: BacktestSignal }) {
  const { t } = useI18n();
  const h22 = signal.horizons['22d'];
  const n = signal.count;
  const hr = h22?.hit_rate ?? 0;

  let key: string;
  let cls: string;

  if (n >= 20 && hr >= 0.7) {
    key = 'backtest.quality.strong';
    cls = 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
  } else if (n >= 10 && hr >= 0.6) {
    key = 'backtest.quality.moderate';
    cls = 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
  } else if (n >= 5) {
    key = 'backtest.quality.weak';
    cls = 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
  } else {
    key = 'backtest.quality.insufficient';
    cls = 'bg-gray-50 text-gray-400 dark:bg-gray-800 dark:text-gray-500';
  }

  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${cls}`}>
      {t(key as any)}
    </span>
  );
}

/** Compact bar chart for hit rate visualization */
function HitRateBar({ rate }: { rate: number | null | undefined }) {
  if (rate == null) return <span className="text-gray-400">-</span>;
  const pctVal = Math.round(rate * 100);
  const barColor = rate >= 0.7 ? 'bg-green-500' : rate >= 0.6 ? 'bg-emerald-400' : rate >= 0.5 ? 'bg-gray-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-12 rounded-full bg-gray-200 dark:bg-gray-700">
        <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${Math.min(pctVal, 100)}%` }} />
      </div>
      <span className={`text-xs tabular-nums ${hitColor(rate)}`}>{pctVal}%</span>
    </div>
  );
}

/** Key findings section — computed from data */
function KeyFindings({ signals, t }: { signals: BacktestSignal[]; t: (k: string) => string }) {
  // Find notable signals
  const strong = signals
    .filter((s) => s.count >= 5 && (s.horizons['22d']?.hit_rate ?? 0) >= 0.7)
    .sort((a, b) => (b.horizons['22d']?.hit_rate ?? 0) - (a.horizons['22d']?.hit_rate ?? 0));

  const traps = signals
    .filter((s) => s.count >= 3 && (s.horizons['22d']?.avg_return ?? 0) < -0.01);

  const bestContrarian = signals
    .filter((s) => s.count >= 5 && s.direction === 'risk_off' && (s.horizons['22d']?.hit_rate ?? 0) > 0.7);

  const findings: { text: string; color: string }[] = [];

  if (strong.length > 0) {
    const best = strong[0];
    const signalLabel = t(`backtest.signal.${best.signal}`) || best.signal;
    const dirLabel = t(`backtest.dir.${best.direction}`) || best.direction;
    findings.push({
      text: t('backtest.finding.strongSignal')
        .replace('{signal}', `${signalLabel} (${dirLabel})`)
        .replace('{hitRate}', pct(best.horizons['22d']?.hit_rate, 0))
        .replace('{return}', pct(best.horizons['22d']?.avg_return))
        .replace('{n}', String(best.count)),
      color: 'border-green-200 bg-green-50 dark:border-green-900/50 dark:bg-green-950/30',
    });
  }

  if (bestContrarian.length > 0) {
    const c = bestContrarian[0];
    findings.push({
      text: t('backtest.finding.contrarian')
        .replace('{hitRate}', pct(c.horizons['22d']?.hit_rate, 0))
        .replace('{return}', pct(c.horizons['22d']?.avg_return))
        .replace('{n}', String(c.count)),
      color: 'border-blue-200 bg-blue-50 dark:border-blue-900/50 dark:bg-blue-950/30',
    });
  }

  if (traps.length > 0) {
    const worst = traps.sort((a, b) => (a.horizons['22d']?.avg_return ?? 0) - (b.horizons['22d']?.avg_return ?? 0))[0];
    const signalLabel = t(`backtest.signal.${worst.signal}`) || worst.signal;
    const dirLabel = t(`backtest.dir.${worst.direction}`) || worst.direction;
    findings.push({
      text: t('backtest.finding.trap')
        .replace('{signal}', `${signalLabel} (${dirLabel})`)
        .replace('{return}', pct(worst.horizons['22d']?.avg_return))
        .replace('{hitRate}', pct(worst.horizons['22d']?.hit_rate, 0)),
      color: 'border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30',
    });
  }

  // Sector trends lack alpha
  const upgrades = signals.find((s) => s.signal === 'sector_trend_transition' && s.direction === 'upgrade');
  const downgrades = signals.find((s) => s.signal === 'sector_trend_transition' && s.direction === 'downgrade');
  if (upgrades && downgrades) {
    const upRet = upgrades.horizons['22d']?.avg_return ?? 0;
    const downRet = downgrades.horizons['22d']?.avg_return ?? 0;
    if (upRet > 0 && downRet > 0) {
      findings.push({
        text: t('backtest.finding.sectorBeta')
          .replace('{upReturn}', pct(upRet))
          .replace('{downReturn}', pct(downRet)),
        color: 'border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30',
      });
    }
  }

  if (findings.length === 0) return null;

  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{t('backtest.keyFindings')}</h2>
      <div className="grid gap-2 sm:grid-cols-2">
        {findings.map((f, i) => (
          <div key={i} className={`rounded-lg border p-3 ${f.color}`}>
            <div className="flex gap-2">
              <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-gray-900/10 text-[10px] font-bold text-gray-700 dark:bg-white/10 dark:text-gray-300">
                {i + 1}
              </span>
              <p className="text-xs leading-relaxed text-gray-700 dark:text-gray-300">{f.text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SignalRow({ signal, t }: { signal: BacktestSignal; t: (k: string) => string }) {
  const [expanded, setExpanded] = useState(false);
  const [tab, setTab] = useState<'horizons' | 'sectors' | 'events'>('horizons');

  const signalLabel = t(`backtest.signal.${signal.signal}`) || signal.signal;
  const dirLabel = t(`backtest.dir.${signal.direction}`) || signal.direction;
  const h22 = signal.horizons['22d'];
  const lowSample = signal.count < MIN_SAMPLES;

  return (
    <div className={`tech-card overflow-hidden ${lowSample ? 'opacity-60' : ''}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 p-3 text-left hover:bg-gray-50 sm:p-4 dark:hover:bg-gray-800/50"
      >
        {/* Signal name + direction */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-semibold text-gray-900 dark:text-white">{signalLabel}</span>
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {dirLabel}
            </span>
            <QualityBadge signal={signal} />
          </div>
          <div className="mt-0.5 text-[11px] text-gray-400">
            {t('backtest.sampleCount' as any).replace('{count}', String(signal.count))} &middot; {signal.date_range.first} ~ {signal.date_range.last}
          </div>
        </div>

        {/* 22d stats — the key metrics */}
        <div className="hidden items-center gap-4 sm:flex">
          <div className="text-right">
            <div className="text-[10px] text-gray-400">{t('backtest.hitRate')} 22d</div>
            <HitRateBar rate={h22?.hit_rate} />
          </div>
          <div className="text-right">
            <div className="text-[10px] text-gray-400">{t('backtest.avgReturn')} 22d</div>
            <span className={`text-sm font-medium tabular-nums ${retColor(h22?.avg_return)}`}>
              {pct(h22?.avg_return)}
            </span>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-gray-400">{t('backtest.maxDD')}</div>
            <span className="text-sm tabular-nums text-red-500 dark:text-red-400">
              {pct(signal.max_drawdown.worst)}
            </span>
          </div>
        </div>

        {/* Mobile: compact stats */}
        <div className="flex items-center gap-3 sm:hidden">
          <div className="text-right">
            <span className={`text-xs font-medium ${hitColor(h22?.hit_rate)}`}>
              {pct(h22?.hit_rate, 0)}
            </span>
          </div>
          <div className="text-right">
            <span className={`text-xs font-medium ${retColor(h22?.avg_return)}`}>
              {pct(h22?.avg_return)}
            </span>
          </div>
        </div>

        <svg className={`h-4 w-4 flex-shrink-0 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 p-3 sm:p-4 dark:border-gray-700">
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
        </div>
      )}
    </div>
  );
}

export function BacktestPage() {
  const { data, loading, error } = useBacktest();
  const { t } = useI18n();
  const [filter, setFilter] = useState<string>('all');
  const [showAll, setShowAll] = useState(false);

  const { filtered, hiddenCount, signalTypes } = useMemo(() => {
    if (!data) return { filtered: [], hiddenCount: 0, signalTypes: [] };

    const types = [...new Set(data.signals.map((s) => s.signal))];

    // Apply signal type filter
    let sigs = filter === 'all' ? data.signals : data.signals.filter((s) => s.signal === filter);

    // Sort by conviction: high sample + high hit rate first
    sigs = [...sigs].sort((a, b) => {
      const scoreA = a.count * Math.abs(a.horizons['22d']?.expectancy ?? 0);
      const scoreB = b.count * Math.abs(b.horizons['22d']?.expectancy ?? 0);
      return scoreB - scoreA;
    });

    // Filter low-sample signals unless showAll
    const hidden = sigs.filter((s) => s.count < MIN_SAMPLES).length;
    if (!showAll) {
      sigs = sigs.filter((s) => s.count >= MIN_SAMPLES);
    }

    return { filtered: sigs, hiddenCount: hidden, signalTypes: types };
  }, [data, filter, showAll]);

  if (loading) return <div className="py-12 text-center text-gray-400">{t('common.loading')}</div>;
  if (error) return <div className="py-12 text-center text-red-500">{t('common.error').replace('{message}', error)}</div>;
  if (!data) return <div className="py-12 text-center text-gray-400">{t('backtest.noData')}</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">
          {t('backtest.title')}
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {t('backtest.subtitle')} &middot; {data.total_events.toLocaleString()} {t('backtest.events')} &middot; {t('backtest.updated')} {data.date}
        </p>
      </div>

      {/* Key Findings */}
      <KeyFindings signals={data.signals} t={t as (k: string) => string} />

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
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

        {hiddenCount > 0 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="ml-auto text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            {showAll
              ? t('backtest.hideSmall')
              : t('backtest.showSmall').replace('{n}', String(hiddenCount))}
          </button>
        )}
      </div>

      {/* Signal list — sorted by conviction */}
      <div className="space-y-2">
        {filtered.map((sig, i) => (
          <SignalRow key={`${sig.signal}-${sig.direction}-${i}`} signal={sig} t={t as (k: string) => string} />
        ))}
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 dark:text-gray-500">
        {t('backtest.disclaimer')}
      </p>
    </div>
  );
}
