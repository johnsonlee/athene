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
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>{t('about.strategy1')}</li>
          <li>{t('about.strategy2')}</li>
          <li>{t('about.strategy3')}</li>
        </ol>
      </section>

      {/* Investment Principles */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">{t('about.principles')}</h2>
        <div className="space-y-4">
          {(['principle1', 'principle2', 'principle3'] as const).map((key, i) => (
            <div key={key} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700 dark:bg-cyan-500/15 dark:text-cyan-300">{i + 1}</span>
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">{t(`about.${key}.title` as any)}</h3>
                <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{t(`about.${key}.desc` as any)}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Strategy Framework */}
      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('about.framework')}</h2>
        <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">{t('about.frameworkDesc')}</p>
        <div className="rounded-lg bg-gray-50 p-3 font-mono text-sm text-gray-800 dark:bg-slate-800/50 dark:text-gray-200">
          Score = VM × EV × Timing / K
        </div>
        <div className="mt-4 space-y-3">
          {(['factorVM', 'factorEV', 'factorTiming'] as const).map((key) => (
            <div key={key} className="border-l-2 border-blue-300 pl-3 dark:border-cyan-600/50">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">{t(`about.${key}.title` as any)}</h3>
                <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600 dark:bg-cyan-500/10 dark:text-cyan-400">{t(`about.${key}.from` as any)}</span>
              </div>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{t(`about.${key}.desc` as any)}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 border-t border-gray-100 pt-3 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white">{t('about.whyMultiply' as any)}</span>
            <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600 dark:bg-cyan-500/10 dark:text-cyan-400">{t('about.whyMultiply.from' as any)}</span>
          </div>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{t('about.whyMultiply.desc' as any)}</p>
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
