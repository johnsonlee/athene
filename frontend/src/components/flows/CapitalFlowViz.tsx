import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useCapitalFlows } from '../../hooks/useCapitalFlows';
import { useI18n } from '../../lib/i18n';
import { LoadingSpinner } from '../common/LoadingSpinner';
import type { CapitalFlowPhase, CapitalFlowNode } from '../../types';

// ─── SVG Layout Constants ───
const SVG_W = 820;
const SVG_H = 500;
const NODE_W = 100;
const NODE_H = 52;

// ─── Color helpers ───
function getNodeColor(net: number) {
  if (net > 5) return { fill: '#064e3b', stroke: '#10b981', text: '#6ee7b7', glow: 'rgba(16,185,129,0.3)' };
  if (net > 0) return { fill: '#14532d', stroke: '#22c55e', text: '#86efac', glow: 'rgba(34,197,94,0.2)' };
  if (net > -5) return { fill: '#451a03', stroke: '#f59e0b', text: '#fcd34d', glow: 'rgba(245,158,11,0.15)' };
  return { fill: '#450a0a', stroke: '#ef4444', text: '#fca5a5', glow: 'rgba(239,68,68,0.3)' };
}

function getPhaseColor(phase: string) {
  switch (phase) {
    case 'deleverage': return '#ef4444';
    case 'outflow': return '#f97316';
    case 'bottom': return '#f59e0b';
    case 'riskon': return '#22c55e';
    default: return '#6b7280';
  }
}

// ─── Compute dynamic node positions from data ───
function computeNodePositions(nodes: Record<string, CapitalFlowNode>) {
  const risk = Object.entries(nodes).filter(([, n]) => n.type === 'risk');
  const safe = Object.entries(nodes).filter(([, n]) => n.type === 'safe');

  const positions: Record<string, { x: number; y: number }> = {};
  const leftX = 80;
  const rightX = 680;

  const distribute = (items: [string, CapitalFlowNode][], x: number) => {
    const count = items.length;
    if (count === 0) return;
    const startY = 55;
    // Available height from first node top to last node bottom
    const availableH = SVG_H - startY - NODE_H - 15;
    const spacing = count > 1 ? availableH / (count - 1) : 0;
    const effectiveStartY = count > 1 ? startY : SVG_H / 2 - NODE_H / 2;
    items.forEach(([id], i) => {
      positions[id] = { x, y: effectiveStartY + i * spacing };
    });
  };

  distribute(risk, leftX);
  distribute(safe, rightX);
  return positions;
}

// ─── Flow Path Component ───
function FlowPath({ from, to, amount, maxAmount, label, animDelay, positions }: {
  from: string; to: string; amount: number; maxAmount: number;
  label: string; animDelay: number;
  positions: Record<string, { x: number; y: number }>;
}) {
  const fp = positions[from];
  const tp = positions[to];
  if (!fp || !tp) return null;

  const sx = fp.x + NODE_W;
  const sy = fp.y + NODE_H / 2;
  const ex = tp.x;
  const ey = tp.y + NODE_H / 2;

  const goesLeft = sx > ex;
  const startX = goesLeft ? fp.x : sx;
  const endX = goesLeft ? tp.x + NODE_W : ex;

  const midX = (startX + endX) / 2;
  const path = `M ${startX} ${sy} C ${midX} ${sy}, ${midX} ${ey}, ${endX} ${ey}`;

  const thickness = Math.max(1.5, Math.min(8, (amount / maxAmount) * 8));
  const opacity = Math.max(0.3, Math.min(0.85, (amount / maxAmount) * 0.85));

  const labelX = midX;
  const labelY = (sy + ey) / 2 - 8;

  const pathId = `flowpath-${from}-${to}`;

  return (
    <g>
      <path d={path} fill="none" stroke="rgba(99,102,241,0.08)" strokeWidth={thickness + 4} />
      <path
        d={path} fill="none" stroke="#6366f1" strokeWidth={thickness}
        opacity={opacity} strokeLinecap="round"
        style={{
          strokeDasharray: '1200', strokeDashoffset: '1200',
          animation: `flowDraw 1s ease ${animDelay}s forwards`,
        }}
      />
      <circle r={Math.max(2, thickness / 2)} fill="#a5b4fc" opacity={0.9}>
        <animateMotion dur="3s" repeatCount="indefinite" begin={`${animDelay}s`}>
          <mpath href={`#${pathId}`} />
        </animateMotion>
      </circle>
      <path id={pathId} d={path} fill="none" stroke="none" />
      <rect x={labelX - 22} y={labelY - 8} width={44} height={16} rx={4}
        fill="rgba(15,15,25,0.85)" stroke="rgba(99,102,241,0.2)" strokeWidth={0.5} />
      <text x={labelX} y={labelY + 3} textAnchor="middle" fill="#a5b4fc"
        fontSize="8" fontWeight="500" style={{ fontFamily: 'monospace' }}>
        {label}
      </text>
    </g>
  );
}

// ─── Node Box Component ───
function NodeBox({ data, pos, locale }: {
  data: CapitalFlowNode;
  pos: { x: number; y: number };
  locale: string;
}) {
  const colors = getNodeColor(data.net);
  const label = locale === 'zh' ? data.label_zh : data.label_en;
  return (
    <g>
      <rect
        x={pos.x} y={pos.y} width={NODE_W} height={NODE_H} rx={8}
        fill={colors.fill} stroke={colors.stroke} strokeWidth={1.2}
        filter={`drop-shadow(0 0 6px ${colors.glow})`}
      />
      <text x={pos.x + NODE_W / 2} y={pos.y + 18} textAnchor="middle"
        fill="#d1d5db" fontSize="11" fontWeight="600">
        {label}
      </text>
      <text x={pos.x + NODE_W / 2} y={pos.y + 36} textAnchor="middle"
        fill={colors.text} fontSize="12" fontWeight="700"
        style={{ fontFamily: 'monospace' }}>
        {data.value}
      </text>
    </g>
  );
}

// ─── Summary Bar Component ───
function SummaryBar({ phase, t }: { phase: CapitalFlowPhase; t: (key: any, p?: any) => string }) {
  const riskNet = phase.risk_net;
  const safeNet = phase.safe_net;
  const isRiskOn = riskNet > 0;
  const untracked = phase.untracked ?? 0;
  const hasUntracked = Math.abs(untracked) > 1;

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
      <div className="tech-card rounded-lg p-3">
        <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-500"
          style={{ fontFamily: 'monospace' }}>
          {t('flows.riskNet')}
        </div>
        <div className={`mt-0.5 text-lg font-bold ${riskNet > 0 ? 'text-green-500' : 'text-red-500'}`}
          style={{ fontFamily: 'monospace' }}>
          {riskNet > 0 ? '+' : ''}{riskNet.toFixed(1)}B
        </div>
      </div>
      <div className="tech-card rounded-lg p-3">
        <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-500"
          style={{ fontFamily: 'monospace' }}>
          {t('flows.safeNet')}
        </div>
        <div className={`mt-0.5 text-lg font-bold ${safeNet > 0 ? 'text-green-500' : 'text-red-500'}`}
          style={{ fontFamily: 'monospace' }}>
          {safeNet > 0 ? '+' : ''}{safeNet.toFixed(1)}B
        </div>
      </div>
      <div className={`rounded-lg border p-3 ${
        isRiskOn
          ? 'border-green-500/20 bg-green-500/5'
          : 'border-red-500/20 bg-red-500/5'
      }`}>
        <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-500"
          style={{ fontFamily: 'monospace' }}>
          {t('flows.marketState')}
        </div>
        <div className={`mt-0.5 text-base font-bold ${isRiskOn ? 'text-green-500' : 'text-red-500'}`}>
          {isRiskOn ? t('flows.riskOn') : t('flows.riskOff')}
        </div>
      </div>
      <div className={`rounded-lg border p-3 ${
        hasUntracked
          ? 'border-orange-500/20 bg-orange-500/5'
          : 'tech-card'
      }`}>
        <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-500"
          style={{ fontFamily: 'monospace' }}>
          {hasUntracked ? t('flows.untracked') : t('flows.totalVolume')}
        </div>
        <div className={`mt-0.5 text-lg font-bold ${hasUntracked ? 'text-orange-400' : 'text-indigo-400'}`}
          style={{ fontFamily: 'monospace' }}>
          ${Math.round(hasUntracked ? untracked : Math.abs(riskNet) + Math.abs(safeNet))}B
        </div>
      </div>
    </div>
  );
}

// ─── Timeline Component ───
function Timeline({ phases, activeIdx, onSelect, locale }: {
  phases: CapitalFlowPhase[];
  activeIdx: number;
  onSelect: (idx: number) => void;
  locale: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);
  const compact = phases.length > 12;

  // Auto-scroll to active phase
  useEffect(() => {
    if (activeRef.current && scrollRef.current) {
      const container = scrollRef.current;
      const el = activeRef.current;
      const left = el.offsetLeft - container.offsetWidth / 2 + el.offsetWidth / 2;
      container.scrollTo({ left: Math.max(0, left), behavior: 'smooth' });
    }
  }, [activeIdx]);

  // In compact mode, show date labels only on active, first, last, and every ~8th phase
  const showDateLabel = (i: number) => {
    if (!compact) return true;
    if (i === activeIdx || i === 0 || i === phases.length - 1) return true;
    const step = Math.max(4, Math.round(phases.length / 8));
    return i % step === 0;
  };

  return (
    <div
      ref={scrollRef}
      className="mb-4 flex items-center overflow-x-auto scrollbar-thin"
      style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.1) transparent' }}
    >
      {phases.map((p, i) => {
        const active = i === activeIdx;
        const past = i < activeIdx;
        const color = getPhaseColor(p.phase);

        return (
          <div key={p.id} className="flex items-center" style={{ flexShrink: 0 }}
            ref={active ? activeRef : undefined}>
            <button
              onClick={() => onSelect(i)}
              className="flex cursor-pointer flex-col items-center gap-0.5 border-0 bg-transparent"
              style={{ padding: compact ? '4px 2px' : '6px', minWidth: compact ? 28 : undefined }}
            >
              <div
                className="rounded-full transition-all duration-300"
                style={{
                  width: active ? 14 : compact ? 8 : 10,
                  height: active ? 14 : compact ? 8 : 10,
                  background: active ? color : past ? color + '88' : 'rgba(255,255,255,0.1)',
                  border: `2px solid ${active ? color : past ? color + '44' : 'rgba(255,255,255,0.08)'}`,
                  boxShadow: active ? `0 0 12px ${color}55` : 'none',
                }}
              />
              {showDateLabel(i) && (
                <span className={`text-[10px] ${active ? 'text-gray-200 font-semibold' : 'text-gray-600 font-normal'}`}
                  style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                  {p.date.slice(5)}
                </span>
              )}
              {(!compact || active) && (
                <span className={`text-[11px] font-semibold ${active ? '' : 'text-gray-500'}`}
                  style={{ color: active ? color : undefined, whiteSpace: 'nowrap' }}>
                  {locale === 'zh' ? p.label_zh : p.label_en}
                </span>
              )}
            </button>
            {i < phases.length - 1 && (
              <div
                style={{
                  width: compact ? 12 : 20,
                  height: 2,
                  flexShrink: 0,
                  marginBottom: compact && !active ? 0 : 28,
                  background: past
                    ? `linear-gradient(to right, ${color}66, ${color}22)`
                    : 'rgba(255,255,255,0.06)',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Column Labels ───
function ColumnLabels({ t, positions, nodes }: {
  t: (key: any) => string;
  positions: Record<string, { x: number; y: number }>;
  nodes: Record<string, CapitalFlowNode>;
}) {
  const risk = Object.entries(nodes).filter(([, n]) => n.type === 'risk');
  const safe = Object.entries(nodes).filter(([, n]) => n.type === 'safe');
  const riskX = risk.length > 0 ? positions[risk[0][0]]?.x ?? 80 : 80;
  const safeX = safe.length > 0 ? positions[safe[0][0]]?.x ?? 680 : 680;

  return (
    <>
      <text x={riskX + NODE_W / 2} y={28} textAnchor="middle" fill="#4b5563"
        fontSize="10" fontWeight="500" letterSpacing="0.1em"
        style={{ fontFamily: 'monospace' }}>
        {t('flows.riskAssets')}
      </text>
      <text x={safeX + NODE_W / 2} y={28} textAnchor="middle" fill="#4b5563"
        fontSize="10" fontWeight="500" letterSpacing="0.1em"
        style={{ fontFamily: 'monospace' }}>
        {t('flows.safeAssets')}
      </text>
      <line x1={SVG_W / 2} y1={35} x2={SVG_W / 2} y2={SVG_H - 10}
        stroke="rgba(255,255,255,0.04)" strokeWidth={1} strokeDasharray="4 4" />
    </>
  );
}

// ─── Interval Selector ───
function IntervalSelector({ options, active, onChange, label }: {
  options: string[];
  active: string;
  onChange: (key: string) => void;
  label: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-500"
        style={{ fontFamily: 'monospace' }}>
        {label}
      </span>
      <div className="flex rounded-md border border-gray-200 dark:border-gray-700">
        {options.map((key) => (
          <button
            key={key}
            onClick={() => onChange(key)}
            className={`px-2.5 py-1 text-xs font-medium transition-colors ${
              active === key
                ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            } ${key === options[0] ? 'rounded-l-md' : ''} ${key === options[options.length - 1] ? 'rounded-r-md' : ''}`}
            style={{ fontFamily: 'monospace' }}
          >
            {key}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Range filter helpers ───
const RANGE_OPTIONS = ['3M', '6M', '1Y', 'All'] as const;
type RangeKey = typeof RANGE_OPTIONS[number];

const RANGE_DAYS: Record<RangeKey, number> = {
  '3M': 90,
  '6M': 180,
  '1Y': 365,
  'All': Infinity,
};

function filterPhasesByRange(phases: CapitalFlowPhase[], range: RangeKey): CapitalFlowPhase[] {
  if (range === 'All' || !phases.length) return phases;
  const days = RANGE_DAYS[range];
  const latestDate = new Date(phases[phases.length - 1].date);
  const cutoff = new Date(latestDate);
  cutoff.setDate(cutoff.getDate() - days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  return phases.filter(p => p.date >= cutoffStr);
}

// ─── Main Component ───
export function CapitalFlowViz() {
  const { data, loading, error } = useCapitalFlows();
  const { t, locale } = useI18n();
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [animKey, setAnimKey] = useState(0);
  const [interval, setInterval] = useState<string | null>(null);
  const [range, setRange] = useState<RangeKey>('1Y');

  // Determine available windows and active window
  const windowKeys = useMemo(() => {
    if (!data?.windows) return [];
    return Object.keys(data.windows);
  }, [data]);

  const activeInterval = interval ?? data?.default_window ?? windowKeys[0] ?? '1W';

  const windowData = data?.windows?.[activeInterval];
  const allPhases = windowData?.phases ?? [];

  // Filter phases by selected time range
  const phases = useMemo(() => filterPhasesByRange(allPhases, range), [allPhases, range]);

  const handleIntervalChange = useCallback((key: string) => {
    setInterval(key);
    setActiveIdx(null);
    setAnimKey(k => k + 1);
  }, []);

  const handleRangeChange = useCallback((key: string) => {
    setRange(key as RangeKey);
    setActiveIdx(null);
    setAnimKey(k => k + 1);
  }, []);

  const handleSelect = useCallback((idx: number) => {
    setActiveIdx(idx);
    setAnimKey(k => k + 1);
  }, []);

  // Set initial active index once data loads (default to latest = last phase)
  const resolvedIdx = activeIdx ?? (phases.length ? phases.length - 1 : 0);

  const phase = phases[resolvedIdx];

  const positions = useMemo(() => {
    if (!phase) return {};
    return computeNodePositions(phase.nodes);
  }, [phase]);

  const maxAmount = useMemo(() => {
    if (!phase) return 1;
    return Math.max(1, ...phase.flows.map(f => f.amount));
  }, [phase]);

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return (
    <div className="py-12 text-center text-gray-500 dark:text-gray-400">
      <p className="mb-2 text-lg font-semibold">{t('flows.noData')}</p>
      <p className="text-sm">{t('flows.noDataHint')}</p>
    </div>
  );
  if (!data || !phases.length || !phase) return (
    <div className="py-12 text-center text-gray-500 dark:text-gray-400">
      <p>{t('flows.noData')}</p>
    </div>
  );

  const description = locale === 'zh' ? phase.description_zh : phase.description_en;

  return (
    <div className="space-y-4">
      <style>{`@keyframes flowDraw { to { stroke-dashoffset: 0; } }`}</style>

      {/* Header + Selectors */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-baseline gap-3">
            <h1 className="tech-heading text-lg font-bold text-gray-900 dark:text-white">
              {t('flows.title')}
            </h1>
            <span className="text-xs text-gray-500 dark:text-gray-500" style={{ fontFamily: 'monospace' }}>
              {t('flows.subtitle')}
            </span>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
            {description}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <IntervalSelector
            options={[...RANGE_OPTIONS]}
            active={range}
            onChange={handleRangeChange}
            label={t('flows.range')}
          />
          {windowKeys.length > 1 && (
            <IntervalSelector
              options={windowKeys}
              active={activeInterval}
              onChange={handleIntervalChange}
              label={t('flows.interval')}
            />
          )}
        </div>
      </div>

      {/* Timeline */}
      <Timeline phases={phases} activeIdx={resolvedIdx} onSelect={handleSelect} locale={locale} />

      {/* Summary stats */}
      <SummaryBar phase={phase} t={t} />

      {/* Flow Diagram */}
      <div className="tech-card overflow-hidden rounded-xl p-2">
        <svg key={animKey} width="100%" viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="block">
          <ColumnLabels t={t} positions={positions} nodes={phase.nodes} />

          {/* Flow paths */}
          {phase.flows.map((f, i) => (
            <FlowPath
              key={`${f.from}-${f.to}-${animKey}`}
              from={f.from} to={f.to}
              amount={f.amount} maxAmount={maxAmount}
              label={f.label}
              animDelay={i * 0.12}
              positions={positions}
            />
          ))}

          {/* Nodes */}
          {Object.entries(phase.nodes).map(([id, nodeData]) => {
            const pos = positions[id];
            if (!pos) return null;
            return <NodeBox key={id} data={nodeData} pos={pos} locale={locale} />;
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-4 text-[10px] text-gray-500 dark:text-gray-500"
        style={{ fontFamily: 'monospace' }}>
        <span>{t('flows.legendInflow5')}</span>
        <span>{t('flows.legendInflow')}</span>
        <span>{t('flows.legendSmallOutflow')}</span>
        <span>{t('flows.legendOutflow5')}</span>
        <span className="text-indigo-400">{t('flows.legendPath')}</span>
      </div>

      {/* Disclaimer */}
      <div className="text-center text-[9px] text-gray-700 dark:text-gray-600"
        style={{ fontFamily: 'monospace' }}>
        {t('flows.disclaimer')}
      </div>
    </div>
  );
}
