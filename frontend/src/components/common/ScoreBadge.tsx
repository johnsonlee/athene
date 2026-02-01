import { tierBgClass } from '../../lib/formatters';

interface ScoreBadgeProps {
  tier: string;
  label: string;
}

export function ScoreBadge({ tier, label }: ScoreBadgeProps) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${tierBgClass(tier)}`}>
      {label}
    </span>
  );
}
