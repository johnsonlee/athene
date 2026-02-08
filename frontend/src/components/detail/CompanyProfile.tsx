import { useState } from 'react';
import { useI18n } from '../../lib/i18n';
import type { CompanyProfile as ProfileData, RankedStock } from '../../types';

interface Props {
  profile: ProfileData | null;
  ranking: RankedStock | null;
}

function formatEmployees(count: number | undefined): string {
  if (count == null) return 'N/A';
  if (count >= 1000) return (count / 1000).toFixed(1) + 'K';
  return String(count);
}

export function CompanyProfile({ profile, ranking }: Props) {
  const { t, tIndustry } = useI18n();
  const [showFullDesc, setShowFullDesc] = useState(false);

  if (!profile?.longBusinessSummary) return null;

  const desc = profile.longBusinessSummary;
  const isLongDesc = desc.length > 150;

  return (
    <div className="tech-card space-y-3 p-4">
      {/* Section heading with sector/industry */}
      <div className="flex items-center justify-between">
        <h2 className="tech-heading text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
          {t('profile.companyProfile')}
        </h2>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-gray-400 dark:text-gray-500">
          {ranking?.sector && (
            <span>{t(`sector.${ranking.sector}` as any) || ranking.sector}</span>
          )}
          {ranking?.sector && ranking?.industry && (
            <span>&middot;</span>
          )}
          {ranking?.industry && (
            <span>{tIndustry(ranking.industry)}</span>
          )}
        </div>
      </div>

      {/* Company description */}
      <div>
        <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-400">
          {isLongDesc && !showFullDesc ? desc.slice(0, 150) + '…' : desc}
        </p>
        {isLongDesc && (
          <button
            onClick={() => setShowFullDesc(!showFullDesc)}
            className="mt-1 text-[10px] text-blue-600 hover:underline dark:text-cyan-400"
          >
            {showFullDesc ? t('profile.showLess') : t('profile.showMore')}
          </button>
        )}
      </div>

      {/* Company info bar */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-gray-400 dark:text-gray-500">
        {profile.fullTimeEmployees != null && (
          <span>{t('profile.employees')}: {formatEmployees(profile.fullTimeEmployees)}</span>
        )}
        {profile.city && profile.country && (
          <span>{profile.city}, {profile.country}</span>
        )}
        {profile.website && (
          <a href={profile.website} target="_blank" rel="noopener noreferrer"
            className="text-blue-500 hover:underline dark:text-cyan-400 truncate max-w-[200px]">
            {profile.website.replace(/^https?:\/\/(www\.)?/, '')}
          </a>
        )}
      </div>
    </div>
  );
}
