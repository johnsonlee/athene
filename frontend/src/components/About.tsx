import { useI18n } from '../lib/i18n';

export function About() {
  const { t } = useI18n();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">{t('about.title')}</h1>

      {/* What is Athene */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.whatIs')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.whatIsDesc')}</p>
      </section>

      {/* Strategy */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.strategy')}</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>{t('about.strategy1')}</li>
          <li>{t('about.strategy2')}</li>
          <li>{t('about.strategy3')}</li>
        </ol>
      </section>

      {/* Version History */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">{t('about.versionHistory')}</h2>
        <div className="relative ml-3 border-l-2 border-gray-200 dark:border-gray-700">
          {([
            { key: 'v19', status: 'current' as const },
            { key: 'v18', status: null },
            { key: 'v17', status: null },
            { key: 'v16', status: null },
            { key: 'v15', status: null },
            { key: 'v14', status: null },
            { key: 'v13', status: null },
            { key: 'v12', status: null },
            { key: 'v11', status: null },
            { key: 'v10', status: null },
            { key: 'v9', status: null },
            { key: 'v8', status: null },
            { key: 'v7', status: null },
            { key: 'v6', status: null },
            { key: 'v5', status: null },
            { key: 'v4', status: null },
            { key: 'v3', status: null },
            { key: 'v2', status: null },
            { key: 'v1', status: 'deprecated' as const },
          ]).map(({ key, status }, i, arr) => {
            const issuesKey = `about.${key}.issues` as any;
            const issues = t(issuesKey);
            const hasIssues = issues !== issuesKey;
            const isLast = i === arr.length - 1;
            return (
              <div key={key} className={`relative ${isLast ? '' : 'mb-6'} ml-6`}>
                <span className={`absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 ${
                  status === 'current'
                    ? 'border-green-500 bg-green-500 dark:border-green-400 dark:bg-green-400'
                    : status === 'deprecated'
                      ? 'border-gray-300 bg-gray-300 dark:border-gray-600 dark:bg-gray-600'
                      : 'border-gray-300 bg-white dark:border-gray-500 dark:bg-gray-800'
                }`} />
                <div className="flex items-center gap-2">
                  <h3 className={`text-sm font-medium ${
                    status === 'deprecated'
                      ? 'text-gray-400 line-through dark:text-gray-600'
                      : 'text-gray-900 dark:text-white'
                  }`}>
                    {t(`about.${key}.title` as any)}
                  </h3>
                  {status && (
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                      status === 'current'
                        ? 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                    }`}>
                      {t(`about.${status}` as any)}
                    </span>
                  )}
                </div>
                <p className={`mt-0.5 text-xs ${
                  status === 'deprecated'
                    ? 'text-gray-400 dark:text-gray-600'
                    : 'text-gray-500 dark:text-gray-400'
                }`}>
                  {t(`about.${key}.desc` as any)}
                </p>
                {hasIssues && (
                  <p className="mt-1 text-xs text-amber-600 dark:text-amber-400/80">
                    {issues}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Data Sources */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.dataSources')}</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>{t('about.dataPrice')}</li>
          <li>{t('about.dataNews')}</li>
          <li>{t('about.dataUniverse')}</li>
          <li>{t('about.dataSectorETF')}</li>
          <li>{t('about.dataCapitalFlowETF')}</li>
        </ul>
      </section>

      {/* Open Source */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.openSource')}</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>
            <a href="https://github.com/tradingview/lightweight-charts" target="_blank" rel="noopener noreferrer"
              className="text-blue-600 hover:underline dark:text-cyan-400">Lightweight Charts</a>
            {' '}&mdash; {t('about.lightweightChartsDesc')}
          </li>
        </ul>
      </section>

      {/* Disclaimer */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.disclaimer')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.disclaimerText')}</p>
      </section>
    </div>
  );
}
