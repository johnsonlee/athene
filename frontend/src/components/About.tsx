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

      {/* Features */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('about.features')}</h2>
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-gray-900 dark:text-white">{t('about.featureTrend')}</h3>
              <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-cyan-500/15 dark:text-cyan-300">{t('about.statusPlanned')}</span>
            </div>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.featureTrendDesc')}</p>
          </div>
          <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-gray-900 dark:text-white">{t('about.featureLeader')}</h3>
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">{t('about.statusPlanned')}</span>
            </div>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.featureLeaderDesc')}</p>
          </div>
          <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-gray-900 dark:text-white">{t('about.featureAlert')}</h3>
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">{t('about.statusPlanned')}</span>
            </div>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.featureAlertDesc')}</p>
          </div>
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
