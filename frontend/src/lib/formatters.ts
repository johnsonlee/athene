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
    case 'strong_buy': return 'bg-green-800 text-white';
    case 'buy': return 'bg-green-400 text-gray-900';
    case 'hold': return 'bg-gray-400 text-gray-900';
    case 'sell': return 'bg-orange-400 text-gray-900';
    case 'strong_sell': return 'bg-red-500 text-white';
    default: return 'bg-gray-300';
  }
}
