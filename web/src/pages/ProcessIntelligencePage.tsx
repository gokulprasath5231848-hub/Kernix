import { useMemo, useState } from 'react';
import { useProcesses, useProcessIntelligence } from '../hooks/useProcesses';
import StatCard from '../components/roadmap/StatCard';
import { FlowNode } from '../types';

export default function ProcessIntelligencePage() {
  const { data: processes, isLoading: loadingProcesses } = useProcesses();
  const [selectedId, setSelectedId] = useState<string>('');

  // Auto-select the first / highest-scoring process once loaded
  const effectiveId = selectedId || (processes?.[0]?.id ?? '');

  const { data: intel, isLoading: loadingIntel, isError } = useProcessIntelligence(effectiveId || undefined);

  // Dominant variant (most common path)
  const dominantVariant = useMemo(() => intel?.variants?.[0] ?? null, [intel]);

  // Top 3 bottlenecks (slowest nodes)
  const bottlenecks = useMemo(() => {
    if (!intel?.nodes?.length) return [];
    return [...intel.nodes]
      .filter(n => n.avg_minutes > 0)
      .sort((a, b) => b.avg_minutes - a.avg_minutes)
      .slice(0, 3);
  }, [intel]);

  // Highest-rework activities (nodes that appear most — high count relative to case_count indicates rework)
  const maxNodeMinutes = useMemo(() => {
    if (!intel?.nodes?.length) return 0;
    return Math.max(...intel.nodes.map(n => n.avg_minutes));
  }, [intel]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-2">Process Intelligence</h1>
          <p className="text-on-surface-variant text-sm">
            Step-level flow analysis — path variants, bottlenecks, and rework.
          </p>
        </div>

        {/* Process selector */}
        <div>
          <select
            value={effectiveId}
            onChange={(e) => setSelectedId(e.target.value)}
            disabled={loadingProcesses}
            className="bg-surface-container border border-outline-variant/30 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary min-w-[280px]"
          >
            {loadingProcesses && <option>Loading…</option>}
            {processes?.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} {p.score ? `(${p.score.value_score.toFixed(1)})` : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading / Error */}
      {(loadingIntel || loadingProcesses) && (
        <div className="p-12 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
      )}
      {isError && (
        <div className="p-12 text-center text-error">Failed to load process intelligence.</div>
      )}

      {intel && !loadingIntel && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Total Cases" value={String(intel.case_count)} icon="cases" />
            <StatCard label="Unique Activities" value={String(intel.nodes.length)} icon="account_tree" accentColor="border-amber-400" />
            <StatCard label="Path Variants" value={String(intel.variants.length)} icon="alt_route" accentColor="border-secondary" />
            <StatCard
              label="Rework Rate"
              value={`${(intel.rework_rate * 100).toFixed(1)}%`}
              icon="replay"
              accentColor={intel.rework_rate > 0.2 ? 'border-rose-400' : 'border-emerald-400'}
            />
          </div>

          {/* Dominant variant flow */}
          {dominantVariant && (
            <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 p-6">
              <h2 className="text-sm font-semibold text-on-surface-variant uppercase tracking-wider mb-4 flex items-center space-x-2">
                <span className="material-symbols-outlined text-[18px]">route</span>
                <span>Dominant Path ({dominantVariant.pct.toFixed(1)}% of cases)</span>
              </h2>
              <div className="flex items-start overflow-x-auto pb-4">
                <div className="flex items-center min-w-max">
                  {dominantVariant.sequence.map((step, idx) => {
                    const node = intel.nodes.find(n => n.activity === step);
                    const isLast = idx === dominantVariant.sequence.length - 1;
                    const edge = !isLast
                      ? intel.edges.find(e => e.source === step && e.target === dominantVariant.sequence[idx + 1])
                      : null;
                    const isSlowest = node && maxNodeMinutes > 0 && node.avg_minutes === maxNodeMinutes;

                    return (
                      <div key={idx} className="flex items-center">
                        <div className={`relative flex flex-col w-56 ${isSlowest ? 'transform -translate-y-2' : ''}`}>
                          {isSlowest && (
                            <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-semibold text-rose-400 bg-rose-950/40 px-2 py-0.5 rounded-full border border-rose-400/30 whitespace-nowrap">
                              ⚠ BOTTLENECK
                            </div>
                          )}
                          <div className={`bg-surface-container-low p-4 rounded-xl border ${
                            isSlowest
                              ? 'border-rose-400/50 shadow-[0_0_15px_rgba(244,63,94,0.1)] ring-1 ring-rose-400/30'
                              : 'border-outline-variant/30 hover:border-outline-variant/60 transition-colors'
                          }`}>
                            <div className="flex justify-between items-start mb-2">
                              <span className="text-[10px] font-mono bg-surface-container-high px-2 py-1 rounded text-on-surface-variant border border-outline-variant/20">
                                STEP_{String(idx + 1).padStart(2, '0')}
                              </span>
                            </div>
                            <h4 className="font-semibold text-xs mb-2 line-clamp-2">{step}</h4>
                            <div className="flex justify-between items-center text-[10px] font-mono border-t border-outline-variant/20 pt-2">
                              <span className="text-primary">{node ? `${node.avg_minutes.toFixed(1)} min` : '—'}</span>
                              <span className="text-on-surface-variant/50">{node?.systems?.join(', ') || '—'}</span>
                            </div>
                          </div>
                        </div>

                        {!isLast && (
                          <div className="w-12 h-0.5 relative mx-1 flex-shrink-0">
                            <div className="absolute inset-0 bg-outline-variant/30"></div>
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/50 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"></div>
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 border-t-2 border-r-2 border-outline-variant/50 rotate-45"></div>
                            {edge && (
                              <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[9px] font-mono text-on-surface-variant/60 whitespace-nowrap">
                                ×{edge.count}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Bottlenecks + Rework panel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Bottlenecks */}
            <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 p-6">
              <h2 className="text-sm font-semibold text-on-surface-variant uppercase tracking-wider mb-4 flex items-center space-x-2">
                <span className="material-symbols-outlined text-[18px]">speed</span>
                <span>Top Bottlenecks</span>
              </h2>
              {bottlenecks.length > 0 ? (
                <div className="space-y-3">
                  {bottlenecks.map((node, i) => (
                    <BottleneckCard key={node.activity} node={node} rank={i + 1} maxMinutes={maxNodeMinutes} />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-on-surface-variant italic">No duration data available.</p>
              )}
            </div>

            {/* Variants table */}
            <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 p-6">
              <h2 className="text-sm font-semibold text-on-surface-variant uppercase tracking-wider mb-4 flex items-center space-x-2">
                <span className="material-symbols-outlined text-[18px]">alt_route</span>
                <span>Path Variants</span>
              </h2>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {intel.variants.map((v, i) => (
                  <div key={i} className="flex items-center space-x-3 bg-surface-container/50 rounded-lg p-3 border border-outline-variant/20">
                    <span className="text-xs font-mono text-on-surface-variant w-8 flex-shrink-0">#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-mono text-on-surface truncate" title={v.sequence.join(' → ')}>
                        {v.sequence.join(' → ')}
                      </div>
                      {/* Percentage bar */}
                      <div className="mt-1.5 h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${Math.max(v.pct, 2)}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0 ml-2">
                      <span className="text-xs font-mono text-on-surface">{v.case_count}</span>
                      <span className="text-[10px] text-on-surface-variant ml-1">({v.pct.toFixed(1)}%)</span>
                    </div>
                  </div>
                ))}
                {!intel.variants.length && (
                  <p className="text-sm text-on-surface-variant italic">No variant data available.</p>
                )}
              </div>
            </div>
          </div>

          {/* All nodes table */}
          <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 overflow-x-auto">
            <div className="px-6 py-4 border-b border-outline-variant/30">
              <h2 className="text-sm font-semibold text-on-surface-variant uppercase tracking-wider flex items-center space-x-2">
                <span className="material-symbols-outlined text-[18px]">list</span>
                <span>All Activities</span>
              </h2>
            </div>
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="bg-surface-container/50 border-b border-outline-variant/30">
                <tr>
                  <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs">Activity</th>
                  <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs text-center">Count</th>
                  <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs text-center">Avg Duration</th>
                  <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs">Systems</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20">
                {intel.nodes.map(node => (
                  <tr key={node.activity} className="hover:bg-surface-container/30">
                    <td className="px-6 py-3 text-sm font-medium">{node.activity}</td>
                    <td className="px-6 py-3 text-center font-mono text-sm">{node.count}</td>
                    <td className="px-6 py-3 text-center font-mono text-sm">
                      {node.avg_minutes > 0 ? `${node.avg_minutes.toFixed(1)} min` : '—'}
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex flex-wrap gap-1">
                        {node.systems.map(s => (
                          <span key={s} className="px-2 py-0.5 rounded bg-surface-container-high text-[10px] uppercase tracking-wider text-on-surface-variant border border-outline-variant/20">
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Bottleneck card sub-component
// ---------------------------------------------------------------------------

function BottleneckCard({ node, rank, maxMinutes }: { node: FlowNode; rank: number; maxMinutes: number }) {
  const pct = maxMinutes > 0 ? (node.avg_minutes / maxMinutes) * 100 : 0;
  return (
    <div className="bg-surface-container/50 rounded-lg p-3 border border-outline-variant/20">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono text-on-surface-variant">#{rank}</span>
          <span className="text-sm font-semibold text-on-surface">{node.activity}</span>
        </div>
        <span className="text-sm font-mono text-rose-400">{node.avg_minutes.toFixed(1)} min</span>
      </div>
      <div className="h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
        <div
          className="h-full bg-rose-400 rounded-full transition-all"
          style={{ width: `${Math.max(pct, 4)}%` }}
        />
      </div>
      {node.systems.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {node.systems.map(s => (
            <span key={s} className="px-2 py-0.5 rounded bg-surface-container-high text-[9px] uppercase tracking-wider text-on-surface-variant border border-outline-variant/20">
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
