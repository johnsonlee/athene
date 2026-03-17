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

type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y' | 'All';
type Interval = 'D' | 'W' | 'M' | 'Q';
type IndicatorPanel = 'rsi' | 'macd' | 'kdj';
type Overlay = 'sma60' | 'sma200' | 'dc';

/** Compute simple moving average from daily close prices. */
function computeSMA(prices: PriceBar[], period: number): { time: string; value: number }[] {
  const result: { time: string; value: number }[] = [];
  for (let i = period - 1; i < prices.length; i++) {
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) {
      sum += prices[j].close;
    }
    result.push({ time: prices[i].date, value: sum / period });
  }
  return result;
}

/** Aggregate daily bars into weekly or monthly bars. */
function aggregateBars(bars: PriceBar[], interval: Interval): PriceBar[] {
  if (interval === 'D' || bars.length === 0) return bars;
  const buckets: PriceBar[][] = [];
  let current: PriceBar[] = [];
  let currentKey = '';

  for (const bar of bars) {
    let key: string;
    if (interval === 'W') {
      // ISO week: Monday-based — use the Monday date as key
      const d = new Date(bar.date);
      const day = d.getUTCDay();
      const diff = day === 0 ? -6 : 1 - day; // shift to Monday
      const monday = new Date(d);
      monday.setUTCDate(d.getUTCDate() + diff);
      key = monday.toISOString().slice(0, 10);
    } else if (interval === 'Q') {
      const q = Math.floor((parseInt(bar.date.slice(5, 7), 10) - 1) / 3);
      key = `${bar.date.slice(0, 4)}-Q${q}`;
    } else {
      key = bar.date.slice(0, 7); // YYYY-MM
    }
    if (key !== currentKey) {
      if (current.length > 0) buckets.push(current);
      current = [];
      currentKey = key;
    }
    current.push(bar);
  }
  if (current.length > 0) buckets.push(current);

  return buckets.map((group) => ({
    date: group[0].date,
    open: group[0].open,
    high: Math.max(...group.map((b) => b.high)),
    low: Math.min(...group.map((b) => b.low)),
    close: group[group.length - 1].close,
    volume: group.reduce((sum, b) => sum + b.volume, 0),
  }));
}

const RANGE_DAYS: Record<TimeRange, number> = {
  '1W': 7,
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
  'All': 0,
};

interface Props {
  prices: PriceBar[];
  ticker: string;
}

export function PriceChart({ prices, ticker }: Props) {
  const [range, setRange] = useState<TimeRange>('1Y');
  const isMobileInit = typeof window !== 'undefined' && window.innerWidth < 640;
  const [visiblePanels, setVisiblePanels] = useState<Record<IndicatorPanel, boolean>>({
    rsi: !isMobileInit,
    macd: !isMobileInit,
    kdj: !isMobileInit,
  });
  const [interval, setInterval] = useState<Interval>('D');
  const [overlays, setOverlays] = useState<Record<Overlay, boolean>>({
    sma60: true,
    sma200: true,
    dc: true,
  });

  const mainRef = useRef<HTMLDivElement>(null);
  const rsiRef = useRef<HTMLDivElement>(null);
  const macdRef = useRef<HTMLDivElement>(null);
  const kdjRef = useRef<HTMLDivElement>(null);
  const chartsRef = useRef<IChartApi[]>([]);
  const syncingRef = useRef(false);

  const { theme } = useTheme();
  const { t, locale } = useI18n();
  const isDark = theme === 'dark';

  const displayPrices = useMemo(() => aggregateBars(prices, interval), [prices, interval]);
  const indicators = useMemo(() => computeIndicators(displayPrices), [displayPrices]);

  const togglePanel = (panel: IndicatorPanel) => {
    setVisiblePanels((prev) => ({ ...prev, [panel]: !prev[panel] }));
  };

  // Create and populate charts
  useEffect(() => {
    if (!mainRef.current || displayPrices.length === 0) return;

    // Build panel list based on visibility
    type PanelType = 'main' | IndicatorPanel;
    const panelRefs: { type: PanelType; ref: React.RefObject<HTMLDivElement | null> }[] = [
      { type: 'main', ref: mainRef },
    ];
    if (visiblePanels.rsi) panelRefs.push({ type: 'rsi', ref: rsiRef });
    if (visiblePanels.macd) panelRefs.push({ type: 'macd', ref: macdRef });
    if (visiblePanels.kdj) panelRefs.push({ type: 'kdj', ref: kdjRef });

    const containers = panelRefs.map((p) => p.ref.current).filter(Boolean) as HTMLDivElement[];
    const panelTypes = panelRefs.filter((p) => p.ref.current).map((p) => p.type);
    if (containers.length === 0) return;

    const isMobile = window.innerWidth < 640;
    const mainHeight = isMobile ? 220 : 300;
    const subHeight = isMobile ? 100 : 120;
    const timeAxisHeight = 26;

    const charts: IChartApi[] = [];
    const primarySeries: ISeriesApi<SeriesType>[] = [];

    const bg = isDark ? '#0d1322' : '#ffffff';
    const text = isDark ? '#64748b' : '#333';
    const gridColor = isDark ? 'rgba(6,182,212,0.06)' : '#f0f0f0';
    const border = isDark ? 'rgba(6,182,212,0.12)' : '#e5e7eb';
    const upC = locale === 'zh' ? '#ef4444' : '#16a34a';
    const downC = locale === 'zh' ? '#16a34a' : '#ef4444';
    const upCAlpha = locale === 'zh' ? 'rgba(239,68,68,' : 'rgba(22,163,74,';
    const downCAlpha = locale === 'zh' ? 'rgba(22,163,74,' : 'rgba(239,68,68,';

    containers.forEach((el, i) => {
      const isLast = i === containers.length - 1;
      const h = panelTypes[i] === 'main' ? mainHeight : subHeight + (isLast ? timeAxisHeight : 0);
      const chart = createChart(el, {
        width: el.clientWidth,
        height: h,
        layout: { background: { color: bg }, textColor: text, attributionLogo: false },
        grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
        rightPriceScale: { borderColor: border, minimumWidth: 80, scaleMargins: { top: 0.08, bottom: 0.08 } },
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

    // Full date range reference for sub-charts
    const fullDates = displayPrices.map((p) => ({ time: p.date, value: 0 }));
    const addTimeRef = (chart: IChartApi) => {
      const ref = chart.addSeries(LineSeries, {
        color: 'transparent',
        lineWidth: 1,
        priceScaleId: '_ref',
        lastValueVisible: false,
        priceLineVisible: false,
      });
      ref.setData(fullDates);
      chart.priceScale('_ref').applyOptions({ scaleMargins: { top: 0.99, bottom: 0 } });
    };

    // Create series for each panel
    panelTypes.forEach((type, i) => {
      const chart = charts[i];

      if (type === 'main') {
        // Candlestick + SMA + BB + Volume
        const candle = chart.addSeries(CandlestickSeries, {
          upColor: upC,
          downColor: downC,
          borderUpColor: upC,
          borderDownColor: downC,
          wickUpColor: upC,
          wickDownColor: downC,
        });
        candle.setData(
          displayPrices.map((p) => ({ time: p.date, open: p.open, high: p.high, low: p.low, close: p.close }))
        );
        primarySeries.push(candle);

        if (overlays.sma60) {
          const sma60Data = computeSMA(displayPrices, 60);
          chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }).setData(sma60Data);
        }
        if (overlays.sma200) {
          const sma200Data = computeSMA(displayPrices, 200);
          chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }).setData(sma200Data);
        }
        if (overlays.dc) {
          chart.addSeries(LineSeries, { color: 'rgba(156,163,175,0.5)', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }).setData(
            indicators.filter((d) => d.dcUpper != null).map((d) => ({ time: d.date, value: d.dcUpper! }))
          );
          chart.addSeries(LineSeries, { color: 'rgba(156,163,175,0.5)', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }).setData(
            indicators.filter((d) => d.dcLower != null).map((d) => ({ time: d.date, value: d.dcLower! }))
          );
        }
        const vol = chart.addSeries(HistogramSeries, {
          priceFormat: { type: 'volume' },
          priceScaleId: 'vol',
          priceLineVisible: false,
        });
        chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
        vol.setData(
          displayPrices.map((p) => ({
            time: p.date,
            value: p.volume,
            color: p.close >= p.open ? `${upCAlpha}0.3)` : `${downCAlpha}0.3)`,
          }))
        );
      } else if (type === 'rsi') {
        addTimeRef(chart);
        const rsi6 = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        rsi6.setData(indicators.filter((d) => d.rsi6 != null).map((d) => ({ time: d.date, value: d.rsi6! })));
        const rsi14 = chart.addSeries(LineSeries, { color: '#8b5cf6', lineWidth: 2 });
        rsi14.setData(indicators.filter((d) => d.rsi != null).map((d) => ({ time: d.date, value: d.rsi! })));
        const rsi24 = chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        rsi24.setData(indicators.filter((d) => d.rsi24 != null).map((d) => ({ time: d.date, value: d.rsi24! })));
        rsi14.createPriceLine({ price: 80, color: '#ef4444', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        rsi14.createPriceLine({ price: 50, color: '#9ca3af', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        rsi14.createPriceLine({ price: 20, color: '#16a34a', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        primarySeries.push(rsi14);
      } else if (type === 'macd') {
        addTimeRef(chart);
        const macdHist = chart.addSeries(HistogramSeries, { priceLineVisible: false });
        macdHist.setData(
          indicators
            .filter((d) => d.macdHist != null)
            .map((d) => ({
              time: d.date,
              value: d.macdHist!,
              color: d.macdHist! >= 0 ? `${upCAlpha}0.5)` : `${downCAlpha}0.5)`,
            }))
        );
        chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 2, priceLineVisible: false }).setData(
          indicators.filter((d) => d.macdLine != null).map((d) => ({ time: d.date, value: d.macdLine! }))
        );
        chart.addSeries(LineSeries, { color: '#f97316', lineWidth: 2, priceLineVisible: false }).setData(
          indicators.filter((d) => d.macdSignal != null).map((d) => ({ time: d.date, value: d.macdSignal! }))
        );
        macdHist.createPriceLine({ price: 0, color: '#9ca3af', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        primarySeries.push(macdHist);
      } else if (type === 'kdj') {
        addTimeRef(chart);
        const stK = chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 2, priceLineVisible: false });
        stK.setData(
          indicators.filter((d) => d.stochK != null).map((d) => ({ time: d.date, value: d.stochK! }))
        );
        chart.addSeries(LineSeries, { color: '#f97316', lineWidth: 2, priceLineVisible: false }).setData(
          indicators.filter((d) => d.stochD != null).map((d) => ({ time: d.date, value: d.stochD! }))
        );
        stK.createPriceLine({ price: 80, color: '#ef4444', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        stK.createPriceLine({ price: 50, color: '#9ca3af', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        stK.createPriceLine({ price: 20, color: '#16a34a', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        primarySeries.push(stK);
      }
    });

    // --- Crosshair legends (tooltip) ---
    const indicatorMap = new Map<string, (typeof indicators)[0]>();
    indicators.forEach((d) => indicatorMap.set(d.date, d));
    const priceMap = new Map<string, (typeof displayPrices)[0]>();
    displayPrices.forEach((p) => priceMap.set(p.date, p));

    const legendColor = isDark ? 'rgba(255,255,255,0.65)' : 'rgba(0,0,0,0.55)';
    const legendEls: HTMLDivElement[] = [];
    containers.forEach((el) => {
      const legend = document.createElement('div');
      legend.style.cssText = `font-size:11px;line-height:1.4;min-height:16px;font-family:ui-monospace,monospace;color:${legendColor};padding:0 0 2px 4px`;
      el.parentNode!.insertBefore(legend, el);
      legendEls.push(legend);
    });

    const fmtTime = (t: unknown): string => {
      if (typeof t === 'string') return t;
      if (t && typeof t === 'object' && 'year' in t) {
        const bd = t as { year: number; month: number; day: number };
        return `${bd.year}-${String(bd.month).padStart(2, '0')}-${String(bd.day).padStart(2, '0')}`;
      }
      return '';
    };

    const updateLegend = (legend: HTMLDivElement, type: string, dateStr: string) => {
      const ind = indicatorMap.get(dateStr);
      if (type === 'main') {
        const p = priceMap.get(dateStr);
        if (p) {
          legend.innerHTML =
            `O:<b>${p.open.toFixed(2)}</b> H:<b>${p.high.toFixed(2)}</b> L:<b>${p.low.toFixed(2)}</b> C:<b>${p.close.toFixed(2)}</b>`;
        } else { legend.innerHTML = ''; }
      } else if (type === 'rsi' && ind) {
        const parts: string[] = [];
        if (ind.rsi6 != null) parts.push(`<span style="color:#f59e0b">6: <b>${ind.rsi6.toFixed(1)}</b></span>`);
        if (ind.rsi != null) parts.push(`<span style="color:#8b5cf6">14: <b>${ind.rsi.toFixed(1)}</b></span>`);
        if (ind.rsi24 != null) parts.push(`<span style="color:#3b82f6">24: <b>${ind.rsi24.toFixed(1)}</b></span>`);
        legend.innerHTML = parts.join(' ');
      } else if (type === 'macd' && ind) {
        const parts: string[] = [];
        if (ind.macdLine != null) parts.push(`<span style="color:#3b82f6">MACD: <b>${ind.macdLine.toFixed(3)}</b></span>`);
        if (ind.macdSignal != null) parts.push(`<span style="color:#f97316">Signal: <b>${ind.macdSignal.toFixed(3)}</b></span>`);
        if (ind.macdHist != null) parts.push(`<span style="color:${ind.macdHist >= 0 ? upC : downC}">Hist: <b>${ind.macdHist.toFixed(3)}</b></span>`);
        legend.innerHTML = parts.join(' ');
      } else if (type === 'kdj' && ind) {
        const parts: string[] = [];
        if (ind.stochK != null) parts.push(`<span style="color:#3b82f6">%K: <b>${ind.stochK.toFixed(1)}</b></span>`);
        if (ind.stochD != null) parts.push(`<span style="color:#f97316">%D: <b>${ind.stochD.toFixed(1)}</b></span>`);
        legend.innerHTML = parts.join(' ');
      } else { legend.innerHTML = ''; }
    };

    // Show latest values by default
    const latestDate = displayPrices[displayPrices.length - 1]?.date;
    if (latestDate) {
      charts.forEach((_, ci) => updateLegend(legendEls[ci], panelTypes[ci], latestDate));
    }

    charts.forEach((chart, ci) => {
      const legend = legendEls[ci];
      const type = panelTypes[ci];
      chart.subscribeCrosshairMove((param) => {
        if (!param.time) {
          // Mouse left chart — restore latest values
          if (latestDate) updateLegend(legend, type, latestDate);
          return;
        }
        updateLegend(legend, type, fmtTime(param.time));
      });
    });

    // Sync visible time ranges
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

    // Sync crosshairs
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
    if (range === 'All') {
      charts.forEach((c) => c.timeScale().fitContent());
    } else {
      const fromDate = new Date();
      fromDate.setDate(fromDate.getDate() - RANGE_DAYS[range]);
      const from = fromDate.toISOString().slice(0, 10);
      const to = displayPrices[displayPrices.length - 1].date;
      charts.forEach((c) => {
        c.timeScale().setVisibleRange({ from, to } as any);
      });
      // Scroll so rightOffset takes effect after setVisibleRange
      charts.forEach((c) => c.timeScale().scrollToRealTime());
    }

    // Resize handler
    const handleResize = () => {
      const mobileNow = window.innerWidth < 640;
      const mH = mobileNow ? 220 : 300;
      const sH = mobileNow ? 80 : 100;
      containers.forEach((el, i) => {
        if (el && charts[i]) {
          const last = i === containers.length - 1;
          charts[i].applyOptions({
            width: el.clientWidth,
            height: panelTypes[i] === 'main' ? mH : sH + (last ? timeAxisHeight : 0),
          });
        }
      });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      legendEls.forEach((el) => el.remove());
      charts.forEach((c) => c.remove());
      chartsRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayPrices, indicators, isDark, locale, visiblePanels.rsi, visiblePanels.macd, visiblePanels.kdj, overlays.sma60, overlays.sma200, overlays.dc]);

  // Handle range change without recreating charts
  useEffect(() => {
    if (chartsRef.current.length === 0 || displayPrices.length === 0) return;
    if (range === 'All') {
      chartsRef.current.forEach((c) => c.timeScale().fitContent());
    } else {
      const fromDate = new Date();
      fromDate.setDate(fromDate.getDate() - RANGE_DAYS[range]);
      const from = fromDate.toISOString().slice(0, 10);
      const to = displayPrices[displayPrices.length - 1].date;
      chartsRef.current.forEach((c) => {
        c.timeScale().setVisibleRange({ from, to } as any);
        c.timeScale().scrollToRealTime();
      });
    }
  }, [range, displayPrices]);

  const panelButtons: { key: IndicatorPanel; label: string }[] = [
    { key: 'rsi', label: t('chart.rsi14') },
    { key: 'macd', label: t('chart.macd1226') },
    { key: 'kdj', label: t('chart.stochastic') },
  ];

  return (
    <div className="tech-card p-3 sm:p-4">
      <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="tech-heading text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
          {t('detail.priceChart', { ticker })}
        </h2>
        <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-2">
          <div className="flex items-center gap-1.5">
            <span className="shrink-0 text-[10px] text-gray-400 dark:text-gray-500">{t('chart.rangeLabel')}</span>
            <div className="flex gap-0.5">
              {(['1W', '1M', '3M', '6M', '1Y', 'All'] as TimeRange[]).map((key) => (
                <button
                  key={key}
                  onClick={() => setRange(key)}
                  className={`rounded px-2 py-1 text-[11px] font-medium transition-colors sm:px-2 sm:py-0.5 sm:text-xs ${
                    range === key
                      ? 'tech-btn-active bg-blue-600 text-white dark:bg-transparent'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-700/50 dark:text-gray-400 dark:hover:bg-slate-600/50'
                  }`}
                >
                  {t(`chart.range.${key}` as any)}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="shrink-0 text-[10px] text-gray-400 dark:text-gray-500">{t('chart.intervalLabel')}</span>
            <div className="flex gap-0.5">
              {(['D', 'W', 'M', 'Q'] as Interval[]).map((key) => (
                <button
                  key={key}
                  onClick={() => setInterval(key)}
                  className={`rounded px-2 py-1 text-[11px] font-medium transition-colors sm:px-2 sm:py-0.5 sm:text-xs ${
                    interval === key
                      ? 'tech-btn-active bg-blue-600 text-white dark:bg-transparent'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-700/50 dark:text-gray-400 dark:hover:bg-slate-600/50'
                  }`}
                >
                  {t(`chart.interval.${key}` as any)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main chart overlay toggles */}
      <div className="mb-1 flex flex-wrap gap-1">
        {([
          { key: 'sma60' as Overlay, color: '#f59e0b', label: t('metric.sma60') },
          { key: 'sma200' as Overlay, color: '#3b82f6', label: t('metric.sma200') },
          { key: 'dc' as Overlay, color: 'rgba(156,163,175,0.5)', label: t('chart.donchianChannel') },
        ]).map(({ key, color, label }) => (
          <button
            key={key}
            onClick={() => setOverlays((prev) => ({ ...prev, [key]: !prev[key] }))}
            className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-medium transition-colors sm:text-xs ${
              overlays[key]
                ? 'bg-blue-100 text-blue-700 dark:bg-cyan-500/15 dark:text-cyan-300'
                : 'bg-gray-100 text-gray-400 dark:bg-slate-700/30 dark:text-gray-500'
            }`}
          >
            <span className="inline-block h-2 w-3 rounded" style={{ backgroundColor: color, opacity: overlays[key] ? 1 : 0.4 }} />
            {label}
          </button>
        ))}
      </div>

      {/* Main price chart */}
      <div ref={mainRef} />

      {/* Indicator toggle buttons */}
      <div className="my-1.5 flex flex-wrap gap-1">
        {panelButtons.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => togglePanel(key)}
            className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors sm:text-xs ${
              visiblePanels[key]
                ? 'bg-blue-100 text-blue-700 dark:bg-cyan-500/15 dark:text-cyan-300'
                : 'bg-gray-100 text-gray-400 dark:bg-slate-700/30 dark:text-gray-500'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Indicator sub-charts — only rendered when visible */}
      {visiblePanels.rsi && <div ref={rsiRef} className="mt-1.5" />}
      {visiblePanels.macd && <div ref={macdRef} className="mt-1.5" />}
      {visiblePanels.kdj && <div ref={kdjRef} className="mt-1.5" />}
    </div>
  );
}
