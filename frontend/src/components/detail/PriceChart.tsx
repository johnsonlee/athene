import { useEffect, useRef } from 'react';
import { createChart, type IChartApi, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import type { PriceBar } from '../../types';

interface Props {
  prices: PriceBar[];
  ticker: string;
}

export function PriceChart({ prices, ticker }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || prices.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      timeScale: {
        timeVisible: false,
      },
    });

    chartRef.current = chart;

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
  }, [prices]);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <h2 className="mb-2 text-lg font-semibold text-gray-900">{ticker} Price Chart</h2>
      <div ref={containerRef} />
    </div>
  );
}
