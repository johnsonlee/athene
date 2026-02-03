import { Fragment } from 'react';
import { useI18n } from '../lib/i18n';
import { useIC } from '../hooks/useIC';
import type { ICData } from '../types';

function ICTable({ data, t }: { data: ICData; t: (key: any, params?: any) => string }) {
  const factorLabels: Record<string, string> = {
    composite_score: t('table.score'),
    earnings_visibility: t('detail.earningsVisibility'),
    valuation_margin: t('detail.valuationMargin'),
    catalyst_timeline: t('detail.catalystTimeline'),
    downside_control: t('detail.downsideControl'),
    // v7: sub-score factors
    value_score: t('factor.value'),
    quality_score: t('factor.quality'),
    growth_score: t('factor.growth'),
    safety_score: t('factor.safety'),
    trend_score: t('factor.trend'),
    momentum_score: t('factor.momentum'),
    volatility_score: t('factor.volatility'),
    volume_score: t('factor.volume'),
  };

  const hasData = Object.values(data.factors).some((horizons) =>
    Object.values(horizons).some((s) => s.count > 0)
  );

  if (!hasData) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">{t('about.icInsufficient')}</p>;
  }

  return (
    <div className="overflow-x-auto">
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
    </div>
  );
}

export function About() {
  const { t } = useI18n();
  const { data: icData } = useIC();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">{t('about.title')}</h1>

      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.methodology')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.methodologyDesc')}</p>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.multiFactorModel')}</h3>
        <div className="overflow-x-auto">
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
                <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.earningsVisibility')}</td>
                <td>30%</td>
                <td>{t('about.evComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.evSubWeights')}</span></td>
              </tr>
              <tr className="border-b dark:border-gray-700">
                <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.valuationMargin')}</td>
                <td>25%</td>
                <td>{t('about.vmComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.vmSubWeights')}</span></td>
              </tr>
              <tr className="border-b dark:border-gray-700">
                <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.catalystTimeline')}</td>
                <td>20%</td>
                <td>{t('about.ctComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.ctSubWeights')}</span></td>
              </tr>
              <tr>
                <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.downsideControl')}</td>
                <td>25%</td>
                <td>{t('about.dcComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.dcSubWeights')}</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.scoringTitle')}</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringAbsolute')}</p>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringComposite')}</p>
        <p className="mt-1 overflow-x-auto rounded bg-gray-100 px-3 py-2 font-mono text-xs text-gray-800 sm:text-sm dark:bg-slate-900/60 dark:text-cyan-200">{t('about.scoringFormula')}</p>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringSmoothing6')}</p>

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

      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.modelHistory')}</h2>
        <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">{t('about.modelHistoryDesc7')}</p>
        <div className="relative ml-3 border-l-2 border-gray-200 dark:border-cyan-500/20">
          {/* v1 */}
          <div className="relative mb-6 ml-6">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-gray-300 bg-white dark:border-gray-500 dark:bg-gray-800" />
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs font-bold text-gray-500 dark:text-gray-400">{t('about.historyV1Label')}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{t('about.historyV1Date')}</span>
            </div>
            <h4 className="font-medium text-gray-900 dark:text-white">{t('about.historyV1Title')}</h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.historyV1Desc')}</p>
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{t('about.historyV1Issue')}</p>
          </div>
          {/* v2 */}
          <div className="relative mb-6 ml-6">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-gray-300 bg-white dark:border-gray-500 dark:bg-gray-800" />
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs font-bold text-gray-500 dark:text-gray-400">{t('about.historyV2Label')}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{t('about.historyV2Date')}</span>
            </div>
            <h4 className="font-medium text-gray-900 dark:text-white">{t('about.historyV2Title')}</h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.historyV2Desc')}</p>
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{t('about.historyV2Issue')}</p>
          </div>
          {/* v3 */}
          <div className="relative mb-6 ml-6">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-gray-300 bg-white dark:border-gray-500 dark:bg-gray-800" />
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs font-bold text-gray-500 dark:text-gray-400">{t('about.historyV3Label')}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{t('about.historyV3Date')}</span>
            </div>
            <h4 className="font-medium text-gray-900 dark:text-white">{t('about.historyV3Title')}</h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.historyV3Desc')}</p>
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{t('about.historyV3Issue')}</p>
          </div>
          {/* v4 */}
          <div className="relative mb-6 ml-6">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-gray-300 bg-white dark:border-gray-500 dark:bg-gray-800" />
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs font-bold text-gray-500 dark:text-gray-400">{t('about.historyV4Label')}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{t('about.historyV4Date')}</span>
            </div>
            <h4 className="font-medium text-gray-900 dark:text-white">{t('about.historyV4Title')}</h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.historyV4Desc')}</p>
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{t('about.historyV4Issue')}</p>
          </div>
          {/* v5 */}
          <div className="relative mb-6 ml-6">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-gray-300 bg-white dark:border-gray-500 dark:bg-gray-800" />
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs font-bold text-gray-500 dark:text-gray-400">{t('about.historyV5Label')}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{t('about.historyV5Date')}</span>
            </div>
            <h4 className="font-medium text-gray-900 dark:text-white">{t('about.historyV5Title')}</h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.historyV5Desc')}</p>
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{t('about.historyV5Issue')}</p>
          </div>
          {/* v6 */}
          <div className="relative mb-6 ml-6">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-gray-300 bg-white dark:border-gray-500 dark:bg-gray-800" />
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs font-bold text-gray-500 dark:text-gray-400">{t('about.historyV6Label')}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{t('about.historyV6Date')}</span>
            </div>
            <h4 className="font-medium text-gray-900 dark:text-white">{t('about.historyV6Title')}</h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.historyV6Desc')}</p>
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{t('about.historyV6Issue')}</p>
          </div>
          {/* v7 (current) */}
          <div className="relative ml-6">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-blue-500 bg-blue-500 dark:border-cyan-400 dark:bg-cyan-400" />
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs font-bold text-blue-600 dark:text-cyan-400">{t('about.historyV7Label')}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{t('about.historyV7Date')}</span>
              <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-cyan-500/15 dark:text-cyan-300">{t('about.historyCurrent')}</span>
            </div>
            <h4 className="font-medium text-gray-900 dark:text-white">{t('about.historyV7Title')}</h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t('about.historyV7Desc')}</p>
          </div>
        </div>
      </section>

      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.dataSources')}</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>{t('about.dataPrice')}</li>
          <li>{t('about.dataNews')}</li>
          <li>{t('about.dataUniverse')}</li>
        </ul>
      </section>

      <section className="tech-card p-4 sm:p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.disclaimer')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.disclaimerText')}</p>
      </section>
    </div>
  );
}
