import { useEffect, useRef, useMemo, useState } from 'react';
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from 'lightweight-charts';
import type { PriceBar } from '../../types';
import { computeIndicators } from '../../lib/indicators';
import { useTheme } from '../../lib/theme';
import { useI18n } from '../../lib/i18n';

type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y';

const RANGE_DAYS: Record<TimeRange, number> = {
  '1W': 7,
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
};

interface Props {
  prices: PriceBar[];
  ticker: string;
}

export function PriceChart({ prices, ticker }: Props) {
  const [range, setRange] = useState<TimeRange>('6M');
  const mainRef = useRef<HTMLDivElement>(null);
  const rsiRef = useRef<HTMLDivElement>(null);
  const macdRef = useRef<HTMLDivElement>(null);
  const kdjRef = useRef<HTMLDivElement>(null);
  const chartsRef = useRef<IChartApi[]>([]);
  const syncingRef = useRef(false);

  const { theme } = useTheme();
  const { t } = useI18n();
  const isDark = theme === 'dark';

  const indicators = useMemo(() => computeIndicators(prices), [prices]);

  // Create and populate charts
  useEffect(() => {
    const containers = [mainRef.current, rsiRef.current, macdRef.current, kdjRef.current];
    if (containers.some((c) => !c) || prices.length === 0) return;

    const heights = [300, 100, 100, 100];
    const charts: IChartApi[] = [];
    const primarySeries: ISeriesApi<SeriesType>[] = [];

    const bg = isDark ? '#1f2937' : '#ffffff';
    const text = isDark ? '#d1d5db' : '#333';
    const gridColor = isDark ? '#374151' : '#f0f0f0';
    const border = isDark ? '#374151' : '#e5e7eb';

    containers.forEach((el, i) => {
      const chart = createChart(el!, {
        width: el!.clientWidth,
        height: heights[i],
        layout: { background: { color: bg }, textColor: text },
        grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
        rightPriceScale: { borderColor: border },
        timeScale: {
          visible: i === containers.length - 1,
          timeVisible: false,
          rightOffset: 3,
          borderColor: border,
        },
        crosshair: { mode: 0 },
      });
      charts.push(chart);
    });

    // --- Main chart: Candlestick + SMA + BB + Volume ---
    const mc = charts[0];
    const candle = mc.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#ef4444',
      borderUpColor: '#16a34a',
      borderDownColor: '#ef4444',
      wickUpColor: '#16a34a',
      wickDownColor: '#ef4444',
    });
    candle.setData(
      prices.map((p) => ({ time: p.date, open: p.open, high: p.high, low: p.low, close: p.close }))
    );
    primarySeries.push(candle);

    mc.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1, title: 'SMA20' }).setData(
      indicators.filter((d) => d.sma20 != null).map((d) => ({ time: d.date, value: d.sma20! }))
    );
    mc.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 1, title: 'SMA50' }).setData(
      indicators.filter((d) => d.sma50 != null).map((d) => ({ time: d.date, value: d.sma50! }))
    );
    mc.addSeries(LineSeries, { color: 'rgba(156,163,175,0.5)', lineWidth: 1 }).setData(
      indicators.filter((d) => d.bbUpper != null).map((d) => ({ time: d.date, value: d.bbUpper! }))
    );
    mc.addSeries(LineSeries, { color: 'rgba(156,163,175,0.5)', lineWidth: 1 }).setData(
      indicators.filter((d) => d.bbLower != null).map((d) => ({ time: d.date, value: d.bbLower! }))
    );

    const vol = mc.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    });
    mc.priceScale('vol').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    vol.setData(
      prices.map((p) => ({
        time: p.date,
        value: p.volume,
        color: p.close >= p.open ? 'rgba(22,163,74,0.3)' : 'rgba(239,68,68,0.3)',
      }))
    );

    // --- RSI ---
    const rc = charts[1];
    const rsi = rc.addSeries(LineSeries, { color: '#8b5cf6', lineWidth: 2, title: 'RSI (14)' });
    rsi.setData(
      indicators.filter((d) => d.rsi != null).map((d) => ({ time: d.date, value: d.rsi! }))
    );
    rsi.createPriceLine({ price: 70, color: '#ef4444', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
    rsi.createPriceLine({ price: 30, color: '#16a34a', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
    primarySeries.push(rsi);

    // --- MACD ---
    const macdC = charts[2];
    const macdHist = macdC.addSeries(HistogramSeries, {});
    macdHist.setData(
      indicators
        .filter((d) => d.macdHist != null)
        .map((d) => ({
          time: d.date,
          value: d.macdHist!,
          color: d.macdHist! >= 0 ? 'rgba(22,163,74,0.5)' : 'rgba(239,68,68,0.5)',
        }))
    );
    macdC.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 2, title: 'MACD' }).setData(
      indicators.filter((d) => d.macdLine != null).map((d) => ({ time: d.date, value: d.macdLine! }))
    );
    macdC.addSeries(LineSeries, { color: '#f97316', lineWidth: 2, title: 'Signal' }).setData(
      indicators.filter((d) => d.macdSignal != null).map((d) => ({ time: d.date, value: d.macdSignal! }))
    );
    macdHist.createPriceLine({ price: 0, color: '#9ca3af', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
    primarySeries.push(macdHist);

    // --- KDJ (Stochastic) ---
    const kc = charts[3];
    const stK = kc.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 2, title: '%K' });
    stK.setData(
      indicators.filter((d) => d.stochK != null).map((d) => ({ time: d.date, value: d.stochK! }))
    );
    kc.addSeries(LineSeries, { color: '#f97316', lineWidth: 2, title: '%D' }).setData(
      indicators.filter((d) => d.stochD != null).map((d) => ({ time: d.date, value: d.stochD! }))
    );
    stK.createPriceLine({ price: 80, color: '#ef4444', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
    stK.createPriceLine({ price: 20, color: '#16a34a', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
    primarySeries.push(stK);

    // --- Sync visible time ranges ---
    charts.forEach((src, si) => {
      src.timeScale().subscribeVisibleLogicalRangeChange((lr) => {
        if (syncingRef.current || !lr) return;
        syncingRef.current = true;
        charts.forEach((tgt, ti) => {
          if (si !== ti) tgt.timeScale().setVisibleLogicalRange(lr);
        });
        syncingRef.current = false;
      });
    });

    // --- Sync crosshairs ---
    charts.forEach((src, si) => {
      src.subscribeCrosshairMove((param) => {
        if (syncingRef.current) return;
        syncingRef.current = true;
        charts.forEach((tgt, ti) => {
          if (si !== ti) {
            if (param.time) {
              tgt.setCrosshairPosition(undefined as any, param.time, primarySeries[ti]);
            } else {
              tgt.clearCrosshairPosition();
            }
          }
        });
        syncingRef.current = false;
      });
    });

    chartsRef.current = charts;

    // Set initial visible range
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - RANGE_DAYS[range]);
    const from = fromDate.toISOString().slice(0, 10);
    const to = prices[prices.length - 1].date;
    charts.forEach((c) => {
      c.timeScale().setVisibleRange({ from, to } as any);
    });

    // Resize handler
    const handleResize = () => {
      containers.forEach((el, i) => {
        if (el && charts[i]) charts[i].applyOptions({ width: el.clientWidth });
      });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      charts.forEach((c) => c.remove());
      chartsRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prices, indicators, isDark]);

  // Handle range change without recreating charts
  useEffect(() => {
    if (chartsRef.current.length === 0 || prices.length === 0) return;
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - RANGE_DAYS[range]);
    const from = fromDate.toISOString().slice(0, 10);
    const to = prices[prices.length - 1].date;
    chartsRef.current.forEach((c) => c.timeScale().setVisibleRange({ from, to } as any));
  }, [range, prices]);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('detail.priceChart', { ticker })}
        </h2>
        <div className="flex gap-1">
          {(['1W', '1M', '3M', '6M', '1Y'] as TimeRange[]).map((key) => (
            <button
              key={key}
              onClick={() => setRange(key)}
              className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                range === key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {t(`chart.range.${key}` as any)}
            </button>
          ))}
        </div>
      </div>
      <div className="mb-1 flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
        <span>
          <span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: '#f59e0b' }} /> {t('metric.sma20')}
        </span>
        <span>
          <span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: '#3b82f6' }} /> {t('metric.sma50')}
        </span>
        <span>
          <span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: 'rgba(156,163,175,0.5)' }} />{' '}
          {t('chart.bollingerBands')}
        </span>
      </div>
      <div ref={mainRef} />
      <div ref={rsiRef} />
      <div ref={macdRef} />
      <div ref={kdjRef} />
    </div>
  );
}
