const BASE_URL = import.meta.env.BASE_URL + 'data/';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(BASE_URL + path);
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return res.json();
}

/** Map variant sector names (yfinance) to canonical GICS names */
const SECTOR_CANONICAL: Record<string, string> = {
  'Consumer Cyclical': 'Consumer Discretionary',
  'Consumer Defensive': 'Consumer Staples',
  'Healthcare': 'Health Care',
  'Technology': 'Information Technology',
};

export function normalizeSector(sector: string): string {
  return SECTOR_CANONICAL[sector] ?? sector;
}

export function loadMeta() {
  return fetchJson<import('../types').Meta>('meta.json');
}

export async function loadRankings() {
  const data = await fetchJson<import('../types').RankedStock[]>('rankings.json');
  return data.map((stock) => ({
    ...stock,
    sector: stock.sector ? normalizeSector(stock.sector) : stock.sector,
  }));
}

export function loadStockDetail(ticker: string) {
  return fetchJson<import('../types').StockDetail>(`stocks/${ticker}.json`);
}

export function loadIC() {
  return fetchJson<import('../types').ICData>('ic.json');
}

export function loadTrends() {
  return fetchJson<import('../types').TrendsData>('trends.json');
}

export function loadTrendHistory() {
  return fetchJson<import('../types').TrendHistory>('trend_history.json');
}
