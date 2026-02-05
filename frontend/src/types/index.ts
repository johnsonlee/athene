export interface MacroRegime {
  regime: string;
  regime_score: number;
  vix: number | null;
  sp500_close: number | null;
  sp500_sma200: number | null;
  sp500_vs_sma200_pct: number | null;
  tnx_yield: number | null;
  irx_yield: number | null;
  yield_curve_spread: number | null;
  weights: Record<string, number>;
}

export interface Meta {
  date: string;
  timestamp: string;
  version: string;
  ticker_count: number;
  macro?: MacroRegime;
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
  market_cap?: number | null;
  fundamental_score?: number | null;
  technical_score?: number | null;
  sentiment_score?: number | null;
  composite_score: number;
  rank: number;
  percentile: number;
  tier: TierKey;
  tier_label: string;
  tier_color: string;
  // Qualitative dimensions (v3)
  earnings_visibility?: number | null;
  valuation_margin?: number | null;
  catalyst_timeline?: number | null;
  downside_control?: number | null;
  weight_earnings_visibility?: number;
  weight_valuation_margin?: number;
  weight_catalyst_timeline?: number;
  weight_downside_control?: number;
  // Legacy factor weights
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
  // v7: data quality
  data_completeness?: number | null;
  data_quality_penalty?: number | null;
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
  date?: string;
  sentiment?: 'positive' | 'negative' | 'neutral';
}

export interface CompanyProfile {
  longBusinessSummary?: string;
  fullTimeEmployees?: number;
  website?: string;
  city?: string;
  country?: string;
}

export interface StockDetail {
  ticker: string;
  profile: CompanyProfile | null;
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

export interface ICHorizonStats {
  dates: string[];
  ic: number[];
  count: number;
  mean: number | null;
  std: number | null;
  ir: number | null;
  hit_rate: number | null;
}

export interface ICData {
  horizons: number[];
  factors: Record<string, Record<string, ICHorizonStats>>;
  computed_at: string;
  num_dates: number;
}

export type TrendState = 'strong_uptrend' | 'uptrend' | 'neutral' | 'downtrend' | 'strong_downtrend';

export interface TrendSignal {
  score: number;
  [key: string]: unknown;
}

export interface SectorTrend {
  sector: string;
  etf: string;
  trend_strength: number;
  trend_state: TrendState;
  primary_signal: string;
  signals: {
    relative_strength: TrendSignal;
    breadth: TrendSignal;
    analyst_revisions: TrendSignal;
    momentum: TrendSignal;
    volume: TrendSignal;
  };
  etf_close: number;
  stock_count: number;
}

export interface TrendsData {
  date: string;
  regime: Record<string, unknown>;
  sectors: SectorTrend[];
}

export interface TrendHistoryEntry {
  trend_strength: number;
  trend_state: TrendState;
  rs_score?: number | null;
  momentum_score?: number | null;
}

/** trend_history.json: keyed by date, then by sector name */
export type TrendHistory = Record<string, Record<string, TrendHistoryEntry>>;

// Capital Flow types
export interface CapitalFlowNode {
  label_zh: string;
  label_en: string;
  value: string;
  net: number;
  type: 'risk' | 'safe';
}

export interface CapitalFlowArrow {
  from: string;
  to: string;
  amount: number;
  label: string;
}

export interface CapitalFlowPhase {
  id: string;
  date: string;
  phase: 'normal' | 'deleverage' | 'outflow' | 'bottom' | 'riskon';
  label_zh: string;
  label_en: string;
  description_zh: string;
  description_en: string;
  nodes: Record<string, CapitalFlowNode>;
  flows: CapitalFlowArrow[];
  risk_net: number;
  safe_net: number;
  untracked?: number;
}

export interface CapitalFlowWindow {
  current_phase_idx: number;
  phases: CapitalFlowPhase[];
}

export interface CapitalFlowData {
  date: string;
  default_window: string;
  signal_method: string;
  windows: Record<string, CapitalFlowWindow>;
}

export interface FilterState {
  search: string;
  sectors: string[];
  tiers: TierKey[];
  minScore: number;
  maxScore: number;
}
