import { useMeta } from '../../hooks/useMeta';
import { useI18n } from '../../lib/i18n';

export function Footer() {
  const { data: meta } = useMeta();
  const { t } = useI18n();

  return (
    <footer className="tech-bar border-t border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="mx-auto max-w-7xl px-4 py-4 text-center text-xs text-gray-500 dark:text-gray-400">
        <p>
          Athene Stock Screener &middot; {t('footer.dataFrom')}
          {meta && (
            <>
              {' '}&middot; {t('footer.lastUpdated', { date: meta.timestamp?.slice(0, 16).replace('T', ' ') || meta.date })}
              {' '}&middot; {t('footer.stockCount', { count: meta.ticker_count })}
            </>
          )}
        </p>
        <p className="mt-1">{t('footer.disclaimer')}</p>
      </div>
    </footer>
  );
}
