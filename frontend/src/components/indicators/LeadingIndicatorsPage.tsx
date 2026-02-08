import { useState } from 'react';
import { useLeadingIndicators } from '../../hooks/useLeadingIndicators';
import { useI18n } from '../../lib/i18n';
import type {
  CreditSpreadEntry,
  RfiAccelerationEntry,
  BreadthThrustEntry,
} from '../../types';

type IndicatorKey = 'credit_spread' | 'breadth_thrust' | 'rfi_acceleration' | 'vix_term_structure';

const SIGNAL_COLORS: Record<string, string> = {
  credit_easing: 'text-green-600 dark:text-green-400',
  credit_tightening: 'text-red-600 dark:text-red-400',
  tightening_reversal: 'text-amber-600 dark:text-amber-400',
  easing_reversal: 'text-cyan-600 dark:text-cyan-400',
  strong_thrust: 'text-green-600 dark:text-green-400',
  thrust: 'text-green-500 dark:text-green-300',
  strong_collapse: 'text-red-600 dark:text-red-400',
  collapse: 'text-red-500 dark:text-red-300',
  strong_improving: 'text-green-600 dark:text-green-400',
  improving: 'text-green-500 dark:text-green-300',
  strong_deteriorating: 'text-red-600 dark:text-red-400',
  deteriorating: 'text-red-500 dark:text-red-300',
  bottoming: 'text-cyan-600 dark:text-cyan-400',
  topping: 'text-amber-600 dark:text-amber-400',
  backwardation: 'text-red-500 dark:text-red-300',
  deep_contango: 'text-amber-600 dark:text-amber-400',
  contango: 'text-green-500 dark:text-green-300',
  neutral: 'text-gray-500 dark:text-gray-400',
};

function pct(v: number | null | undefined, digits = 2): string {
  if (v == null) return '—';
  return (v * 100).toFixed(digits) + '%';
}

function num(v: number | null | undefined, digits = 4): string {
  if (v == null) return '—';
  return v.toFixed(digits);
}

function SignalBadge({ signal }: { signal: string }) {
  const { t } = useI18n();
  const color = SIGNAL_COLORS[signal] || SIGNAL_COLORS.neutral;
  const label = t(`indicators.signal.${signal}` as any);
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${color}`}>
      {label.startsWith('indicators.signal.') ? signal.replace(/_/g, ' ') : label}
    </span>
  );
}

function CreditSpreadCard({ data }: { data: CreditSpreadEntry[] }) {
  const { t } = useI18n();
  const latest = data[data.length - 1];
  if (!latest) return null;

  // Find recent signal events (newest first)
  const signals = data.filter((d) => d.signal !== 'neutral').slice(-5).reverse();

  return (
    <div className="tech-card p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('indicators.creditSpread' as any)}
        </h3>
        <SignalBadge signal={latest.signal} />
      </div>
      <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
        {t('indicators.creditSpreadDesc' as any)}
      </p>

      <div className="mb-3 grid grid-cols-3 gap-2">
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">LQD/TLT</div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">{num(latest.lqd_tlt_ratio)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">{t('indicators.velocity5d' as any)}</div>
          <div className={`text-sm font-medium ${(latest.velocity_5d ?? 0) < 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {pct(latest.velocity_5d)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">{t('indicators.velocity10d' as any)}</div>
          <div className={`text-sm font-medium ${(latest.velocity_10d ?? 0) < 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {pct(latest.velocity_10d)}
          </div>
        </div>
      </div>

      {/* Mini sparkline using bars */}
      <div className="mb-2 flex items-end gap-px" style={{ height: 40 }}>
        {data.slice(-60).map((d, i) => {
          const v5 = d.velocity_5d ?? 0;
          const absV = Math.min(Math.abs(v5) * 1000, 40);
          return (
            <div
              key={i}
              className={`flex-1 rounded-t-sm ${v5 < 0 ? 'bg-green-400 dark:bg-green-500' : 'bg-red-400 dark:bg-red-500'}`}
              style={{ height: Math.max(1, absV) }}
              title={`${d.date}: ${t('indicators.velocity5d' as any)} ${pct(d.velocity_5d)}`}
            />
          );
        })}
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400">
        <span>{data.slice(-60)[0]?.date}</span>
        <span>{latest.date}</span>
      </div>

      {signals.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-2 dark:border-gray-700">
          <div className="text-[10px] font-medium uppercase text-gray-400">{t('indicators.recentSignals' as any)}</div>
          <div className="mt-1 space-y-1">
            {signals.map((s, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-gray-500 dark:text-gray-400">{s.date}</span>
                <SignalBadge signal={s.signal} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BreadthThrustCard({ data }: { data: BreadthThrustEntry[] }) {
  const { t } = useI18n();
  const latest = data[data.length - 1];
  if (!latest) return null;

  const signals = data.filter((d) => d.signal !== 'neutral').slice(-5).reverse();

  return (
    <div className="tech-card p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('indicators.breadthThrust' as any)}
        </h3>
        <SignalBadge signal={latest.signal} />
      </div>
      <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
        {t('indicators.breadthThrustDesc' as any)}
      </p>

      <div className="mb-3 grid grid-cols-3 gap-2">
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">{t('indicators.sectorsUp' as any)}</div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">{latest.sectors_uptrend}/{latest.sectors_total}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">{t('indicators.pctUptrend' as any)}</div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">{pct(latest.pct_uptrend, 1)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">{t('indicators.thrust' as any)}</div>
          <div className={`text-sm font-medium ${latest.thrust > 0 ? 'text-green-600 dark:text-green-400' : latest.thrust < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'}`}>
            {latest.thrust > 0 ? '+' : ''}{pct(latest.thrust, 1)}
          </div>
        </div>
      </div>

      {/* Breadth area chart using stacked bars */}
      <div className="mb-2 flex items-end gap-px" style={{ height: 40 }}>
        {data.slice(-60).map((d, i) => {
          const h = d.pct_uptrend * 40;
          return (
            <div
              key={i}
              className="flex-1 rounded-t-sm bg-green-400 dark:bg-green-500"
              style={{ height: Math.max(1, h), opacity: d.pct_uptrend > 0.5 ? 1 : 0.6 }}
              title={`${d.date}: ${pct(d.pct_uptrend, 0)} ${t('indicators.uptrend' as any)}`}
            />
          );
        })}
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400">
        <span>{data.slice(-60)[0]?.date}</span>
        <span>{latest.date}</span>
      </div>

      {signals.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-2 dark:border-gray-700">
          <div className="text-[10px] font-medium uppercase text-gray-400">{t('indicators.recentSignals' as any)}</div>
          <div className="mt-1 space-y-1">
            {signals.map((s, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-gray-500 dark:text-gray-400">{s.date}</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">{s.sectors_uptrend}/{s.sectors_total}</span>
                  <SignalBadge signal={s.signal} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RfiAccelerationCard({ data }: { data: RfiAccelerationEntry[] }) {
  const { t } = useI18n();
  const latest = data[data.length - 1];
  if (!latest) return null;

  const signals = data.filter((d) => d.signal !== 'neutral').slice(-5).reverse();

  return (
    <div className="tech-card p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('indicators.rfiAcceleration' as any)}
        </h3>
        <SignalBadge signal={latest.signal} />
      </div>
      <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
        {t('indicators.rfiAccelerationDesc' as any)}
      </p>

      <div className="mb-3 grid grid-cols-3 gap-2">
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">RFI</div>
          <div className={`text-sm font-medium ${latest.rfi > 0 ? 'text-green-600 dark:text-green-400' : latest.rfi < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'}`}>
            {num(latest.rfi, 2)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">{t('indicators.velocity' as any)}</div>
          <div className={`text-sm font-medium ${latest.rfi_velocity > 0 ? 'text-green-600 dark:text-green-400' : latest.rfi_velocity < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'}`}>
            {num(latest.rfi_velocity, 4)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">{t('indicators.acceleration' as any)}</div>
          <div className={`text-sm font-medium ${latest.rfi_acceleration > 0 ? 'text-green-600 dark:text-green-400' : latest.rfi_acceleration < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'}`}>
            {num(latest.rfi_acceleration, 4)}
          </div>
        </div>
      </div>

      {/* RFI bar chart */}
      <div className="mb-2 flex items-center gap-px" style={{ height: 40 }}>
        {data.slice(-30).map((d, i) => {
          const abs = Math.min(Math.abs(d.rfi) * 20, 20);
          const isPositive = d.rfi >= 0;
          return (
            <div key={i} className="relative flex-1" style={{ height: 40 }} title={`${d.date}: ${t('indicators.rfiAcceleration' as any)} ${num(d.rfi, 2)}`}>
              {isPositive ? (
                <div
                  className="absolute bottom-[20px] w-full rounded-t-sm bg-green-400 dark:bg-green-500"
                  style={{ height: abs }}
                />
              ) : (
                <div
                  className="absolute top-[20px] w-full rounded-b-sm bg-red-400 dark:bg-red-500"
                  style={{ height: abs }}
                />
              )}
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400">
        <span>{data.slice(-30)[0]?.date}</span>
        <span>{latest.date}</span>
      </div>

      {signals.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-2 dark:border-gray-700">
          <div className="text-[10px] font-medium uppercase text-gray-400">{t('indicators.recentSignals' as any)}</div>
          <div className="mt-1 space-y-1">
            {signals.map((s, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-gray-500 dark:text-gray-400">{s.date}</span>
                <SignalBadge signal={s.signal} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function VixTermStructureCard() {
  const { t } = useI18n();

  return (
    <div className="tech-card p-4 opacity-60 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('indicators.vixTermStructure' as any)}
        </h3>
        <span className="text-xs text-gray-400">{t('indicators.pendingData' as any)}</span>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        {t('indicators.vixTermStructureDesc' as any)}
      </p>
      <p className="mt-2 text-xs text-amber-500 dark:text-amber-400">
        {t('indicators.vixPending' as any)}
      </p>
    </div>
  );
}

const INDICATOR_KEYS: IndicatorKey[] = ['credit_spread', 'breadth_thrust', 'rfi_acceleration', 'vix_term_structure'];

export function LeadingIndicatorsPage() {
  const { data, loading, error } = useLeadingIndicators();
  const { t } = useI18n();
  const [selectedIndicator, setSelectedIndicator] = useState<IndicatorKey | 'all'>('all');

  if (loading) return <div className="py-12 text-center text-gray-500">{t('common.loading')}</div>;
  if (error) return <div className="py-12 text-center text-red-500">{t('common.error', { message: error })}</div>;
  if (!data) return <div className="py-12 text-center text-gray-500">{t('indicators.noData' as any)}</div>;

  const { indicators } = data;

  // Count active indicators
  const activeCount = INDICATOR_KEYS.filter((k) => indicators[k].available).length;

  // Current signal summary
  const latestSignals: { key: IndicatorKey; signal: string; available: boolean }[] = INDICATOR_KEYS.map((k) => ({
    key: k,
    signal: indicators[k].data.length > 0 ? indicators[k].data[indicators[k].data.length - 1].signal : 'na',
    available: indicators[k].available,
  }));

  const showCard = (key: IndicatorKey) => selectedIndicator === 'all' || selectedIndicator === key;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">
            {t('indicators.title' as any)}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('indicators.subtitle' as any)} · {t('backtest.updated')} {data.date}
          </p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {latestSignals.map(({ key, signal, available }) => (
          <button
            key={key}
            onClick={() => setSelectedIndicator(selectedIndicator === key ? 'all' : key)}
            className={`tech-card cursor-pointer p-3 text-left transition-all ${
              selectedIndicator === key ? 'ring-2 ring-blue-500 dark:ring-blue-400' : ''
            } ${!available ? 'opacity-50' : ''}`}
          >
            <div className="text-[10px] font-medium uppercase text-gray-400">
              {t(`indicators.${key}.short` as any)}
            </div>
            <div className="mt-1">
              <SignalBadge signal={available ? signal : 'na'} />
            </div>
            <div className="mt-1 text-[10px] text-gray-400">
              {available ? `${indicators[key].count} ${t('indicators.dataPoints' as any)}` : t('indicators.pendingData' as any)}
            </div>
          </button>
        ))}
      </div>

      {/* Active indicator count */}
      <div className="text-xs text-gray-400">
        {activeCount}/{INDICATOR_KEYS.length} {t('indicators.active' as any)}
      </div>

      {/* Indicator cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        {showCard('credit_spread') && indicators.credit_spread.available && (
          <CreditSpreadCard data={indicators.credit_spread.data} />
        )}
        {showCard('breadth_thrust') && indicators.breadth_thrust.available && (
          <BreadthThrustCard data={indicators.breadth_thrust.data} />
        )}
        {showCard('rfi_acceleration') && indicators.rfi_acceleration.available && (
          <RfiAccelerationCard data={indicators.rfi_acceleration.data} />
        )}
        {showCard('vix_term_structure') && (
          <VixTermStructureCard />
        )}
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 dark:text-gray-500">
        {t('indicators.disclaimer' as any)}
      </p>
    </div>
  );
}
