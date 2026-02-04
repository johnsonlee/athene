import { useMemo, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { SectorTrend, TrendHistory } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  sectors: SectorTrend[];
  history: TrendHistory | null;
  selectedSector: string | null;
  onSectorSelect: (sector: string | null) => void;
}

type Signal = 'rs_score' | 'momentum_score';
type Range = '3m' | '6m' | '1y' | 'all';
type Interval = 'D' | 'W' | 'M' | 'Q';

const SIGNAL_I18N: Record<Signal, string> = {
  rs_score: 'trends.relativeStrength',
  momentum_score: 'trends.momentum',
};

const RANGE_OPTIONS: { key: Range; i18nKey: string; days: number }[] = [
  { key: '3m', i18nKey: 'trends.range3m', days: 91 },
  { key: '6m', i18nKey: 'trends.range6m', days: 182 },
  { key: '1y', i18nKey: 'trends.range1y', days: 365 },
  { key: 'all', i18nKey: 'trends.rangeAll', days: Infinity },
];

const INTERVAL_OPTIONS: { key: Interval; i18nKey: string }[] = [
  { key: 'D', i18nKey: 'trends.intervalD' },
  { key: 'W', i18nKey: 'trends.intervalW' },
  { key: 'M', i18nKey: 'trends.intervalM' },
  { key: 'Q', i18nKey: 'trends.intervalQ' },
];

/** Distinct colors that read well on both light and dark backgrounds. */
const SECTOR_COLORS: Record<string, string> = {
  'Information Technology': '#6366f1',
  'Financials': '#3b82f6',
  'Energy': '#f97316',
  'Health Care': '#ef4444',
  'Consumer Discretionary': '#a855f7',
  'Consumer Staples': '#22c55e',
  'Real Estate': '#f59e0b',
  'Industrials': '#14b8a6',
  'Utilities': '#84cc16',
  'Materials': '#78716c',
  'Communication Services': '#06b6d4',
};

const EMA_PERIOD = 4;

/**
 * Return a period key for grouping: "2025-W16", "2025-04", "2025-Q2".
 */
function periodKey(dateStr: string, interval: Interval): string {
  if (interval === 'D') return dateStr;
  const d = new Date(dateStr + 'T00:00:00');
  const y = d.getFullYear();
  if (interval === 'W') {
    // ISO week number
    const jan4 = new Date(y, 0, 4);
    const dayOfYear = Math.floor((d.getTime() - new Date(y, 0, 1).getTime()) / 86400000) + 1;
    const wk = Math.ceil((dayOfYear + jan4.getDay() - 1) / 7);
    return `${y}-W${String(wk).padStart(2, '0')}`;
  }
  if (interval === 'M') {
    return `${y}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  }
  // Q
  const q = Math.floor(d.getMonth() / 3) + 1;
  return `${y}-Q${q}`;
}

function computeEMA(values: (number | null)[], period: number): (number | null)[] {
  const alpha = 2 / (period + 1);
  const result: (number | null)[] = [];
  let prev: number | null = null;
  for (const v of values) {
    if (v == null) {
      result.push(prev);
      continue;
    }
    if (prev == null) {
      prev = v;
    } else {
      prev = alpha * v + (1 - alpha) * prev;
    }
    result.push(prev);
  }
  return result;
}

function CustomTooltipContent({ active, payload, label, t, sectorEtfMap, signal }: any) {
  if (!active || !payload?.length) return null;

  const sorted = [...payload]
    .filter((p: any) => p.value != null && p.dataKey !== '_signal')
    .sort((a: any, b: any) => (b.value ?? 0) - (a.value ?? 0));

  return (
    <div className="max-h-80 overflow-y-auto rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg dark:border-gray-700 dark:bg-gray-800">
      <p className="mb-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
        {label} · {t(SIGNAL_I18N[signal as Signal])}
      </p>
      {sorted.map((entry: any) => {
        const sector = entry.dataKey as string;
        const etf = sectorEtfMap[sector] || '';
        return (
          <div key={sector} className="flex items-center justify-between gap-3 py-0.5 text-xs">
            <span className="flex items-center gap-1.5 truncate">
              <span
                className="inline-block h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-gray-700 dark:text-gray-300">
                {t(`sector.${sector}`) || sector}
              </span>
              <span className="font-mono text-gray-400 dark:text-gray-500">{etf}</span>
            </span>
            <span className="font-mono font-medium text-gray-900 dark:text-white">
              {entry.value?.toFixed(0)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ToggleGroup({ options, value, onChange, t }: {
  options: { key: string; i18nKey: string }[];
  value: string;
  onChange: (v: any) => void;
  t: (k: any) => string;
}) {
  return (
    <div className="flex items-center gap-0.5">
      {options.map((opt) => (
        <button
          key={opt.key}
          onClick={() => onChange(opt.key)}
          className={`rounded px-1.5 py-0.5 font-mono text-xs transition-colors ${
            value === opt.key
              ? 'bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-white'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          {t(opt.i18nKey)}
        </button>
      ))}
    </div>
  );
}

const VALID_RANGES: Range[] = ['3m', '6m', '1y', 'all'];
const VALID_INTERVALS: Interval[] = ['D', 'W', 'M', 'Q'];

export function TrendLineChart({ sectors, history, selectedSector, onSectorSelect }: Props) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [showGuide, setShowGuide] = useState(false);

  const rawSignal = searchParams.get('signal');
  const signal: Signal = rawSignal === 'momentum' ? 'momentum_score' : 'rs_score';

  const rawRange = searchParams.get('range') as Range | null;
  const range: Range = rawRange && VALID_RANGES.includes(rawRange) ? rawRange : 'all';

  const rawInterval = searchParams.get('interval') as Interval | null;
  const interval: Interval = rawInterval && VALID_INTERVALS.includes(rawInterval) ? rawInterval : 'W';

  const updateParam = useCallback((key: string, value: string, defaultValue: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value === defaultValue) next.delete(key);
      else next.set(key, value);
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const setSignal = useCallback((s: Signal) => updateParam('signal', s === 'momentum_score' ? 'momentum' : 'rs', 'rs'), [updateParam]);
  const setRange = useCallback((r: Range) => updateParam('range', r, 'all'), [updateParam]);
  const setInterval = useCallback((i: Interval) => updateParam('interval', i, 'W'), [updateParam]);

  const sectorEtfMap = useMemo(
    () => Object.fromEntries(sectors.map((s) => [s.sector, s.etf])),
    [sectors],
  );

  const sectorNames = useMemo(() => sectors.map((s) => s.sector), [sectors]);

  const chartData = useMemo(() => {
    if (!history) return [];

    // 1. Filter by range
    const now = Date.now();
    const rangeDays = RANGE_OPTIONS.find((o) => o.key === range)!.days;
    const cutoff = rangeDays === Infinity ? 0 : now - rangeDays * 86400000;

    const allDates = Object.keys(history)
      .filter((d) => new Date(d).getTime() >= cutoff)
      .sort();

    // 2. Group by interval period, keep last date per period
    const periodLast = new Map<string, string>();
    for (const d of allDates) {
      const pk = periodKey(d, interval);
      periodLast.set(pk, d); // later date overwrites — keeps last
    }
    const sampledDates = [...periodLast.values()].sort();

    // 3. Build rows
    const rows: Record<string, any>[] = [];
    for (const date of sampledDates) {
      const row: Record<string, any> = { date };
      const dayData = history[date];
      for (const sector of sectorNames) {
        const entry = dayData?.[sector];
        row[sector] = entry?.[signal] ?? null;
      }
      rows.push(row);
    }

    // 4. Append current-day from trends.json
    const today = new Date().toISOString().slice(0, 10);
    const currentRow: Record<string, any> = { date: today };
    for (const s of sectors) {
      currentRow[s.sector] =
        signal === 'rs_score'
          ? s.signals.relative_strength.score
          : s.signals.momentum.score;
    }

    if (rows.length > 0 && rows[rows.length - 1].date === today) {
      Object.assign(rows[rows.length - 1], currentRow);
    } else {
      rows.push(currentRow);
    }

    return rows;
  }, [history, sectors, sectorNames, signal, range, interval]);

  // Compute signal line + histogram for selected sector
  const { augmentedData, histogramData } = useMemo(() => {
    if (!selectedSector || !chartData.length) {
      return { augmentedData: chartData, histogramData: null };
    }

    const values = chartData.map((row) => row[selectedSector] as number | null);
    const emaValues = computeEMA(values, EMA_PERIOD);

    const augmented = chartData.map((row, i) => ({
      ...row,
      _signal: emaValues[i],
    }));

    const hist = chartData.map((row, i) => {
      const v = values[i];
      const s = emaValues[i];
      return {
        date: row.date,
        hist: v != null && s != null ? +(v - s).toFixed(1) : null,
      };
    });

    return { augmentedData: augmented, histogramData: hist };
  }, [chartData, selectedSector]);

  const handleSectorClick = useCallback((sector: string) => {
    onSectorSelect(selectedSector === sector ? null : sector);
  }, [selectedSector, onSectorSelect]);

  const isDark = document.documentElement.classList.contains('dark');
  const gridColor = isDark ? '#374151' : '#e5e7eb';
  const axisColor = isDark ? '#9ca3af' : '#6b7280';
  const refLineColor = isDark ? '#4b5563' : '#d1d5db';

  const tickFormatter = useCallback((v: string) => {
    if (!v || v === 'now') return '';
    const parts = v.split('-');
    if (parts.length < 3) return v;
    if (interval === 'Q') return `${parts[0].slice(2)}Q${Math.floor((+parts[1] - 1) / 3) + 1}`;
    if (interval === 'M') return `${parts[1]}/${parts[0].slice(2)}`;
    return `${parts[1]}/${parts[2]}`;
  }, [interval]);

  return (
    <div className="tech-card">
      {/* Controls */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-y-2 px-3 pt-3 text-xs">
        {/* Signal */}
        <ToggleGroup
          options={Object.entries(SIGNAL_I18N).map(([k, v]) => ({ key: k, i18nKey: v }))}
          value={signal}
          onChange={setSignal}
          t={t}
        />

        <div className="flex items-center gap-x-4">
          {/* Range */}
          <div className="flex items-center gap-1">
            <span className="text-gray-500 dark:text-gray-400">{t('trends.range' as any)}</span>
            <ToggleGroup options={RANGE_OPTIONS} value={range} onChange={setRange} t={t} />
          </div>

          {/* Interval */}
          <div className="flex items-center gap-1">
            <span className="text-gray-500 dark:text-gray-400">{t('trends.interval' as any)}</span>
            <ToggleGroup options={INTERVAL_OPTIONS} value={interval} onChange={setInterval} t={t} />
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 px-1 text-xs">
        {sectorNames.map((sector) => {
          const isSelected = selectedSector === sector;
          const isDimmed = selectedSector != null && !isSelected;
          const color = SECTOR_COLORS[sector] || '#6b7280';
          const etf = sectorEtfMap[sector];
          return (
            <button
              key={sector}
              onClick={() => handleSectorClick(sector)}
              className={`flex items-center gap-1 rounded px-1 py-0.5 transition-all ${
                isSelected
                  ? 'bg-gray-100 ring-1 ring-gray-300 dark:bg-gray-800 dark:ring-gray-600'
                  : isDimmed
                    ? 'opacity-40'
                    : ''
              }`}
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-gray-600 dark:text-gray-400">
                {etf}
                {(t(`sector.${sector}` as any) as string) !== sector && (
                  <span className="ml-0.5 text-gray-400 dark:text-gray-500">
                    {t(`sector.${sector}` as any)}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>

      {/* Main chart */}
      <div className={selectedSector ? 'h-[240px] sm:h-[320px]' : 'h-[300px] sm:h-[400px]'}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={augmentedData} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: axisColor }}
              stroke={gridColor}
              tickFormatter={tickFormatter}
              interval="preserveStartEnd"
              minTickGap={40}
              hide={!!selectedSector}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tick={{ fontSize: 10, fill: axisColor }}
              stroke={gridColor}
              width={30}
            />
            <ReferenceLine y={50} stroke={refLineColor} strokeDasharray="4 4" />
            <Tooltip
              content={
                <CustomTooltipContent
                  t={t}
                  sectorEtfMap={sectorEtfMap}
                  signal={signal}
                />
              }
            />
            {sectorNames.map((sector) => {
              const isSelected = selectedSector === sector;
              const isDimmed = selectedSector != null && !isSelected;
              return (
                <Line
                  key={sector}
                  type="monotone"
                  dataKey={sector}
                  stroke={SECTOR_COLORS[sector] || '#6b7280'}
                  strokeWidth={isSelected ? 2.5 : isDimmed ? 1 : 1.5}
                  strokeOpacity={isDimmed ? 0.2 : 1}
                  dot={false}
                  activeDot={{
                    r: 4,
                    cursor: 'pointer',
                    onClick: () =>
                      navigate(`/screener?sector=${encodeURIComponent(sector)}`),
                  }}
                  connectNulls
                />
              );
            })}
            {selectedSector && (
              <Line
                type="monotone"
                dataKey="_signal"
                stroke={SECTOR_COLORS[selectedSector] || '#6b7280'}
                strokeWidth={1}
                strokeDasharray="6 3"
                strokeOpacity={0.6}
                dot={false}
                activeDot={false}
                connectNulls
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Histogram */}
      {selectedSector && histogramData && (
        <div className="h-[80px] sm:h-[100px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogramData} margin={{ top: 0, right: 12, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: axisColor }}
                stroke={gridColor}
                tickFormatter={tickFormatter}
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis
                tick={{ fontSize: 10, fill: axisColor }}
                stroke={gridColor}
                width={30}
              />
              <ReferenceLine y={0} stroke={refLineColor} />
              <Tooltip
                formatter={(value: any) => [Number(value)?.toFixed(1), t('trends.histogram' as any)]}
                labelFormatter={(label: any) => tickFormatter(String(label))}
                contentStyle={{
                  fontSize: 12,
                  backgroundColor: isDark ? '#1f2937' : '#fff',
                  borderColor: isDark ? '#374151' : '#e5e7eb',
                  color: isDark ? '#e5e7eb' : '#111827',
                }}
              />
              <Bar dataKey="hist" radius={[2, 2, 0, 0]}>
                {histogramData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={entry.hist != null && entry.hist >= 0 ? '#22c55e' : '#ef4444'}
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* How to read guide */}
      <div className="border-t border-gray-100 px-3 pb-3 pt-2 dark:border-gray-800">
        <button
          onClick={() => setShowGuide((v) => !v)}
          className="text-xs text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
        >
          {t('trends.howToRead' as any)} {showGuide ? '▾' : '▸'}
        </button>
        {showGuide && (
          <div className="mt-2 space-y-2 text-xs text-gray-500 dark:text-gray-400">
            <p>{t('trends.guideLine' as any)}</p>
            <p>{t('trends.guideSignal' as any)}</p>
            <div className="space-y-1 pl-2">
              <p className="flex items-start gap-1.5">
                <span className="mt-0.5 inline-block h-2.5 w-2.5 shrink-0 rounded-sm bg-green-500/80" />
                {t('trends.guideBullish' as any)}
              </p>
              <p className="flex items-start gap-1.5">
                <span className="mt-0.5 inline-block h-2.5 w-2.5 shrink-0 rounded-sm bg-red-500/80" />
                {t('trends.guideBearish' as any)}
              </p>
            </div>
            <p>{t('trends.guideTurn' as any)}</p>
          </div>
        )}
      </div>
    </div>
  );
}
