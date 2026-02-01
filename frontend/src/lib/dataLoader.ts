const BASE_URL = import.meta.env.BASE_URL + 'data/';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(BASE_URL + path);
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return res.json();
}

export function loadMeta() {
  return fetchJson<import('../types').Meta>('meta.json');
}

export function loadRankings() {
  return fetchJson<import('../types').RankedStock[]>('rankings.json');
}

export function loadStockDetail(ticker: string) {
  return fetchJson<import('../types').StockDetail>(`stocks/${ticker}.json`);
}

export function loadIC() {
  return fetchJson<import('../types').ICData>('ic.json');
}
