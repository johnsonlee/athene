export function formatScore(score: number | null | undefined): string {
  if (score == null) return 'N/A';
  return score.toFixed(1);
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  return (value * 100).toFixed(1) + '%';
}

export function formatLargeNumber(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  if (Math.abs(value) >= 1e12) return (value / 1e12).toFixed(2) + 'T';
  if (Math.abs(value) >= 1e9) return (value / 1e9).toFixed(2) + 'B';
  if (Math.abs(value) >= 1e6) return (value / 1e6).toFixed(2) + 'M';
  if (Math.abs(value) >= 1e3) return (value / 1e3).toFixed(1) + 'K';
  return value.toFixed(2);
}

export function formatPrice(price: number | null | undefined): string {
  if (price == null) return 'N/A';
  return '$' + price.toFixed(2);
}

export function formatRatio(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  return value.toFixed(2);
}

export function tierBgClass(tier: string): string {
  switch (tier) {
    case 'strong_buy': return 'bg-emerald-600 text-white dark:bg-emerald-500/20 dark:text-emerald-300 dark:border dark:border-emerald-500/30';
    case 'buy': return 'bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300 dark:border dark:border-green-500/25';
    case 'hold': return 'bg-gray-200 text-gray-700 dark:bg-slate-500/15 dark:text-slate-300 dark:border dark:border-slate-500/25';
    case 'sell': return 'bg-orange-100 text-orange-800 dark:bg-orange-500/15 dark:text-orange-300 dark:border dark:border-orange-500/25';
    case 'strong_sell': return 'bg-red-600 text-white dark:bg-red-500/20 dark:text-red-300 dark:border dark:border-red-500/30';
    default: return 'bg-gray-200 dark:bg-gray-700';
  }
}
