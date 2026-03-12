import { tierBgClass } from '../../lib/formatters';

const TIER_RANK: Record<string, number> = {
  strong_buy: 0, buy: 1, hold: 2, sell: 3, strong_sell: 4,
};

interface ScoreBadgeProps {
  tier: string;
  tierRaw?: string;
  label: string;
}

export function ScoreBadge({ tier, tierRaw, label }: ScoreBadgeProps) {
  // Show directional arrow when hysteresis is holding back a tier change
  let arrow = '';
  if (tierRaw && tierRaw !== tier) {
    const rawRank = TIER_RANK[tierRaw] ?? 2;
    const curRank = TIER_RANK[tier] ?? 2;
    arrow = rawRank < curRank ? ' \u2191' : ' \u2193';  // ↑ upgrading, ↓ downgrading
  }

  return (
    <span className={`tech-badge inline-block rounded px-2 py-0.5 text-xs font-semibold ${tierBgClass(tier)}`}>
      {label}{arrow}
    </span>
  );
}
