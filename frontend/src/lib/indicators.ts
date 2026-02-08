/**
 * Compute technical indicators from OHLCV price bars.
 * All functions take arrays of numbers and return arrays of the same length
 * (with leading NaN/null where insufficient data).
 */

export interface IndicatorBar {
  date: string;
  close: number;
  volume: number;
  sma20: number | null;
  sma50: number | null;
  rsi: number | null;
  macdLine: number | null;
  macdSignal: number | null;
  macdHist: number | null;
  dcUpper: number | null;
  dcLower: number | null;
  dcMiddle: number | null;
  stochK: number | null;
  stochD: number | null;
}

function sma(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += values[j];
      result.push(sum / period);
    }
  }
  return result;
}

function ema(values: number[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const result: (number | null)[] = [];
  let prev: number | null = null;
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else if (prev === null) {
      // Seed with SMA
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += values[j];
      prev = sum / period;
      result.push(prev);
    } else {
      prev = values[i] * k + prev * (1 - k);
      result.push(prev);
    }
  }
  return result;
}

function computeRSI(closes: number[], period = 14): (number | null)[] {
  const result: (number | null)[] = [null]; // first element has no change
  const changes: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    changes.push(closes[i] - closes[i - 1]);
  }

  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 0; i < changes.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else if (i === period - 1) {
      // Initial averages
      let gains = 0, losses = 0;
      for (let j = 0; j <= i; j++) {
        if (changes[j] > 0) gains += changes[j];
        else losses -= changes[j];
      }
      avgGain = gains / period;
      avgLoss = losses / period;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      result.push(100 - 100 / (1 + rs));
    } else {
      const change = changes[i];
      avgGain = (avgGain * (period - 1) + (change > 0 ? change : 0)) / period;
      avgLoss = (avgLoss * (period - 1) + (change < 0 ? -change : 0)) / period;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      result.push(100 - 100 / (1 + rs));
    }
  }
  return result;
}

function computeMACD(
  closes: number[],
  fast = 12,
  slow = 26,
  signal = 9,
): { line: (number | null)[]; signal: (number | null)[]; histogram: (number | null)[] } {
  const emaFast = ema(closes, fast);
  const emaSlow = ema(closes, slow);
  const macdLine: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (emaFast[i] != null && emaSlow[i] != null) {
      macdLine.push(emaFast[i]! - emaSlow[i]!);
    } else {
      macdLine.push(null);
    }
  }

  // Signal = EMA of MACD line (only from non-null values)
  const nonNullStart = macdLine.findIndex((v) => v != null);
  if (nonNullStart === -1) {
    // Not enough data for MACD — return all nulls
    const allNull = Array(closes.length).fill(null);
    return { line: allNull, signal: allNull, histogram: allNull };
  }
  const macdValues = macdLine.slice(nonNullStart).map((v) => v!);
  const signalEma = ema(macdValues, signal);

  const signalLine: (number | null)[] = Array(nonNullStart).fill(null);
  const histogram: (number | null)[] = Array(nonNullStart).fill(null);
  for (let i = 0; i < macdValues.length; i++) {
    signalLine.push(signalEma[i]);
    if (signalEma[i] != null) {
      histogram.push(macdValues[i] - signalEma[i]!);
    } else {
      histogram.push(null);
    }
  }

  return { line: macdLine, signal: signalLine, histogram };
}

function computeDonchian(
  highs: number[],
  lows: number[],
  period = 20,
): { upper: (number | null)[]; lower: (number | null)[]; middle: (number | null)[] } {
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  const middle: (number | null)[] = [];
  for (let i = 0; i < highs.length; i++) {
    if (i < period - 1) {
      upper.push(null);
      lower.push(null);
      middle.push(null);
    } else {
      let highest = -Infinity, lowest = Infinity;
      for (let j = i - period + 1; j <= i; j++) {
        if (highs[j] > highest) highest = highs[j];
        if (lows[j] < lowest) lowest = lows[j];
      }
      upper.push(highest);
      lower.push(lowest);
      middle.push((highest + lowest) / 2);
    }
  }
  return { upper, lower, middle };
}

function computeStochastic(
  highs: number[],
  lows: number[],
  closes: number[],
  period = 14,
  smoothK = 3,
): { k: (number | null)[]; d: (number | null)[] } {
  const rawK: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      rawK.push(null);
    } else {
      let highest = -Infinity, lowest = Infinity;
      for (let j = i - period + 1; j <= i; j++) {
        if (highs[j] > highest) highest = highs[j];
        if (lows[j] < lowest) lowest = lows[j];
      }
      const range = highest - lowest;
      rawK.push(range === 0 ? 50 : ((closes[i] - lowest) / range) * 100);
    }
  }

  // %K = SMA(smoothK) of rawK
  const kLine: (number | null)[] = [];
  for (let i = 0; i < rawK.length; i++) {
    if (rawK[i] == null || i < period - 1 + smoothK - 1) {
      kLine.push(null);
    } else {
      let sum = 0, count = 0;
      for (let j = i - smoothK + 1; j <= i; j++) {
        if (rawK[j] != null) { sum += rawK[j]!; count++; }
      }
      kLine.push(count > 0 ? sum / count : null);
    }
  }

  // %D = SMA(3) of %K
  const dLine: (number | null)[] = [];
  for (let i = 0; i < kLine.length; i++) {
    if (kLine[i] == null || i < period - 1 + smoothK - 1 + 2) {
      dLine.push(null);
    } else {
      let sum = 0, count = 0;
      for (let j = i - 2; j <= i; j++) {
        if (kLine[j] != null) { sum += kLine[j]!; count++; }
      }
      dLine.push(count > 0 ? sum / count : null);
    }
  }

  return { k: kLine, d: dLine };
}

export interface PriceInput {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export function computeIndicators(prices: PriceInput[]): IndicatorBar[] {
  const closes = prices.map((p) => p.close);
  const highs = prices.map((p) => p.high);
  const lows = prices.map((p) => p.low);

  const sma20 = sma(closes, 20);
  const sma50 = sma(closes, 50);
  const rsi = computeRSI(closes);
  const macd = computeMACD(closes);
  const dc = computeDonchian(highs, lows);
  const stoch = computeStochastic(highs, lows, closes);

  return prices.map((p, i) => ({
    date: p.date,
    close: p.close,
    volume: p.volume,
    sma20: sma20[i],
    sma50: sma50[i],
    rsi: rsi[i],
    macdLine: macd.line[i],
    macdSignal: macd.signal[i],
    macdHist: macd.histogram[i],
    dcUpper: dc.upper[i],
    dcLower: dc.lower[i],
    dcMiddle: dc.middle[i],
    stochK: stoch.k[i],
    stochD: stoch.d[i],
  }));
}
