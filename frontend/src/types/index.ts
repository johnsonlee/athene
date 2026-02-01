export interface Meta {
  date: string;
  timestamp: string;
  version: string;
  ticker_count: number;
}

export interface UniverseStock {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
}

export interface RankedStock {
  ticker: string;
  name?: string;
  sector?: string;
  industry?: string;
  fundamental_score?: number | null;
  technical_score?: number | null;
  sentiment_score?: number | null;
  composite_score: number;
  rank: number;
  percentile: number;
  tier: TierKey;
  tier_label: string;
  tier_color: string;
  weight_fundamental?: number;
  weight_technical?: number;
  weight_sentiment?: number;
  // Sub-scores
  value_score?: number | null;
  quality_score?: number | null;
  growth_score?: number | null;
  safety_score?: number | null;
  trend_score?: number | null;
  momentum_score?: number | null;
  volatility_score?: number | null;
  volume_score?: number | null;
}

export type TierKey = 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';

export interface FundamentalData {
  ticker: string;
  pe?: number | null;
  forward_pe?: number | null;
  pb?: number | null;
  ps?: number | null;
  roe?: number | null;
  roa?: number | null;
  revenue_growth?: number | null;
  earnings_growth?: number | null;
  debt_to_equity?: number | null;
  fcf?: number | null;
  market_cap?: number | null;
  profit_margin?: number | null;
  operating_margin?: number | null;
  gross_margin?: number | null;
  dividend_yield?: number | null;
  beta?: number | null;
  current_price?: number | null;
  high_52w?: number | null;
  low_52w?: number | null;
  // Sub-scores (from scored pipeline)
  value_score?: number | null;
  quality_score?: number | null;
  growth_score?: number | null;
  safety_score?: number | null;
  fundamental_score?: number | null;
}

export interface TechnicalData {
  ticker: string;
  close?: number;
  sma_20?: number | null;
  sma_50?: number | null;
  sma_200?: number | null;
  rsi?: number | null;
  macd_line?: number | null;
  macd_histogram?: number | null;
  bb_position?: number | null;
  bb_upper?: number | null;
  bb_lower?: number | null;
  volume_ratio?: number | null;
  trend_alignment?: number | null;
  stoch_k?: number | null;
  stoch_d?: number | null;
  // Sub-scores (from scored pipeline)
  trend_score?: number | null;
  momentum_score?: number | null;
  volatility_score?: number | null;
  volume_score?: number | null;
  technical_score?: number | null;
}

export interface SentimentData {
  ticker: string;
  sentiment_compound: number;
  sentiment_pos: number;
  sentiment_neg: number;
  sentiment_neu: number;
  news_count: number;
  sentiment_score?: number | null;
}

export interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HeadlineItem {
  title: string;
  url: string;
  publisher: string;
}

export interface StockDetail {
  ticker: string;
  prices: PriceBar[];
  fundamental: FundamentalData | null;
  technical: TechnicalData | null;
  sentiment: SentimentData | null;
  ranking: RankedStock | null;
  headlines: HeadlineItem[];
}

export interface HistorySnapshot {
  composite_score: number;
  tier: TierKey;
  rank: number;
  percentile: number;
}

/** history.json: keyed by date, then by ticker */
export type DailyHistory = Record<string, Record<string, HistorySnapshot>>;

export interface FilterState {
  search: string;
  sectors: string[];
  tiers: TierKey[];
  minScore: number;
  maxScore: number;
}
