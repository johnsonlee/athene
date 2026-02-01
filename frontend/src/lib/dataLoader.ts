const BASE_URL = import.meta.env.BASE_URL + 'data/';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(BASE_URL + path);
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return res.json();
}

export function loadMeta() {
  return fetchJson<import('../types').Meta>('meta.json');
}

export function loadUniverse() {
  return fetchJson<import('../types').UniverseStock[]>('universe.json');
}

export function loadRankings() {
  return fetchJson<import('../types').RankedStock[]>('rankings.json');
}

export function loadFundamentals() {
  return fetchJson<import('../types').FundamentalData[]>('fundamentals.json');
}

export function loadTechnicals() {
  return fetchJson<import('../types').TechnicalData[]>('technicals.json');
}

export function loadSentiment() {
  return fetchJson<import('../types').SentimentData[]>('sentiment.json');
}

export function loadStockDetail(ticker: string) {
  return fetchJson<import('../types').StockDetail>(`stocks/${ticker}.json`);
}
