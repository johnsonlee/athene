import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useCapitalFlows } from '../../hooks/useCapitalFlows';
import { useI18n } from '../../lib/i18n';
import { useTheme } from '../../lib/theme';
import { LoadingSpinner } from '../common/LoadingSpinner';
import type { CapitalFlowPhase, CapitalFlowNode } from '../../types';

// ─── Catmull-Rom spline → SVG cubic bezier path ───
function catmullRomPath(points: { x: number; y: number }[], alpha = 0.5): string {
  if (points.length < 2) return '';
  if (points.length === 2) return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;

  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];

    // Knot parameterization
    const d1 = Math.hypot(p2.x - p1.x, p2.y - p1.y);
    const d0 = Math.hypot(p1.x - p0.x, p1.y - p0.y);
    const d2 = Math.hypot(p3.x - p2.x, p3.y - p2.y);

    const t0a = Math.pow(d0, alpha) || 1;
    const t1a = Math.pow(d1, alpha) || 1;
    const t2a = Math.pow(d2, alpha) || 1;

    const cp1x = p1.x + (p2.x - p0.x) / (3 * (1 + t0a / t1a));
    const cp1y = p1.y + (p2.y - p0.y) / (3 * (1 + t0a / t1a));
    const cp2x = p2.x - (p3.x - p1.x) / (3 * (1 + t2a / t1a));
    const cp2y = p2.y - (p3.y - p1.y) / (3 * (1 + t2a / t1a));

    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}

// ─── SVG Layout Constants ───
const SVG_W = 820;
const SVG_H = 500;
const NODE_W = 100;
const NODE_H = 52;

// ─── Color helpers ───
function getNodeColor(net: number, isDark: boolean) {
  if (isDark) {
    if (net > 5) return { fill: '#064e3b', stroke: '#10b981', text: '#6ee7b7', label: '#d1d5db', glow: 'rgba(16,185,129,0.3)' };
    if (net > 0) return { fill: '#14532d', stroke: '#22c55e', text: '#86efac', label: '#d1d5db', glow: 'rgba(34,197,94,0.2)' };
    if (net > -5) return { fill: '#451a03', stroke: '#f59e0b', text: '#fcd34d', label: '#d1d5db', glow: 'rgba(245,158,11,0.15)' };
    return { fill: '#450a0a', stroke: '#ef4444', text: '#fca5a5', label: '#d1d5db', glow: 'rgba(239,68,68,0.3)' };
  }
  if (net > 5) return { fill: '#ecfdf5', stroke: '#10b981', text: '#065f46', label: '#374151', glow: 'rgba(16,185,129,0.15)' };
  if (net > 0) return { fill: '#f0fdf4', stroke: '#22c55e', text: '#166534', label: '#374151', glow: 'rgba(34,197,94,0.1)' };
  if (net > -5) return { fill: '#fffbeb', stroke: '#f59e0b', text: '#92400e', label: '#374151', glow: 'rgba(245,158,11,0.1)' };
  return { fill: '#fef2f2', stroke: '#ef4444', text: '#991b1b', label: '#374151', glow: 'rgba(239,68,68,0.15)' };
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
function FlowPath({ from, to, amount, maxAmount, label, animDelay, positions, isDark }: {
  from: string; to: string; amount: number; maxAmount: number;
  label: string; animDelay: number;
  positions: Record<string, { x: number; y: number }>;
  isDark: boolean;
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
      <path d={path} fill="none" stroke={isDark ? 'rgba(99,102,241,0.08)' : 'rgba(99,102,241,0.06)'} strokeWidth={thickness + 4} />
      <path
        d={path} fill="none" stroke="#6366f1" strokeWidth={thickness}
        opacity={opacity} strokeLinecap="round"
        style={{
          strokeDasharray: '1200', strokeDashoffset: '1200',
          animation: `flowDraw 1s ease ${animDelay}s forwards`,
        }}
      />
      <circle r={Math.max(2, thickness / 2)} fill={isDark ? '#a5b4fc' : '#6366f1'} opacity={0.9}>
        <animateMotion dur="3s" repeatCount="indefinite" begin={`${animDelay}s`}>
          <mpath href={`#${pathId}`} />
        </animateMotion>
      </circle>
      <path id={pathId} d={path} fill="none" stroke="none" />
      <rect x={labelX - 22} y={labelY - 8} width={44} height={16} rx={4}
        fill={isDark ? 'rgba(15,15,25,0.85)' : 'rgba(255,255,255,0.92)'}
        stroke={isDark ? 'rgba(99,102,241,0.2)' : 'rgba(99,102,241,0.3)'} strokeWidth={0.5} />
      <text x={labelX} y={labelY + 3} textAnchor="middle"
        fill={isDark ? '#a5b4fc' : '#4f46e5'}
        fontSize="8" fontWeight="500" style={{ fontFamily: 'monospace' }}>
        {label}
      </text>
    </g>
  );
}

// ─── Node Box Component ───
function NodeBox({ data, pos, locale, isDark }: {
  data: CapitalFlowNode;
  pos: { x: number; y: number };
  locale: string;
  isDark: boolean;
}) {
  const colors = getNodeColor(data.net, isDark);
  const label = locale === 'zh' ? data.label_zh : data.label_en;
  const isProxy = data.confidence !== undefined && data.confidence < 1.0;
  return (
    <g>
      <rect
        x={pos.x} y={pos.y} width={NODE_W} height={NODE_H} rx={8}
        fill={colors.fill} stroke={colors.stroke} strokeWidth={1.2}
        strokeDasharray={isProxy ? '4 2' : 'none'}
        opacity={isProxy ? 0.8 : 1}
        filter={`drop-shadow(0 0 6px ${colors.glow})`}
      />
      <text x={pos.x + NODE_W / 2} y={pos.y + 18} textAnchor="middle"
        fill={colors.label} fontSize="11" fontWeight="600">
        {label}
      </text>
      <text x={pos.x + NODE_W / 2} y={pos.y + 36} textAnchor="middle"
        fill={colors.text} fontSize="12" fontWeight="700"
        style={{ fontFamily: 'monospace' }}>
        {data.value}
      </text>
      {isProxy && (
        <text x={pos.x + NODE_W - 4} y={pos.y + 10} textAnchor="end"
          fill={isDark ? '#6b7280' : '#9ca3af'} fontSize="7"
          style={{ fontFamily: 'monospace' }}>
          proxy
        </text>
      )}
    </g>
  );
}

// ─── RFI helpers ───
function computeRfi(riskNet: number, safeNet: number): number {
  const total = Math.abs(riskNet) + Math.abs(safeNet);
  if (total < 0.5) return 0;
  return (riskNet - safeNet) / total;
}

function getRfiRegime(rfi: number, t: (k: any) => string): { label: string; color: string } {
  if (rfi < -0.7) return { label: t('flows.rfiPanic'), color: '#991b1b' };
  if (rfi < -0.3) return { label: t('flows.rfiRiskOff'), color: '#ef4444' };
  if (rfi < 0)    return { label: t('flows.rfiMild'), color: '#f59e0b' };
  if (rfi < 0.3)  return { label: t('flows.rfiNeutral'), color: '#6b7280' };
  return { label: t('flows.rfiRiskOn'), color: '#22c55e' };
}

// ─── RFI Trend Chart (SVG line chart with colored zone bands) ───
const RFI_ZONES = [
  { from: -1.0, to: -0.7, color: '#991b1b' },  // panic
  { from: -0.7, to: -0.3, color: '#ef4444' },  // risk-off
  { from: -0.3, to: 0.0,  color: '#f59e0b' },  // mild
  { from: 0.0,  to: 0.3,  color: '#6b7280' },  // neutral
  { from: 0.3,  to: 1.0,  color: '#22c55e' },  // risk-on
];

function RfiTrendChart({ phases, activeIdx, onSelect, t, isDark }: {
  phases: CapitalFlowPhase[];
  activeIdx: number;
  onSelect: (idx: number) => void;
  t: (k: any) => string;
  isDark: boolean;
}) {
  const W = 600;
  const H = 160;
  const pad = { top: 14, right: 40, bottom: 22, left: 40 };
  const cw = W - pad.left - pad.right; // chart width
  const ch = H - pad.top - pad.bottom; // chart height

  const n = phases.length;
  if (n === 0) return null;

  // Map RFI [-1, +1] → y coordinate
  const yMin = -1, yMax = 1;
  const toY = (v: number) => pad.top + ch * (1 - (v - yMin) / (yMax - yMin));
  const toX = (i: number) => pad.left + (n > 1 ? (i / (n - 1)) * cw : cw / 2);

  // Build the line path using Catmull-Rom spline
  const points = phases.map((p, i) => {
    const rfi = p.rfi ?? computeRfi(p.risk_net, p.safe_net);
    return { x: toX(i), y: toY(Math.max(-1, Math.min(1, rfi))), rfi };
  });
  const linePath = catmullRomPath(points);

  // Active point
  const ap = points[activeIdx];
  const activeRfi = ap?.rfi ?? 0;
  const regime = getRfiRegime(activeRfi, t);

  // Date labels: show ~5-7 evenly spaced labels
  const labelCount = Math.min(n, 6);
  const labelStep = n > 1 ? (n - 1) / (labelCount - 1) : 0;
  const dateLabels: { idx: number; x: number; label: string }[] = [];
  for (let k = 0; k < labelCount; k++) {
    const idx = Math.round(k * labelStep);
    dateLabels.push({ idx, x: toX(idx), label: phases[idx].date.slice(5) });
  }

  // Y-axis threshold labels
  const yTicks = [
    { v: 0.3, label: '0.3' },
    { v: 0, label: '0' },
    { v: -0.3, label: '-0.3' },
    { v: -0.7, label: '-0.7' },
  ];

  // Hover hit area: find nearest point
  const handleClick = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const svgX = (clientX / rect.width) * W;
    // Find nearest phase index
    let best = 0;
    let bestDist = Infinity;
    for (let i = 0; i < n; i++) {
      const d = Math.abs(toX(i) - svgX);
      if (d < bestDist) { bestDist = d; best = i; }
    }
    onSelect(best);
  }, [n, onSelect]);

  return (
    <svg
      width="100%" viewBox={`0 0 ${W} ${H}`} className="block cursor-crosshair"
      onClick={handleClick}
    >
      {/* Zone background bands */}
      {RFI_ZONES.map((z, i) => (
        <rect
          key={i}
          x={pad.left} y={toY(z.to)}
          width={cw} height={toY(z.from) - toY(z.to)}
          fill={z.color}
          opacity={isDark ? 0.08 : 0.06}
        />
      ))}
      {/* Horizontal threshold lines */}
      {yTicks.map(({ v }) => (
        <line
          key={v}
          x1={pad.left} y1={toY(v)} x2={pad.left + cw} y2={toY(v)}
          stroke={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}
          strokeWidth={0.5}
          strokeDasharray={v === 0 ? 'none' : '3 3'}
        />
      ))}
      {/* Y-axis labels (right side) */}
      {yTicks.map(({ v, label }) => (
        <text
          key={v}
          x={pad.left + cw + 4} y={toY(v) + 3}
          fill={isDark ? '#6b7280' : '#9ca3af'}
          fontSize="8" style={{ fontFamily: 'monospace' }}
        >
          {label}
        </text>
      ))}
      {/* X-axis date labels */}
      {dateLabels.map(({ idx, x, label }) => (
        <text
          key={idx}
          x={x} y={H - 4}
          textAnchor="middle"
          fill={isDark ? '#6b7280' : '#9ca3af'}
          fontSize="8" style={{ fontFamily: 'monospace' }}
        >
          {label}
        </text>
      ))}
      {/* RFI line */}
      <path
        d={linePath} fill="none"
        stroke={isDark ? '#a5b4fc' : '#6366f1'}
        strokeWidth={1.8} strokeLinejoin="round" strokeLinecap="round"
      />
      {/* Active vertical crosshair */}
      {ap && (
        <>
          <line
            x1={ap.x} y1={pad.top} x2={ap.x} y2={pad.top + ch}
            stroke={isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)'}
            strokeWidth={0.5} strokeDasharray="2 2"
          />
          <circle
            cx={ap.x} cy={ap.y} r={4}
            fill={regime.color} stroke={isDark ? '#1f2937' : '#fff'} strokeWidth={1.5}
          />
          {/* Value badge near the active point */}
          <rect
            x={ap.x - 24} y={ap.y - 18}
            width={48} height={14} rx={3}
            fill={isDark ? 'rgba(15,15,25,0.9)' : 'rgba(255,255,255,0.95)'}
            stroke={regime.color} strokeWidth={0.5}
          />
          <text
            x={ap.x} y={ap.y - 8}
            textAnchor="middle" fill={regime.color}
            fontSize="8" fontWeight="700" style={{ fontFamily: 'monospace' }}
          >
            {activeRfi >= 0 ? '+' : ''}{activeRfi.toFixed(2)}
          </text>
        </>
      )}
    </svg>
  );
}

// ─── Per-asset line colors ───
const ASSET_COLORS: Record<string, string> = {
  // Risk
  usEquity: '#3b82f6',  // blue
  euEquity: '#14b8a6',  // teal
  jpEquity: '#ec4899',  // pink
  emEquity: '#f97316',  // orange
  crypto:   '#a855f7',  // purple
  // Safe
  gold:       '#eab308', // yellow
  usTreasury: '#6366f1', // indigo
  cash:       '#22c55e', // green
  corpBond:   '#06b6d4', // cyan
};

// ─── Asset Flow Panel (multi-line chart for one asset group) ───
function AssetFlowPanel({ phases, activeIdx, onSelect, assetIds, isDark, locale }: {
  phases: CapitalFlowPhase[];
  activeIdx: number;
  onSelect: (idx: number) => void;
  assetIds: string[];
  isDark: boolean;
  locale: string;
}) {
  const W = 300;
  const H = 120;
  const pad = { top: 10, right: 8, bottom: 20, left: 38 };
  const cw = W - pad.left - pad.right;
  const ch = H - pad.top - pad.bottom;

  const n = phases.length;
  if (n === 0) return null;

  // Collect all net values to determine y-axis range
  let minVal = 0, maxVal = 0;
  const seriesData: Record<string, number[]> = {};
  for (const id of assetIds) {
    seriesData[id] = [];
  }
  for (const p of phases) {
    for (const id of assetIds) {
      const v = p.nodes[id]?.net ?? 0;
      seriesData[id].push(v);
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    }
  }
  // Ensure symmetric or at least include zero with some padding
  const yPad = Math.max(1, (maxVal - minVal) * 0.1);
  const yMin = Math.min(minVal - yPad, -0.5);
  const yMax = Math.max(maxVal + yPad, 0.5);

  const toY = (v: number) => pad.top + ch * (1 - (v - yMin) / (yMax - yMin));
  const toX = (i: number) => pad.left + (n > 1 ? (i / (n - 1)) * cw : cw / 2);

  // Zero line
  const zeroY = toY(0);

  // Y-axis ticks: 0 + nice bounds
  const yTicks = [
    { v: Math.round(yMax), label: `${Math.round(yMax)}` },
    { v: 0, label: '0' },
    { v: Math.round(yMin), label: `${Math.round(yMin)}` },
  ];

  // X-axis date labels: 3-4 evenly spaced
  const labelCount = Math.min(n, 4);
  const labelStep = n > 1 ? (n - 1) / (labelCount - 1) : 0;
  const dateLabels: { idx: number; x: number; label: string }[] = [];
  for (let k = 0; k < labelCount; k++) {
    const idx = Math.round(k * labelStep);
    dateLabels.push({ idx, x: toX(idx), label: phases[idx].date.slice(5) });
  }

  // Click handler
  const handleClick = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0, bestDist = Infinity;
    for (let i = 0; i < n; i++) {
      const d = Math.abs(toX(i) - svgX);
      if (d < bestDist) { bestDist = d; best = i; }
    }
    onSelect(best);
  }, [n, onSelect]);

  const activeX = toX(activeIdx);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="block cursor-crosshair" onClick={handleClick}>
      {/* Zero line */}
      <line x1={pad.left} y1={zeroY} x2={pad.left + cw} y2={zeroY}
        stroke={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}
        strokeWidth={0.5}
      />
      {/* Y-axis labels */}
      {yTicks.map(({ v, label }) => (
        <text key={v} x={pad.left - 4} y={toY(v) + 3} textAnchor="end"
          fill={isDark ? '#6b7280' : '#9ca3af'} fontSize="7"
          style={{ fontFamily: 'monospace' }}>
          {label}
        </text>
      ))}
      {/* X-axis date labels */}
      {dateLabels.map(({ idx, x, label }) => (
        <text key={idx} x={x} y={H - 4} textAnchor="middle"
          fill={isDark ? '#6b7280' : '#9ca3af'} fontSize="7"
          style={{ fontFamily: 'monospace' }}>
          {label}
        </text>
      ))}
      {/* Asset lines */}
      {assetIds.map((id) => {
        const vals = seriesData[id];
        const pts = vals.map((v, i) => ({ x: toX(i), y: toY(v) }));
        const path = catmullRomPath(pts);
        return (
          <path key={id} d={path} fill="none"
            stroke={ASSET_COLORS[id] ?? '#888'}
            strokeWidth={1.3} strokeLinejoin="round" strokeLinecap="round"
            opacity={0.85}
          />
        );
      })}
      {/* Active crosshair */}
      <line x1={activeX} y1={pad.top} x2={activeX} y2={pad.top + ch}
        stroke={isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)'}
        strokeWidth={0.5} strokeDasharray="2 2"
      />
      {/* Active dots */}
      {assetIds.map((id) => {
        const v = seriesData[id][activeIdx] ?? 0;
        return (
          <circle key={id} cx={activeX} cy={toY(v)} r={2.5}
            fill={ASSET_COLORS[id] ?? '#888'}
            stroke={isDark ? '#1f2937' : '#fff'} strokeWidth={1}
          />
        );
      })}
      {/* Legend inside chart (top area) */}
      {assetIds.map((id, i) => {
        const node = phases[activeIdx]?.nodes[id];
        const label = node ? (locale === 'zh' ? node.label_zh : node.label_en) : id;
        const val = seriesData[id][activeIdx] ?? 0;
        const colsPerRow = assetIds.length <= 4 ? assetIds.length : Math.ceil(assetIds.length / 2);
        const row = Math.floor(i / colsPerRow);
        const col = i % colsPerRow;
        const spacing = cw / colsPerRow;
        const lx = pad.left + col * spacing + 4;
        const ly = pad.top + row * 10 + 7;
        return (
          <g key={id}>
            <rect x={lx} y={ly - 5} width={5} height={5} rx={1}
              fill={ASSET_COLORS[id] ?? '#888'}
            />
            <text x={lx + 7} y={ly} fontSize="7"
              fill={isDark ? '#d1d5db' : '#374151'}
              style={{ fontFamily: 'monospace' }}>
              {label} {val >= 0 ? '+' : ''}{val.toFixed(1)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ─── Asset ID lists (stable references) ───
const RISK_ASSET_IDS = ['usEquity', 'euEquity', 'jpEquity', 'emEquity', 'crypto'];
const SAFE_ASSET_IDS = ['gold', 'usTreasury', 'cash', 'corpBond'];

// ─── RFI Dashboard ───
function RfiDashboard({ phases, activeIdx, onSelect, t, isDark }: {
  phases: CapitalFlowPhase[];
  activeIdx: number;
  onSelect: (idx: number) => void;
  t: (key: any, p?: any) => string;
  isDark: boolean;
}) {
  const phase = phases[activeIdx];
  if (!phase) return null;

  const riskNet = phase.risk_net;
  const safeNet = phase.safe_net;
  const untracked = phase.untracked ?? 0;
  const hasUntracked = Math.abs(untracked) > 1;
  const total = Math.abs(riskNet) + Math.abs(safeNet);
  const rfi = phase.rfi ?? computeRfi(riskNet, safeNet);
  const regime = getRfiRegime(rfi, t);

  return (
    <div className="space-y-2">
      {/* Chart header: title + current RFI value */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-gray-500"
            style={{ fontFamily: 'monospace' }}>
            {t('flows.rfi')}
          </span>
          <span className="text-base font-bold" style={{ fontFamily: 'monospace', color: regime.color }}>
            {rfi >= 0 ? '+' : ''}{rfi.toFixed(2)}
          </span>
          <span className="text-xs font-semibold" style={{ color: regime.color }}>
            {regime.label}
          </span>
        </div>
      </div>

      {/* Trend chart */}
      <div className="tech-card overflow-hidden rounded-xl p-2">
        <RfiTrendChart
          phases={phases} activeIdx={activeIdx} onSelect={onSelect}
          t={t} isDark={isDark}
        />
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="tech-card rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-gray-500"
            style={{ fontFamily: 'monospace' }}>
            {t('flows.riskNet')}
          </div>
          <div className={`mt-0.5 text-lg font-bold ${riskNet > 0 ? 'text-green-500' : 'text-red-500'}`}
            style={{ fontFamily: 'monospace' }}>
            {riskNet > 0 ? '+' : ''}{riskNet.toFixed(1)}B
          </div>
        </div>
        <div className="tech-card rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-gray-500"
            style={{ fontFamily: 'monospace' }}>
            {t('flows.safeNet')}
          </div>
          <div className={`mt-0.5 text-lg font-bold ${safeNet > 0 ? 'text-green-500' : 'text-red-500'}`}
            style={{ fontFamily: 'monospace' }}>
            {safeNet > 0 ? '+' : ''}{safeNet.toFixed(1)}B
          </div>
        </div>
        <div className="tech-card rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-gray-500"
            style={{ fontFamily: 'monospace' }}>
            {t('flows.total')}
          </div>
          <div className="mt-0.5 text-lg font-bold text-indigo-400"
            style={{ fontFamily: 'monospace' }}>
            ${Math.round(total)}B
          </div>
        </div>
        <div className={`rounded-lg border p-3 ${
          hasUntracked
            ? 'border-orange-500/20 bg-orange-500/5'
            : 'tech-card'
        }`}>
          <div className="text-[10px] uppercase tracking-wider text-gray-500"
            style={{ fontFamily: 'monospace' }}>
            {t('flows.untracked')}
          </div>
          <div className={`mt-0.5 text-lg font-bold ${hasUntracked ? 'text-orange-400' : 'text-gray-500'}`}
            style={{ fontFamily: 'monospace' }}>
            {hasUntracked ? `$${Math.round(untracked)}B` : '—'}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Timeline Component ───
function Timeline({ phases, activeIdx, onSelect, locale, isDark }: {
  phases: CapitalFlowPhase[];
  activeIdx: number;
  onSelect: (idx: number) => void;
  locale: string;
  isDark: boolean;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);
  const compact = phases.length > 12;

  // Auto-scroll to active phase
  useEffect(() => {
    // Use setTimeout to ensure DOM has updated after phases change
    const timer = setTimeout(() => {
      if (activeRef.current && scrollRef.current) {
        const container = scrollRef.current;
        const el = activeRef.current;
        const left = el.offsetLeft - container.offsetWidth / 2 + el.offsetWidth / 2;
        container.scrollTo({ left: Math.max(0, left), behavior: 'smooth' });
      }
    }, 50);
    return () => clearTimeout(timer);
  }, [activeIdx, phases.length]);

  // In compact mode, show date labels only on active, first, last, and every ~8th phase
  const showDateLabel = (i: number) => {
    if (!compact) return true;
    if (i === activeIdx || i === 0 || i === phases.length - 1) return true;
    const step = Math.max(4, Math.round(phases.length / 8));
    return i % step === 0;
  };

  // Fixed height for dot row to keep connector lines aligned
  const dotRowHeight = 14; // max dot size (active)
  const dotCenterY = dotRowHeight / 2;

  return (
    <div
      ref={scrollRef}
      className="mb-4 flex items-start overflow-x-auto scrollbar-thin"
      style={{ scrollbarWidth: 'thin', scrollbarColor: isDark ? 'rgba(255,255,255,0.1) transparent' : 'rgba(0,0,0,0.15) transparent' }}
    >
      {phases.map((p, i) => {
        const active = i === activeIdx;
        const past = i < activeIdx;
        const color = getPhaseColor(p.phase);
        const dotSize = active ? 14 : compact ? 8 : 10;

        return (
          <div key={p.id} className="flex items-start" style={{ flexShrink: 0 }}
            ref={active ? activeRef : undefined}>
            <button
              onClick={() => onSelect(i)}
              className="flex cursor-pointer flex-col items-center gap-0.5 border-0 bg-transparent"
              style={{ padding: compact ? '4px 2px' : '6px', minWidth: compact ? 28 : undefined }}
            >
              <div
                className="rounded-full transition-colors duration-300"
                style={{
                  width: dotSize,
                  height: dotSize,
                  marginTop: (dotRowHeight - dotSize) / 2,
                  background: active ? color : past ? color + '88' : (isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'),
                  border: `2px solid ${active ? color : past ? color + '44' : (isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.12)')}`,
                  boxShadow: active ? `0 0 12px ${color}55` : 'none',
                }}
              />
              {showDateLabel(i) && (
                <span className={`text-[10px] ${active ? 'text-gray-800 dark:text-gray-200 font-semibold' : 'text-gray-600 font-normal'}`}
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
                  marginTop: (compact ? 4 : 6) + dotCenterY,
                  background: past
                    ? `linear-gradient(to right, ${color}66, ${color}22)`
                    : (isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)'),
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
function ColumnLabels({ t, positions, nodes, isDark }: {
  t: (key: any) => string;
  positions: Record<string, { x: number; y: number }>;
  nodes: Record<string, CapitalFlowNode>;
  isDark: boolean;
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
        stroke={isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)'} strokeWidth={1} strokeDasharray="4 4" />
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
  const { theme } = useTheme();
  const isDark = theme === 'dark';
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
    // Reset to last index (latest) instead of null to avoid scroll issues
    setActiveIdx(-1); // -1 signals "use latest"
    setAnimKey(k => k + 1);
  }, []);

  const handleSelect = useCallback((idx: number) => {
    setActiveIdx(idx);
    setAnimKey(k => k + 1);
  }, []);

  // Set initial active index once data loads (default to latest = last phase)
  // -1 or null both resolve to the last phase
  const resolvedIdx = (activeIdx === null || activeIdx === -1 || activeIdx >= phases.length)
    ? (phases.length ? phases.length - 1 : 0)
    : activeIdx;

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
      <Timeline phases={phases} activeIdx={resolvedIdx} onSelect={handleSelect} locale={locale} isDark={isDark} />

      {/* RFI Dashboard */}
      <RfiDashboard phases={phases} activeIdx={resolvedIdx} onSelect={handleSelect} t={t} isDark={isDark} />

      {/* Flow Diagram */}
      <div className="tech-card overflow-hidden rounded-xl p-2">
        <svg key={animKey} width="100%" viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="block">
          <ColumnLabels t={t} positions={positions} nodes={phase.nodes} isDark={isDark} />

          {/* Flow paths */}
          {phase.flows.map((f, i) => (
            <FlowPath
              key={`${f.from}-${f.to}-${animKey}`}
              from={f.from} to={f.to}
              amount={f.amount} maxAmount={maxAmount}
              label={f.label}
              animDelay={i * 0.12}
              positions={positions}
              isDark={isDark}
            />
          ))}

          {/* Nodes */}
          {Object.entries(phase.nodes).map(([id, nodeData]) => {
            const pos = positions[id];
            if (!pos) return null;
            return <NodeBox key={id} data={nodeData} pos={pos} locale={locale} isDark={isDark} />;
          })}
        </svg>
      </div>

      {/* Per-asset flow charts: risk left, safe right */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div className="tech-card overflow-hidden rounded-xl p-2">
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-gray-500 px-1"
            style={{ fontFamily: 'monospace' }}>
            {t('flows.riskAssets')}
          </div>
          <AssetFlowPanel
            phases={phases} activeIdx={resolvedIdx} onSelect={handleSelect}
            assetIds={RISK_ASSET_IDS} isDark={isDark} locale={locale}
          />
        </div>
        <div className="tech-card overflow-hidden rounded-xl p-2">
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-gray-500 px-1"
            style={{ fontFamily: 'monospace' }}>
            {t('flows.safeAssets')}
          </div>
          <AssetFlowPanel
            phases={phases} activeIdx={resolvedIdx} onSelect={handleSelect}
            assetIds={SAFE_ASSET_IDS} isDark={isDark} locale={locale}
          />
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-4 text-[10px] text-gray-500 dark:text-gray-500"
        style={{ fontFamily: 'monospace' }}>
        <span>{t('flows.legendInflow5')}</span>
        <span>{t('flows.legendInflow')}</span>
        <span>{t('flows.legendSmallOutflow')}</span>
        <span>{t('flows.legendOutflow5')}</span>
        <span className="text-indigo-400">{t('flows.legendPath')}</span>
        <span className="text-gray-400">{t('flows.legendProxy')}</span>
      </div>

      {/* Disclaimer */}
      <div className="text-center text-[9px] text-gray-700 dark:text-gray-600"
        style={{ fontFamily: 'monospace' }}>
        {t('flows.disclaimer')}
      </div>
    </div>
  );
}
