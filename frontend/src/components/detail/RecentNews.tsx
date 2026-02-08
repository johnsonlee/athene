import { useI18n } from '../../lib/i18n';
import type { HeadlineItem } from '../../types';

interface Props {
  headlines: HeadlineItem[];
}

const sentimentColor: Record<string, string> = {
  positive: 'text-green-600 dark:text-green-400',
  negative: 'text-red-600 dark:text-red-400',
  neutral: 'text-gray-400 dark:text-gray-500',
};

const sentimentDot: Record<string, string> = {
  positive: 'bg-green-500',
  negative: 'bg-red-500',
  neutral: 'bg-gray-400 dark:bg-gray-500',
};

export function RecentNews({ headlines }: Props) {
  const { t } = useI18n();

  if (headlines.length === 0) return null;

  return (
    <div className="tech-card space-y-2 p-4">
      <div className="flex items-center justify-between">
        <h2 className="tech-heading text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
          {t('detail.recentNews')}
        </h2>
        <span className="text-[10px] text-gray-400 dark:text-gray-500">
          {t('detail.articles', { count: headlines.length })}
        </span>
      </div>

      <ul className="space-y-1.5">
        {headlines.map((item, i) => (
          <li key={i} className="flex items-start gap-2">
            {item.sentiment && (
              <span className={`mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${sentimentDot[item.sentiment] ?? sentimentDot.neutral}`} />
            )}
            <div className="min-w-0 flex-1">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs leading-snug text-gray-800 hover:text-blue-600 dark:text-gray-300 dark:hover:text-cyan-400 line-clamp-2"
              >
                {item.title}
              </a>
              <div className="mt-0.5 flex items-center gap-2 text-[10px] text-gray-400 dark:text-gray-500">
                <span>{item.publisher}</span>
                {item.date && <span>{item.date}</span>}
                {item.sentiment && (
                  <span className={sentimentColor[item.sentiment] ?? ''}>
                    {t(`metric.${item.sentiment}` as any)}
                  </span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
