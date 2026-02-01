import { Fragment } from 'react';
import { useI18n } from '../lib/i18n';
import { useIC } from '../hooks/useIC';
import type { ICData } from '../types';

function ICTable({ data, t }: { data: ICData; t: (key: any, params?: any) => string }) {
  const factorLabels: Record<string, string> = {
    composite_score: t('table.score'),
    fundamental_score: t('detail.fundamentals'),
    technical_score: t('detail.technical'),
    sentiment_score: t('detail.sentiment'),
  };

  const hasData = Object.values(data.factors).some((horizons) =>
    Object.values(horizons).some((s) => s.count > 0)
  );

  if (!hasData) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">{t('about.icInsufficient')}</p>;
  }

  return (
    <table className="mt-2 w-full text-sm">
      <thead>
        <tr className="border-b text-left dark:border-gray-700">
          <th className="py-1 text-gray-900 dark:text-white">{t('about.icFactor')}</th>
          {data.horizons.map((h) => (
            <th key={h} colSpan={3} className="py-1 text-center text-gray-900 dark:text-white">
              {t('about.icHorizon', { days: h })}
            </th>
          ))}
        </tr>
        <tr className="border-b text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
          <th />
          {data.horizons.map((h) => (
            <Fragment key={h}>
              <th className="py-1 text-center">{t('about.icMeanIC')}</th>
              <th className="py-1 text-center">{t('about.icIR')}</th>
              <th className="py-1 text-center">{t('about.icHitRate')}</th>
            </Fragment>
          ))}
        </tr>
      </thead>
      <tbody className="text-gray-600 dark:text-gray-400">
        {Object.entries(data.factors).map(([factor, horizons]) => (
          <tr key={factor} className="border-b dark:border-gray-700">
            <td className="py-1 font-medium text-gray-800 dark:text-gray-200">
              {factorLabels[factor] || factor}
            </td>
            {data.horizons.map((h) => {
              const s = horizons[String(h)];
              const na = t('about.icNA');
              return (
                <Fragment key={h}>
                  <td className="py-1 text-center font-mono">
                    {s?.mean != null ? s.mean.toFixed(3) : na}
                  </td>
                  <td className="py-1 text-center font-mono">
                    {s?.ir != null ? s.ir.toFixed(2) : na}
                  </td>
                  <td className="py-1 text-center font-mono">
                    {s?.hit_rate != null ? `${(s.hit_rate * 100).toFixed(0)}%` : na}
                  </td>
                </Fragment>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function About() {
  const { t } = useI18n();
  const { data: icData } = useIC();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('about.title')}</h1>

      <section className="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.methodology')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.methodologyDesc')}</p>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.multiFactorModel')}</h3>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b text-left dark:border-gray-700">
              <th className="py-1 text-gray-900 dark:text-white">{t('about.factor')}</th>
              <th className="py-1 text-gray-900 dark:text-white">{t('about.weight')}</th>
              <th className="py-1 text-gray-900 dark:text-white">{t('about.components')}</th>
            </tr>
          </thead>
          <tbody className="text-gray-600 dark:text-gray-400">
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.fundamentals')}</td>
              <td>50%</td>
              <td>{t('about.fundComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.fundSubWeights')}</span></td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.technical')}</td>
              <td>30%</td>
              <td>{t('about.techComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.techSubWeights')}</span></td>
            </tr>
            <tr>
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.sentiment')}</td>
              <td>20%</td>
              <td>{t('about.sentComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.sentSubWeights')}</span></td>
            </tr>
          </tbody>
        </table>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.scoringTitle')}</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringAbsolute')}</p>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringComposite')}</p>
        <p className="mt-1 rounded bg-gray-100 px-3 py-2 font-mono text-sm text-gray-800 dark:bg-gray-900 dark:text-gray-200">{t('about.scoringFormula')}</p>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringSmoothing')}</p>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.ratingTiers')}</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.ratingTiersDesc')}</p>
        <table className="mt-2 w-full text-sm">
          <tbody className="text-gray-600 dark:text-gray-400">
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.strong_buy')}</td>
              <td>{t('about.tierStrongBuy')}</td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.buy')}</td>
              <td>{t('about.tierBuy')}</td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.hold')}</td>
              <td>{t('about.tierHold')}</td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.sell')}</td>
              <td>{t('about.tierSell')}</td>
            </tr>
            <tr>
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.strong_sell')}</td>
              <td>{t('about.tierStrongSell')}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t('about.hysteresis')}</p>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.icTitle')}</h3>
        <p className="mt-2 mb-3 text-sm text-gray-600 dark:text-gray-400">{t('about.icDesc')}</p>
        {icData ? (
          <ICTable data={icData} t={t} />
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('about.icInsufficient')}</p>
        )}
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.dataSources')}</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>{t('about.dataPrice')}</li>
          <li>{t('about.dataNews')}</li>
          <li>{t('about.dataUniverse')}</li>
        </ul>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.disclaimer')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.disclaimerText')}</p>
      </section>
    </div>
  );
}
