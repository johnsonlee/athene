import { useEffect, useRef, useMemo } from 'react';
import { createChart, type IChartApi, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';
import type { PriceBar } from '../../types';
import { computeIndicators } from '../../lib/indicators';
import { useTheme } from '../../lib/theme';
import { useI18n } from '../../lib/i18n';

interface Props {
  prices: PriceBar[];
  ticker: string;
}

export function PriceChart({ prices, ticker }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const indicators = useMemo(() => computeIndicators(prices), [prices]);
  const { theme } = useTheme();
  const { t } = useI18n();
  const isDark = theme === 'dark';

  useEffect(() => {
    if (!containerRef.current || prices.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: isDark ? '#1f2937' : '#ffffff' },
        textColor: isDark ? '#d1d5db' : '#333',
      },
      grid: {
        vertLines: { color: isDark ? '#374151' : '#f0f0f0' },
        horzLines: { color: isDark ? '#374151' : '#f0f0f0' },
      },
      timeScale: {
        timeVisible: false,
      },
    });

    chartRef.current = chart;

    // Candlestick
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#ef4444',
      borderUpColor: '#16a34a',
      borderDownColor: '#ef4444',
      wickUpColor: '#16a34a',
      wickDownColor: '#ef4444',
    });

    candleSeries.setData(
      prices.map((p) => ({
        time: p.date,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      }))
    );

    // SMA 20
    const sma20Series = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 1,
      title: 'SMA20',
    });
    sma20Series.setData(
      indicators
        .filter((d) => d.sma20 != null)
        .map((d) => ({ time: d.date, value: d.sma20! }))
    );

    // SMA 50
    const sma50Series = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 1,
      title: 'SMA50',
    });
    sma50Series.setData(
      indicators
        .filter((d) => d.sma50 != null)
        .map((d) => ({ time: d.date, value: d.sma50! }))
    );

    // Bollinger Bands
    const bbUpperSeries = chart.addSeries(LineSeries, {
      color: 'rgba(156,163,175,0.5)',
      lineWidth: 1,
      title: 'BB Upper',
    });
    bbUpperSeries.setData(
      indicators
        .filter((d) => d.bbUpper != null)
        .map((d) => ({ time: d.date, value: d.bbUpper! }))
    );

    const bbLowerSeries = chart.addSeries(LineSeries, {
      color: 'rgba(156,163,175,0.5)',
      lineWidth: 1,
      title: 'BB Lower',
    });
    bbLowerSeries.setData(
      indicators
        .filter((d) => d.bbLower != null)
        .map((d) => ({ time: d.date, value: d.bbLower! }))
    );

    // Volume
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    volumeSeries.setData(
      prices.map((p) => ({
        time: p.date,
        value: p.volume,
        color: p.close >= p.open ? 'rgba(22,163,74,0.3)' : 'rgba(239,68,68,0.3)',
      }))
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [prices, indicators, isDark]);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('detail.priceChart', { ticker })}</h2>
      <div className="mb-1 flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
        <span><span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: '#f59e0b' }} /> {t('metric.sma20')}</span>
        <span><span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: '#3b82f6' }} /> {t('metric.sma50')}</span>
        <span><span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: 'rgba(156,163,175,0.5)' }} /> {t('chart.bollingerBands')}</span>
      </div>
      <div ref={containerRef} />
    </div>
  );
}
